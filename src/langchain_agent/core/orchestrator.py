"""
Perfa - LangChain Agent Module

@file: core/orchestrator.py
@desc: Agent编排器 — 支持工作流路由和 ReAct 两种模式
@author: Perfa Team
@date: 2026-03-18
"""

# 标准库导入
import asyncio
import time as _time
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

# 第三方库导入
from langchain_agent.core.logger import get_logger
logger = get_logger()
from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseLLM
from langchain_core.tools import BaseTool

# 本地模块导入
from langchain_agent.agents import ReActAgent
from langchain_agent.core.memory import ConversationMemory
from langchain_agent.core.error_handler import ErrorHandler
from langchain_agent.core.config import LLMConfig, MCPConfig, AgentConfig
from langchain_agent.backend.report_store import ReportStore

# OTel 可观测性
_otel_initialized = False


def _init_otel():
    """初始化 OTel 追踪和指标（仅一次）"""
    global _otel_initialized
    if _otel_initialized:
        return
    _otel_initialized = True
    try:
        from langchain_agent.observability import setup_tracing, setup_metrics
        setup_tracing(service_name="perfa-agent")
        setup_metrics(service_name="perfa-agent")
        logger.info("✅ OTel 可观测性初始化完成")
    except Exception as e:
        logger.warning(f"⚠️ OTel 初始化失败（不影响运行）: {e}")


class AgentOrchestrator:
    """
    Agent编排器
    
    负责协调不同Agent和工具，处理用户查询。
    支持两种执行模式：
    - auto: 先场景路由，结构化场景走 LangGraph 工作流，其余走 ReAct
    - react: 强制走原 ReAct 循环
    """
    
    def __init__(
        self,
        mcp_adapter,
        llm_config: Optional[LLMConfig] = None,
        agent_config: Optional[AgentConfig] = None,
        memory_max_turns: int = 10,
        memory_max_age_hours: int = 24
    ):
        """
        初始化Agent编排器
        
        Args:
            mcp_adapter: MCP工具适配器
            llm_config: LLM配置（可选）
            agent_config: Agent配置（可选）
            memory_max_turns: 记忆最大轮数
            memory_max_age_hours: 记忆最大存活时间（小时）
        """
        self.mcp_adapter = mcp_adapter
        self.llm_config = llm_config or LLMConfig()
        self.agent_config = agent_config or AgentConfig()
        
        # 初始化组件
        self.memory = ConversationMemory(max_turns=memory_max_turns, max_age_hours=memory_max_age_hours)
        self.report_store = ReportStore()
        self.error_handler = ErrorHandler(
            max_retries=self.agent_config.error_max_retries,
            retry_delay=self.agent_config.error_retry_delay
        )
        self.llm = self._create_llm()
        self.tools = self.mcp_adapter.list_tools()
        self.tools_dict = {tool.name: tool for tool in self.tools}
        self.agent = ReActAgent(
            llm=self.llm,
            tools=self.tools,
            max_iterations=self.agent_config.max_iterations
        )
        
        # 初始化工作流引擎
        self.workflow_engine = None
        self._init_workflow_engine()
        
        # 初始化 OTel 可观测性
        _init_otel()
        
        logger.info(f"Agent编排器初始化完成，使用智谱AI GLM-5")
        logger.info(f"可用工具数: {len(self.tools)}")

    @staticmethod
    def _scenario_label(scenario_name: str) -> str:
        labels = {
            "quick_test": "快速测试",
            "full_assessment": "全面评估",
            "cpu_focus": "CPU 专项",
            "storage_focus": "存储专项",
            "network_focus": "网络专项",
        }
        return labels.get(scenario_name, scenario_name)

    @staticmethod
    def _safe_detach_token(token) -> None:
        if not token:
            return
        try:
            from opentelemetry import context as otel_ctx
            otel_ctx.detach(token)
        except ValueError as e:
            logger.debug(f"忽略跨上下文 detach 异常: {e}")
        except Exception as e:
            logger.debug(f"detach token 异常: {e}")

    async def _resolve_server_metadata(self, server_id: Optional[str]) -> Dict[str, Any]:
        if not server_id:
            return {}

        list_servers_tool = self.tools_dict.get("list_servers")
        if not list_servers_tool:
            return {}

        try:
            result = await list_servers_tool.ainvoke({}) if hasattr(list_servers_tool, "ainvoke") else list_servers_tool.run({})
            if isinstance(result, str):
                import json
                result = json.loads(result)
            servers = result if isinstance(result, list) else result.get("servers", [])
            for server in servers:
                if isinstance(server, dict) and server.get("server_id") == server_id:
                    return server
        except Exception as e:
            logger.debug(f"解析服务器元数据失败: {e}")
        return {}

    @staticmethod
    def _extract_summary(text: str) -> str:
        normalized = "\n".join(line.strip() for line in text.splitlines() if line.strip())
        if not normalized:
            return "暂无摘要"
        normalized = normalized.replace("#", "").strip()
        return normalized[:180] + ("..." if len(normalized) > 180 else "")

    async def _persist_workflow_report(
        self,
        *,
        query: str,
        result: Dict[str, Any],
        session_id: str,
        conversation_id: str,
        trace_id: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        if result.get("mode") != "workflow":
            return None

        scenario = result.get("scenario") or "workflow"
        server_id = result.get("server_id")
        server_meta = await self._resolve_server_metadata(server_id)
        server_alias = server_meta.get("alias") if isinstance(server_meta, dict) else None
        server_ip = result.get("server_ip") or (server_meta.get("ip") if isinstance(server_meta, dict) else None)
        ai_report = result.get("result", "") or "未生成报告"
        report = {
            "id": f"report_{uuid.uuid4().hex}",
            "type": scenario,
            "title": f"{self._scenario_label(scenario)} · {server_alias or server_ip or server_id or '未命名服务器'}",
            "scenario": scenario,
            "scenario_label": self._scenario_label(scenario),
            "server_id": server_id or "",
            "server_alias": server_alias,
            "server_ip": server_ip,
            "created_at": datetime.now().isoformat(),
            "status": "completed" if result.get("success") else "failed",
            "summary": self._extract_summary(ai_report),
            "ai_report": ai_report,
            "content": ai_report,
            "raw_results": result.get("results", {}),
            "raw_errors": result.get("errors", []),
            "knowledge_matches": result.get("knowledge_matches", []),
            "task_ids": result.get("task_ids", {}),
            "tool_calls": result.get("tool_calls", []),
            "trace_id": trace_id,
            "query": query,
            "session_id": session_id,
            "conversation_id": conversation_id,
            "source": "workflow",
            "test_count": len(result.get("results", {})),
            "charts": [],
        }
        self.report_store.save_report(report)
        result["report_id"] = report["id"]
        return report
    
    def _init_workflow_engine(self):
        """初始化 LangGraph 工作流引擎"""
        try:
            from langchain_agent.workflows.graph_builder import WorkflowEngine
            self.workflow_engine = WorkflowEngine(
                tools=self.tools_dict,
                llm=self.llm,
                confidence_threshold=0.7
            )
            logger.info(f"✅ 工作流引擎初始化完成，可用场景: {self.workflow_engine.get_available_scenarios()}")
        except ImportError as e:
            logger.warning(f"⚠️ LangGraph 未安装，工作流模式不可用: {e}")
            self.workflow_engine = None
        except Exception as e:
            logger.warning(f"⚠️ 工作流引擎初始化失败: {e}")
            self.workflow_engine = None
    
    def _create_llm(self) -> BaseLLM:
        """
        创建LLM实例
        
        使用智谱AI GLM-5模型
        智谱AI的API兼容OpenAI格式，可以直接使用ChatOpenAI
        """
        if not self.llm_config.zhipu_api_key:
            raise ValueError("智谱AI API Key未配置，请在.env文件中设置ZHIPU_API_KEY")
        
        logger.info(f"创建智谱AI LLM，模型: {self.llm_config.zhipu_model}")
        
        # 使用LangChain的ChatOpenAI连接智谱AI
        # 智谱AI的API兼容OpenAI格式，只需设置base_url
        return ChatOpenAI(
            api_key=self.llm_config.zhipu_api_key,
            base_url=self.llm_config.zhipu_base_url,
            model=self.llm_config.zhipu_model,
            temperature=self.llm_config.zhipu_temperature,
            max_tokens=self.llm_config.zhipu_max_tokens
        )
    
    async def process_query(
        self,
        query: str,
        session_id: Optional[str] = None,
        mode: str = "auto",
        conversation_id: Optional[str] = None,
        server_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        处理用户查询
        
        Args:
            query: 用户查询
            session_id: 会话ID（可选）
            mode: 执行模式
                - auto: 先场景路由，结构化场景走 LangGraph 工作流，其余走 ReAct
                - react: 强制走原 ReAct 循环
                - workflow: 强制走工作流模式（需指定 scenario 参数）
        
        Returns:
            Dict: 处理结果
        """
        if not session_id:
            import uuid
            session_id = f"session_{uuid.uuid4().hex[:16]}"
        if not conversation_id:
            conversation_id = session_id
        
        if mode not in ["auto", "react", "workflow"]:
            logger.warning(f"未知的执行模式 '{mode}'，使用默认模式 'auto'")
            mode = "auto"
        
        logger.info(f"开始处理查询，会话ID: {session_id}，模式: {mode}")
        logger.info(f"用户查询: {query}")
        if server_id:
            logger.info(f"绑定目标服务器: {server_id}")
        
        # 记录用户消息到记忆
        self.memory.add_message(session_id, "user", query)
        
        # OTel: 顶层查询处理 span + 活跃会话指标
        _span = None
        _token = None
        _trace_id = None
        try:
            from langchain_agent.observability.tracer import get_tracer
            _tracer = get_tracer()
            if _tracer:
                from opentelemetry import context as otel_ctx, trace
                _span = _tracer.start_span(
                    "orchestrator.process_query",
                    attributes={
                        "query": query[:200],
                        "session_id": session_id,
                        "conversation_id": conversation_id,
                        "mode": mode
                    },
                )
                ctx = trace.set_span_in_context(_span)
                _token = otel_ctx.attach(ctx)
                # 获取 trace_id 传给前端
                span_ctx = _span.get_span_context()
                _trace_id = format(span_ctx.trace_id, '032x')
        except Exception:
            pass
        
        session_metric_attrs = {"session_id": session_id, "conversation_id": conversation_id}
        if server_id:
            session_metric_attrs["server_id"] = server_id

        # 活跃会话 +1
        try:
            from langchain_agent.observability.metrics import get_metric
            session_metric = get_metric("session_active")
            if session_metric:
                session_metric.add(1, session_metric_attrs)
        except Exception:
            pass
        
        try:
            if mode == "react":
                # 强制走 ReAct
                if _span:
                    _span.add_event("routing.decision", {
                        "mode": "react",
                        "reason": "user_forced",
                    })
                result = await self._run_react(query, session_id)
            elif mode == "workflow" or mode == "auto":
                # auto 模式: 先尝试场景路由
                if mode == "auto" and self.workflow_engine:
                    scenario = await self.workflow_engine.route(query)
                    logger.info(f"场景路由结果: {scenario.name} ({scenario.display_name})")
                    
                    if scenario.name == "free_chat":
                        # 走原 ReAct 循环
                        if _span:
                            _span.add_event("routing.decision", {
                                "mode": "react",
                                "routed_scenario": scenario.name,
                                "reason": "free_chat_no_workflow_match",
                            })
                        result = await self._run_react(query, session_id)
                    else:
                        # 走 LangGraph 工作流
                        if _span:
                            _span.add_event("routing.decision", {
                                "mode": "workflow",
                                "routed_scenario": scenario.name,
                                "scenario_display": scenario.display_name,
                                "reason": "scenario_matched",
                            })
                    result = await self._run_workflow(scenario.name, query, session_id, server_id=server_id)
                elif mode == "workflow" and self.workflow_engine:
                    # 强制走工作流，默认使用 full_assessment
                    scenario = await self.workflow_engine.route(query)
                    if scenario.name == "free_chat":
                        scenario_name = "full_assessment"
                    else:
                        scenario_name = scenario.name
                    if _span:
                        _span.add_event("routing.decision", {
                            "mode": "workflow",
                            "routed_scenario": scenario_name,
                            "original_scenario": scenario.name,
                            "reason": "user_forced_workflow",
                        })
                    result = await self._run_workflow(scenario_name, query, session_id, server_id=server_id)
                else:
                    # 降级到 ReAct
                    if _span:
                        _span.add_event("routing.decision", {
                            "mode": "react",
                            "reason": "workflow_engine_unavailable",
                        })
                    result = await self._run_react(query, session_id)
            
            # 记录助手消息到记忆
            self.memory.add_message(session_id, "assistant", result.get("result", ""))
            
            # 记录工具调用到记忆
            for tool_call in result.get("tool_calls", []):
                self.memory.add_message(
                    session_id,
                    "tool",
                    f"工具: {tool_call.get('tool_name', '')}，结果: {str(tool_call.get('result', ''))[:100]}...",
                    metadata={
                        "tool_name": tool_call.get("tool_name", ""),
                        "arguments": tool_call.get("arguments", {}),
                        "execution_time": tool_call.get("execution_time", 0),
                    }
                )
            
            logger.info(f"查询处理完成，耗时: {result.get('execution_time', 0):.2f}秒")
            
            await self._persist_workflow_report(
                query=query,
                result=result,
                session_id=session_id,
                conversation_id=conversation_id,
                trace_id=_trace_id,
            )

            # OTel: 结束 span
            if _span and _span.is_recording():
                _span.set_attribute("is_success", result.get("is_success", False))
                _span.set_attribute("execution_time", result.get("execution_time", 0))
                _span.set_attribute("mode_used", result.get("mode", mode))
                _span.end()
            self._safe_detach_token(_token)
            
            # 活跃会话 -1
            try:
                from langchain_agent.observability.metrics import get_metric
                session_metric = get_metric("session_active")
                if session_metric:
                    session_metric.add(-1, session_metric_attrs)
            except Exception:
                pass
            
            # 附加 trace_id 到结果
            if _trace_id:
                result["trace_id"] = _trace_id
                result["jaeger_url"] = f"/api/monitor/jaeger/trace/{_trace_id}"
            result["conversation_id"] = conversation_id
            
            return result
            
        except Exception as e:
            error_msg = f"处理查询失败: {str(e)}"
            logger.error(error_msg)
            
            # OTel: 记录异常
            if _span and _span.is_recording():
                _span.record_exception(e)
                _span.set_attribute("is_success", False)
                _span.end()
            self._safe_detach_token(_token)
            
            # 活跃会话 -1
            try:
                from langchain_agent.observability.metrics import get_metric
                session_metric = get_metric("session_active")
                if session_metric:
                    session_metric.add(-1, session_metric_attrs)
            except Exception:
                pass
            
            return {
                "success": False,
                "session_id": session_id,
                "query": query,
                "error": error_msg,
                "tool_calls": [],
                "execution_time": 0,
                "is_success": False,
                "trace_id": _trace_id,
                "jaeger_url": f"/api/monitor/jaeger/trace/{_trace_id}" if _trace_id else None,
            }
    
    async def _run_react(self, query: str, session_id: str) -> Dict[str, Any]:
        """使用原 ReAct Agent 执行查询"""
        session_history = self.memory.get_history(session_id, last_n=10)
        
        logger.info("使用 ReAct Agent 执行查询")
        response = await self.agent.run(
            query, 
            session_id=session_id,
            context={"session_history": session_history}
        )
        
        return {
            "success": True,
            "session_id": session_id,
            "query": query,
            "result": response.result,
            "tool_calls": [
                {
                    "tool_name": tc.tool_name,
                    "arguments": tc.arguments,
                    "result": tc.result,
                    "execution_time": tc.execution_time
                }
                for tc in response.tool_calls
            ],
            "execution_time": response.execution_time,
            "is_success": response.is_success,
            "mode": "react",
            "thinking_process": response.thinking_process if hasattr(response, 'thinking_process') else None,
            "reasoning_time": response.reasoning_time if hasattr(response, 'reasoning_time') else 0
        }
    
    async def process_query_stream(
        self,
        query: str,
        session_id: Optional[str] = None,
        mode: str = "auto",
        conversation_id: Optional[str] = None,
        server_id: Optional[str] = None
    ):
        """
        流式处理用户查询 — 双通道事件流
        
        过程事件（metadata 通道）：
        - thinking_start: 开始思考 {iteration}
        - thinking_result: 思考完成 {iteration, reasoning_preview, decision}
        - tool_result: 工具调用结果 {tool_name, result, execution_time}
        - workflow_progress: 工作流进度 {current_node, status, scenario}
        
        答案事件（content 通道）：
        - answer_start: 答案即将开始
        - answer_delta: 答案文本增量 {content}
        - answer_done: 答案流结束
        
        完成事件：
        - done: 整个处理完成 {result}
        """
        import asyncio
        
        if not session_id:
            import uuid
            session_id = f"session_{uuid.uuid4().hex[:16]}"
        if not conversation_id:
            conversation_id = session_id
        
        logger.info(f"[Stream] 开始流式处理查询，会话ID: {session_id}，模式: {mode}")
        if server_id:
            logger.info(f"[Stream] 绑定目标服务器: {server_id}")
        
        # 记录用户消息到记忆
        self.memory.add_message(session_id, "user", query)
        
        # OTel
        _span = None
        _token = None
        _trace_id = None
        session_metric_attrs = {"session_id": session_id, "conversation_id": conversation_id}
        if server_id:
            session_metric_attrs["server_id"] = server_id
        try:
            from langchain_agent.observability.tracer import get_tracer
            _tracer = get_tracer()
            if _tracer:
                from opentelemetry import context as otel_ctx, trace
                _span = _tracer.start_span(
                    "orchestrator.process_query_stream",
                    attributes={
                        "query": query[:200],
                        "session_id": session_id,
                        "conversation_id": conversation_id,
                        "mode": mode
                    },
                )
                ctx = trace.set_span_in_context(_span)
                _token = otel_ctx.attach(ctx)
                span_ctx = _span.get_span_context()
                _trace_id = format(span_ctx.trace_id, '032x')
        except Exception:
            pass

        # 活跃会话 +1
        try:
            from langchain_agent.observability.metrics import get_metric
            session_metric = get_metric("session_active")
            if session_metric:
                session_metric.add(1, session_metric_attrs)
        except Exception:
            pass
        
        try:
            # 场景路由
            scenario = None
            if mode == "auto" and self.workflow_engine:
                scenario = await self.workflow_engine.route(query)
                logger.info(f"[Stream] 场景路由结果: {scenario.name}")
                
                if _span:
                    _span.add_event("routing.decision", {
                        "mode": "workflow" if scenario.name != "free_chat" else "react",
                        "routed_scenario": scenario.name,
                    })
            
            if scenario and scenario.name != "free_chat" and self.workflow_engine:
                # ---- 工作流模式 ----
                yield {
                    "type": "workflow_progress",
                    "current_node": "starting",
                    "status": "running",
                    "scenario": scenario.display_name or scenario.name,
                }
                
                result = await self._run_workflow(scenario.name, query, session_id, server_id=server_id)
                
                # 工作流节点进度
                node_statuses = result.get("node_statuses", {})
                for node, status in node_statuses.items():
                    yield {
                        "type": "workflow_progress",
                        "current_node": node,
                        "status": status,
                        "scenario": scenario.display_name or scenario.name,
                    }
                
                # 推送最终结果
                if _trace_id:
                    result["trace_id"] = _trace_id
                    result["jaeger_url"] = f"/api/monitor/jaeger/trace/{_trace_id}"
                result["conversation_id"] = conversation_id

                # 记录到记忆，保证流式工作流和同步路径一致
                self.memory.add_message(session_id, "assistant", result.get("result", ""))
                for tool_call in result.get("tool_calls", []):
                    self.memory.add_message(
                        session_id,
                        "tool",
                        f"工具: {tool_call.get('tool_name', '')}，结果: {str(tool_call.get('result', ''))[:100]}...",
                        metadata={
                            "tool_name": tool_call.get("tool_name", ""),
                            "arguments": tool_call.get("arguments", {}),
                            "execution_time": tool_call.get("execution_time", 0),
                        }
                    )
                
                # 流式推送答案正文
                final_content = result.get("result", "")
                if final_content:
                    yield {"type": "answer_start"}
                    async for chunk in self._stream_answer(final_content):
                        yield chunk
                    yield {"type": "answer_done"}
                
                await self._persist_workflow_report(
                    query=query,
                    result=result,
                    session_id=session_id,
                    conversation_id=conversation_id,
                    trace_id=_trace_id,
                )
                yield {"type": "done", "result": result}
            else:
                # ---- ReAct 模式（逐步推送） ----
                session_history = self.memory.get_history(session_id, last_n=10)
                
                from langchain_agent.agents.base_agent import AgentResponse, ToolCall
                
                self.agent.thoughts.clear()
                tool_calls: list = []
                iteration = 0
                final_result = ""
                thinking_log: list = []
                total_reasoning_time = 0.0
                
                while iteration < self.agent.max_iterations:
                    iteration += 1
                    
                    yield {
                        "type": "thinking_start",
                        "iteration": iteration,
                    }
                    
                    think_start_dt = __import__('datetime').datetime.now()
                    thought, full_reasoning = await self.agent._think(
                        query, tool_calls,
                        {"session_history": session_history}
                    )
                    think_time = (__import__('datetime').datetime.now() - think_start_dt).total_seconds()
                    total_reasoning_time += think_time
                    
                    self.agent.thoughts.append(thought)
                    if full_reasoning:
                        thinking_log.append(f"### 思考 #{iteration}\n\n{full_reasoning}")
                    
                    yield {
                        "type": "thinking_result",
                        "iteration": iteration,
                        "reasoning": full_reasoning[:500] if full_reasoning else "",
                        "decision": {
                            "is_final": thought.get("is_final", False),
                            "tool_name": thought.get("tool_name"),
                            "tool_args": thought.get("tool_args"),
                        },
                    }
                    
                    # 检查是否完成
                    if thought.get("is_final", False):
                        final_result = thought.get("content", "任务已完成")
                        break
                    
                    # 行动：调用工具
                    if "tool_name" in thought and "tool_args" in thought:
                        tool_name = thought["tool_name"]
                        tool_args = thought["tool_args"]
                        
                        tool_start_dt = __import__('datetime').datetime.now()
                        tool_result = await self.agent._act(tool_name, tool_args)
                        execution_time = (__import__('datetime').datetime.now() - tool_start_dt).total_seconds()
                        
                        tool_call = ToolCall(
                            tool_name=tool_name,
                            arguments=tool_args,
                            result=tool_result,
                            execution_time=execution_time
                        )
                        tool_calls.append(tool_call)
                        
                        yield {
                            "type": "tool_result",
                            "tool_name": tool_name,
                            "result": tool_result,
                            "execution_time": execution_time,
                        }
                    
                    await asyncio.sleep(0.1)
                
                # 构建最终结果
                if iteration >= self.agent.max_iterations and not final_result:
                    final_result = f"达到最大迭代次数({self.agent.max_iterations})仍未完成，已返回部分结果"
                
                thinking_summary = "\n\n".join(thinking_log) if thinking_log else None
                total_time = self.agent._calculate_execution_time()
                
                result = {
                    "success": True,
                    "session_id": session_id,
                    "conversation_id": conversation_id,
                    "query": query,
                    "result": final_result or "未生成结果",
                    "tool_calls": [
                        {
                            "tool_name": tc.tool_name,
                            "arguments": tc.arguments,
                            "result": tc.result,
                            "execution_time": tc.execution_time
                        }
                        for tc in tool_calls
                    ],
                    "execution_time": total_time,
                    "is_success": True,
                    "mode": "react",
                    "thinking_process": thinking_summary,
                    "reasoning_time": total_reasoning_time,
                }
                
                # 记录到记忆
                self.memory.add_message(session_id, "assistant", result.get("result", ""))
                for tc in tool_calls:
                    self.memory.add_message(
                        session_id, "tool",
                        f"工具: {tc.tool_name}，结果: {str(tc.result)[:100]}...",
                        metadata={"tool_name": tc.tool_name, "arguments": tc.arguments, "execution_time": tc.execution_time}
                    )
                
                if _trace_id:
                    result["trace_id"] = _trace_id
                    result["jaeger_url"] = f"/api/monitor/jaeger/trace/{_trace_id}"
                result["conversation_id"] = conversation_id
                
                # 流式推送答案正文
                if result.get("result"):
                    yield {"type": "answer_start"}
                    async for chunk in self._stream_answer(result["result"]):
                        yield chunk
                    yield {"type": "answer_done"}
                
                yield {"type": "done", "result": result}

        except (GeneratorExit, asyncio.CancelledError):
            logger.info("[Stream] 客户端提前断开，结束流式上下文")
            raise
        
        except Exception as e:
            logger.error(f"[Stream] 流式处理异常: {str(e)}")
            if _span and _span.is_recording():
                _span.record_exception(e)
            yield {
                "type": "done",
                "result": {
                    "success": False,
                    "session_id": session_id,
                    "conversation_id": conversation_id,
                    "query": query,
                    "result": f"处理失败: {str(e)}",
                    "tool_calls": [],
                    "execution_time": 0,
                    "is_success": False,
                    "mode": mode,
                    "trace_id": _trace_id,
                    "jaeger_url": f"/api/monitor/jaeger/trace/{_trace_id}" if _trace_id else None,
                }
            }
        finally:
            if _span and _span.is_recording():
                _span.end()
            self._safe_detach_token(_token)
            try:
                from langchain_agent.observability.metrics import get_metric
                session_metric = get_metric("session_active")
                if session_metric:
                    session_metric.add(-1, session_metric_attrs)
            except Exception:
                pass
    
    async def _stream_answer(self, text: str, chunk_size: int = 40):
        """将最终答案按段落/片段切片流式输出"""
        if not text:
            return
        # 按 markdown 段落分割，保持自然感
        import re
        parts = re.split(r'(\n\n+)', text)
        buffer = ""
        for part in parts:
            buffer += part
            # 累积到足够长度才输出一个 chunk
            if len(buffer) >= chunk_size or part.strip() == "":
                if buffer:
                    yield {"type": "answer_delta", "content": buffer}
                    buffer = ""
        if buffer:
            yield {"type": "answer_delta", "content": buffer}
    
    async def _run_workflow(self, scenario_name: str, query: str, session_id: str, server_id: Optional[str] = None) -> Dict[str, Any]:
        """使用 LangGraph 工作流执行查询"""
        logger.info(f"使用工作流执行查询，场景: {scenario_name}")
        
        result = await self.workflow_engine.run(scenario_name, query, session_id, server_id=server_id)
        
        # 补充工作流元信息
        result["mode"] = "workflow"
        result["scenario"] = scenario_name
        success = result.get("success", False)
        result["success"] = success
        result["is_success"] = success
        if "current_node" not in result:
            result["current_node"] = next(
                (
                    node for node, status in result.get("node_statuses", {}).items()
                    if status == "running"
                ),
                result.get("completed_nodes", [])[-1] if result.get("completed_nodes") else None
            )
        
        # 兼容字段
        if "thinking_process" not in result:
            # 构造工作流进度信息作为 thinking_process
            node_statuses = result.get("node_statuses", {})
            completed = result.get("completed_nodes", [])
            progress_lines = [f"### 工作流执行进度\n"]
            for node, status in node_statuses.items():
                icon = {"completed": "✅", "running": "🔄", "failed": "❌", "pending": "⬜"}.get(status, "⬜")
                progress_lines.append(f"{icon} {node}: {status}")
            result["thinking_process"] = "\n".join(progress_lines)
        
        return result
    
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any], max_retries: Optional[int] = None) -> Dict[str, Any]:
        """
        执行指定工具（带重试机制）
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数
            max_retries: 最大重试次数（可选）
        
        Returns:
            Dict: 执行结果
        """
        if tool_name not in self.mcp_adapter.get_tool_names():
            error_msg = f"工具不存在: {tool_name}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
        
        tool = self.mcp_adapter.get_tool(tool_name)
        if not tool:
            error_msg = f"获取工具失败: {tool_name}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
        
        # 使用错误处理器的重试机制
        result = await self.error_handler.retry_with_backoff(
            tool.ainvoke,
            arguments,
            tool_name=tool_name
        )
        
        return result
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """
        获取可用工具列表
        
        Returns:
            List[Dict]: 工具信息列表
        """
        tools = []
        for tool_name in self.mcp_adapter.get_tool_names():
            tool = self.mcp_adapter.get_tool(tool_name)
            if tool:
                tools.append({
                    "name": tool_name,
                    "description": tool.description or "无描述"
                })
        
        return tools
    
    def get_session_history(self, session_id: str, last_n: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        获取会话历史
        
        Args:
            session_id: 会话ID
            last_n: 获取最近N条消息
        
        Returns:
            List[Dict]: 消息列表
        """
        return self.memory.get_history(session_id, last_n)
    
    def get_recent_sessions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取最近的会话列表
        
        Args:
            limit: 返回的最大会话数
        
        Returns:
            List[Dict]: 会话信息
        """
        return self.memory.get_recent_sessions(limit)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            Dict: 统计信息
        """
        memory_stats = self.memory.get_session_stats()
        error_stats = self.error_handler.get_overall_stats()
        
        return {
            "memory": memory_stats,
            "errors": error_stats,
            "tool_count": len(self.tools),
            "max_iterations": self.agent_config.max_iterations
        }
    
    def clear_session(self, session_id: str):
        """清理指定会话"""
        self.memory.clear_session(session_id)
        logger.info(f"清理会话: {session_id}")
    
    def clear_all_sessions(self):
        """清理所有会话"""
        self.memory.clear_all_sessions()
        logger.info("清理所有会话")
    
    def reset_error_stats(self, tool_name: Optional[str] = None):
        """
        重置错误统计
        
        Args:
            tool_name: 指定工具，None则重置所有
        """
        self.error_handler.reset_stats(tool_name)
        logger.info(f"重置错误统计: {tool_name or 'all'}")
