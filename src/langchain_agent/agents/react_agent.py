"""
Perfa - LangChain Agent Module

@file: agents/react_agent.py
@desc: ReAct模式Agent实现
@author: Perfa Team
@date: 2026-03-18
"""

# 标准库导入
import asyncio
import json
import re
from typing import Dict, List, Any, Optional, Set
from datetime import datetime

# 第三方库导入
from langchain_agent.core.logger import get_logger
logger = get_logger()
from langchain_core.language_models import BaseLLM
from langchain_core.tools import BaseTool

# 本地模块导入
from langchain_agent.agents.base_agent import BaseAgent, AgentResponse, ToolCall


class ReActAgent(BaseAgent):
    """
    ReAct (Reasoning and Acting) Agent
    
    实现思考-行动-观察循环，适用于性能测试场景
    
    工作流程：
    1. 思考：分析用户查询，确定需要的工具
    2. 行动：调用MCP工具执行测试
    3. 观察：获取工具执行结果
    4. 重复直到完成任务或达到最大迭代次数
    """
    
    def __init__(
        self,
        llm: BaseLLM,
        tools: List[BaseTool],
        name: str = "ReActAgent",
        description: str = "ReAct模式性能测试Agent",
        max_iterations: int = 10
    ):
        """
        初始化ReAct Agent
        
        Args:
            llm: 语言模型实例
            tools: 工具列表
            name: Agent名称
            description: Agent描述
            max_iterations: 最大迭代次数
        """
        super().__init__(name, description)
        self.llm = llm
        self.tools = {tool.name: tool for tool in tools}
        self.max_iterations = max_iterations
        self.thoughts: List[Dict[str, Any]] = []
        
        logger.info(f"ReAct Agent初始化完成，可用工具数: {len(self.tools)}")
    
    async def run(self, query: str, **kwargs) -> AgentResponse:
        """
        执行ReAct循环
        
        Args:
            query: 用户查询
            **kwargs: 额外参数
                - session_id: 会话ID
                - context: 上下文信息
        
        Returns:
            AgentResponse: 执行结果
        """
        self._log_execution("info", f"开始执行ReAct循环，查询: {query}")
        self.start_time = datetime.now()
        
        session_id = kwargs.get("session_id", "default")
        context = kwargs.get("context", {})
        
        # 检查是否是直接工具调用格式（加速）
        direct_tool_match = re.match(r'^`?(\w+)`?\s*(.*)$', query.strip())
        if direct_tool_match and direct_tool_match.group(1) in self.tools:
            # 直接调用工具模式
            tool_name = direct_tool_match.group(1)
            tool_args_str = direct_tool_match.group(2).strip()
            
            self._log_execution("info", f"检测到直接工具调用: {tool_name}")
            
            # 解析参数（简单的键值对）
            tool_args = {}
            if tool_args_str:
                # 尝试解析 "key1=value1 key2=value2" 格式
                for pair in tool_args_str.split():
                    if '=' in pair:
                        key, value = pair.split('=', 1)
                        tool_args[key.strip()] = value.strip()
            
            # 执行工具调用
            tool_start = datetime.now()
            tool_result = await self._act(tool_name, tool_args)
            execution_time = (datetime.now() - tool_start).total_seconds()
            
            tool_call = ToolCall(
                tool_name=tool_name,
                arguments=tool_args,
                result=tool_result,
                execution_time=execution_time
            )
            
            total_time = self._calculate_execution_time()
            
            # 构建响应
            if tool_result.get("success"):
                result_str = f"工具 {tool_name} 执行成功\n结果: {tool_result.get('data', tool_result)}"
            else:
                result_str = f"工具 {tool_name} 执行失败\n错误: {tool_result.get('error', '未知错误')}"
            
            return AgentResponse(
                query=query,
                result=result_str,
                tool_calls=[tool_call],
                execution_time=total_time,
                tokens_used=0,
                is_success=tool_result.get("success", False),
                session_id=session_id
            )
        
        # 初始化状态
        self.thoughts.clear()
        tool_calls: List[ToolCall] = []
        iteration = 0
        final_result = ""
        thinking_log: List[str] = []  # 记录思考过程
        total_reasoning_time = 0.0  # 总推理时间
        used_tools: Set[str] = set()  # 跟踪已使用的工具
        
        try:
            # ReAct循环
            while iteration < self.max_iterations:
                iteration += 1
                iter_start = datetime.now()
                self._log_execution("debug", f"第 {iteration} 次迭代开始")
                
                # 思考：分析当前状态，决定下一步行动
                think_start = datetime.now()
                thought, full_reasoning = await self._think(query, tool_calls, context)
                think_time = (datetime.now() - think_start).total_seconds()
                total_reasoning_time += think_time
                logger.info(f"⏱️ 思考阶段耗时: {think_time:.2f}秒")
                
                self.thoughts.append(thought)
                
                # 记录完整的思考过程
                if full_reasoning:
                    thinking_log.append(f"### 思考 #{iteration}\n\n{full_reasoning}")
                
                # 记录思考结果摘要
                if thought.get("is_final"):
                    self._log_execution("info", f"得到最终结果")
                elif "tool_name" in thought:
                    self._log_execution("info", f"决定调用工具: {thought['tool_name']}")
                else:
                    self._log_execution("warning", f"思考结果格式异常: {thought}")
                
                # 检查是否已完成
                if thought.get("is_final", False):
                    final_result = thought.get("content", "任务已完成")
                    self._log_execution("info", "ReAct循环完成，得到最终结果")
                    break
                
                # 行动：调用工具
                if "tool_name" in thought and "tool_args" in thought:
                    tool_name = thought["tool_name"]
                    tool_args = thought["tool_args"]
                    
                    self._log_execution("info", f"调用工具: {tool_name}，参数: {tool_args}")
                    
                    # 执行工具调用
                    tool_start = datetime.now()
                    tool_result = await self._act(tool_name, tool_args)
                    execution_time = (datetime.now() - tool_start).total_seconds()
                    
                    # 记录工具调用
                    tool_call = ToolCall(
                        tool_name=tool_name,
                        arguments=tool_args,
                        result=tool_result,
                        execution_time=execution_time
                    )
                    tool_calls.append(tool_call)
                    
                    self._log_execution("info", f"工具调用完成: {tool_name}，耗时: {execution_time:.2f}秒")
                    
                    # 如果工具调用失败，记录错误
                    if not tool_result.get("success", False):
                        error_msg = tool_result.get("error", "未知错误")
                        self._log_execution("warning", f"工具调用失败: {tool_name} - {error_msg}")
                
                # 记录本次迭代总耗时
                iter_time = (datetime.now() - iter_start).total_seconds()
                logger.info(f"⏱️ 第{iteration}次迭代总耗时: {iter_time:.2f}秒")
                
                # 避免过快循环
                await asyncio.sleep(0.1)
            
            # 如果达到最大迭代次数仍未完成
            if iteration >= self.max_iterations and not final_result:
                final_result = f"达到最大迭代次数({self.max_iterations})仍未完成，已返回部分结果"
                self._log_execution("warning", final_result)
            
            # 计算总执行时间
            total_time = self._calculate_execution_time()
            
            # 构建思考过程摘要
            thinking_summary = "\n\n".join(thinking_log) if thinking_log else None
            
            # 构建响应
            response = AgentResponse(
                query=query,
                result=final_result or "未生成结果",
                tool_calls=tool_calls,
                execution_time=total_time,
                tokens_used=0,  # TODO: 从LLM响应中获取实际token使用量
                is_success=True,
                session_id=session_id,
                thinking_process=thinking_summary,
                reasoning_time=total_reasoning_time
            )
            
            self._log_execution("info", f"ReAct执行完成，总耗时: {total_time:.2f}秒，工具调用: {len(tool_calls)}次")
            return response
            
        except Exception as e:
            logger.error(f"ReAct执行异常: {str(e)}")
            self._log_execution("error", f"执行异常: {str(e)}")
            
            total_time = self._calculate_execution_time()
            
            return AgentResponse(
                query=query,
                result="执行过程中发生错误",
                tool_calls=tool_calls,
                execution_time=total_time,
                tokens_used=0,
                is_success=False,
                error_message=str(e),
                session_id=session_id
            )
    
    async def _think(self, query: str, tool_calls: List[ToolCall], context: Dict[str, Any]) -> tuple:
        """
        思考：分析当前状态，决定下一步行动（流式输出完整推理过程）
        
        Args:
            query: 用户查询
            tool_calls: 已执行的工具调用列表
            context: 上下文信息
                - session_history: 会话历史记录
        
        Returns:
            tuple: (思考结果字典, 完整推理内容字符串)
        """
        # 构建思考提示
        tools_description = self._format_tools_description()
        
        # 构建对话历史
        history = self._format_history(tool_calls)
        
        # 构建会话上下文（从之前的对话中提取关键信息）
        session_context = self._format_session_context(context)
        
        prompt = f"""
你是一位专业的服务器性能测试助手。请根据用户需求和历史操作，决定下一步行动。

## 可用工具
{tools_description}

## 会话上下文（之前的对话）
{session_context}

## 用户需求
{query}

## 已完成的操作（本次查询）
{history}

## 当前状态
- 已执行步骤数: {len(tool_calls)}
- 最新结果: {tool_calls[-1].result if tool_calls else "无"}

## 重要规则

### 1. 利用上下文信息
- 仔细查看"会话上下文"，了解之前的对话内容
- 如果之前的对话中提到了 task_id、server_id 等信息，直接使用！
- 不要重复查询已知的信息

### 2. 避免重复操作
- 不要重复调用已执行的工具
- 利用已有信息继续下一步

### 3. 工具选择指南

**执行性能测试：**
- `run_benchmark` - 启动测试（异步，返回task_id）
  - 参数: server_id, test_name, params(可选)
  - 返回: {{"task_id": "xxx", "status": "started"}}
  - ⚠️ 测试是异步执行的，需要后续获取结果！

**获取测试结果：**
- `get_benchmark_result` - 获取指定任务结果
  - 参数: server_id, task_id
  - 在run_benchmark返回task_id后使用此工具
- `get_benchmark_status` - 查询任务状态
  - 参数: server_id, task_id

**查询历史记录：**
- `list_benchmark_history` - 查询历史测试记录
  - 仅用于查看过去的测试，不用于获取刚启动的测试

### 4. 正确的测试流程

```
用户："测试superpi"
→ list_servers (获取server_id)
→ run_benchmark(test_name='superpi') 
  返回: {{"task_id": "abc-123", "status": "started"}}
→ get_benchmark_result(task_id='abc-123') 
  获取实际测试结果
→ 生成最终答案
```

**错误示例：**
```
run_benchmark → list_benchmark_history ❌
（测试刚启动，还没有历史记录）
```

### 5. 及时完成
如果已有足够信息回答用户问题，直接给出最终答案。

---

**请先思考以下问题，然后给出决策：**
1. 用户的核心需求是什么？
2. 会话上下文中有哪些可用信息？
3. 当前已完成哪些步骤？
4. 还需要什么信息或操作？
5. 下一步应该调用什么工具？

请以JSON格式回复：
- 完成任务: {{"is_final": true, "content": "最终答案（Markdown格式）"}}
- 调用工具: {{"is_final": false, "tool_name": "工具名", "tool_args": {{参数}}}}
"""
        
        try:
            # 调用LLM进行思考（流式输出）
            llm_start = datetime.now()
            self._log_execution("debug", "调用LLM进行思考")
            
            # 使用流式输出
            print("\n💭 思考中...", flush=True)
            content_chunks = []
            
            async for chunk in self.llm.astream(prompt):
                if hasattr(chunk, "content"):
                    chunk_text = chunk.content
                else:
                    chunk_text = str(chunk)
                
                # 实时打印思考过程
                print(chunk_text, end="", flush=True)
                content_chunks.append(chunk_text)
            
            print()  # 换行
            
            llm_time = (datetime.now() - llm_start).total_seconds()
            logger.info(f"⏱️ LLM推理耗时: {llm_time:.2f}秒")
            
            # 合并完整内容
            content = "".join(content_chunks)
            
            logger.debug(f"LLM完整响应: {content[:200]}...")
            
            # 尝试提取JSON（处理markdown代码块）
            
            # 尝试提取markdown代码块中的JSON
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # 尝试直接提取JSON
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                json_str = json_match.group(0) if json_match else content
            
            try:
                thought = json.loads(json_str)
                logger.debug(f"成功解析思考结果: {thought}")
                
                # 确保返回的字典有必要的字段
                if "is_final" not in thought:
                    thought["is_final"] = True
                if "content" not in thought and thought.get("is_final"):
                    thought["content"] = content
                    
                return thought, content  # 返回思考结果和完整推理内容
            except json.JSONDecodeError as e:
                logger.warning(f"JSON解析失败: {e}")
                # 如果无法解析JSON，返回默认结构
                return {
                    "is_final": True,
                    "content": content
                }, content
                
        except Exception as e:
            logger.error(f"思考过程失败: {str(e)}")
            return {
                "is_final": True,
                "content": f"思考过程失败，无法继续: {str(e)}"
            }, ""
    
    async def _act(self, tool_name: str, tool_args: Any) -> Dict[str, Any]:
        """
        行动：调用工具
        
        Args:
            tool_name: 工具名称
            tool_args: 工具参数（可以是字典、None或其他）
        
        Returns:
            Dict: 工具执行结果
        """
        if tool_name not in self.tools:
            return {
                "success": False,
                "error": f"工具不存在: {tool_name}"
            }
        
        tool = self.tools[tool_name]
        
        # 确保参数是字典
        if tool_args is None:
            tool_args = {}
        elif not isinstance(tool_args, dict):
            tool_args = {}
        
        try:
            # 调用工具（异步方式）
            if hasattr(tool, 'ainvoke'):
                # LangChain 1.0+ 使用 ainvoke
                result = await tool.ainvoke(tool_args)
            elif hasattr(tool, 'coroutine'):
                # 使用 coroutine
                result = await tool.coroutine(tool_args)
            else:
                # 同步调用
                result = tool.run(tool_args)
            
            # 处理返回结果
            # MCP 工具返回的可能是：
            # 1. 字典（已解析）- 直接返回
            # 2. JSON 字符串 - 需要解析
            # 3. 普通字符串 - 包装返回
            if isinstance(result, dict):
                return result
            elif isinstance(result, str):
                # 尝试解析 JSON
                try:
                    parsed = json.loads(result)
                    if isinstance(parsed, dict):
                        return parsed
                except (json.JSONDecodeError, TypeError):
                    pass
                # 如果不是 JSON，返回文本结果
                return {
                    "success": True,
                    "data": result
                }
            else:
                return {
                    "success": True,
                    "data": result
                }
            
        except Exception as e:
            logger.error(f"工具调用失败 {tool_name}: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e)
            }
    
    def _format_tools_description(self) -> str:
        """格式化工具描述（包含参数说明）"""
        descriptions = []
        for name, tool in self.tools.items():
            desc = tool.description or "无描述"
            
            # 添加参数说明
            param_info = ""
            if hasattr(tool, 'args_schema') and tool.args_schema:
                # 从Pydantic模型获取参数
                schema = tool.args_schema.model_json_schema()
                properties = schema.get('properties', {})
                required = schema.get('required', [])
                
                if properties:
                    params = []
                    for param_name, param_def in properties.items():
                        param_desc = param_def.get('description', '')
                        is_required = param_name in required
                        req_mark = "*" if is_required else ""
                        params.append(f"  - {param_name}{req_mark}: {param_desc}")
                    
                    param_info = "\n  参数:\n" + "\n".join(params)
            
            descriptions.append(f"**{name}**: {desc}{param_info}")
        
        return "\n\n".join(descriptions)
    
    def _format_history(self, tool_calls: List[ToolCall]) -> str:
        """格式化历史记录（保留完整结果）"""
        if not tool_calls:
            return "暂无历史操作"
        
        history = []
        for i, call in enumerate(tool_calls, 1):
            # 智能截断：保留关键信息
            result_str = str(call.result)
            if isinstance(call.result, dict):
                # 提取关键信息，特别是 task_id
                result = call.result
                
                # 特殊处理：如果结果包含 task_id，要明确显示
                if 'task_id' in result:
                    result_str = f"✅ **task_id**: `{result['task_id']}`\n"
                    if 'status' in result:
                        result_str += f"- 状态: {result['status']}\n"
                    if 'test_name' in result:
                        result_str += f"- 测试: {result['test_name']}\n"
                    if 'message' in result:
                        result_str += f"- 消息: {result['message']}\n"
                elif 'servers' in result:
                    # list_servers结果
                    servers = result.get('servers', [])
                    result_str = f"找到 {len(servers)} 台服务器:\n"
                    for s in servers[:3]:
                        result_str += f"  - {s.get('ip', 'unknown')} (ID: {s.get('id', 'unknown')})\n"
                elif 'tools' in result:
                    # list_tools结果
                    tools = result.get('tools', [])
                    result_str = f"找到 {len(tools)} 个工具: " + ", ".join([t.get('name', 'unknown') for t in tools[:5]])
                elif 'results' in result:
                    # list_benchmark_history 结果
                    results = result.get('results', [])
                    result_str = f"找到 {len(results)} 条测试记录\n"
                    if results:
                        # 显示最近的记录
                        latest = results[0] if results else {}
                        result_str += f"  最近: task_id={latest.get('task_id', 'unknown')}, status={latest.get('status', 'unknown')}\n"
                elif 'success' in result:
                    # 其他结果
                    success = result.get('success')
                    if success:
                        result_str = "✅ 成功\n"
                        # 显示其他关键字段
                        for key in ['status', 'message', 'count']:
                            if key in result:
                                result_str += f"- {key}: {result[key]}\n"
                    else:
                        error = result.get('error', '未知错误')
                        result_str = f"❌ 失败: {error}\n"
                else:
                    # 其他情况，截断显示
                    result_str = str(result)[:500]
            else:
                result_str = result_str[:300] if len(result_str) > 300 else result_str
            
            history.append(
                f"**步骤{i}**: 调用 `{call.tool_name}`\n"
                f"- 参数: {call.arguments}\n"
                f"- 结果:\n{result_str}\n"
                f"- 耗时: {call.execution_time:.2f}秒"
            )
        
        return "\n\n".join(history)
    
    def _format_session_context(self, context: Dict[str, Any]) -> str:
        """
        格式化会话上下文（从之前的对话中提取关键信息）
        
        Args:
            context: 包含 session_history 的上下文
        
        Returns:
            str: 格式化的会话上下文
        """
        if not context:
            return "暂无会话上下文"
        
        session_history = context.get("session_history", [])
        if not session_history:
            return "暂无会话上下文"
        
        # 提取关键信息
        context_parts = []
        key_info = {
            "server_ids": set(),
            "task_ids": set(),
            "test_names": set(),
            "recent_queries": []
        }
        
        for msg in session_history[-10:]:  # 最近10条消息
            role = msg.get("role", "")
            content = msg.get("content", "")
            metadata = msg.get("metadata", {})
            
            if role == "user":
                # 记录最近的用户查询
                key_info["recent_queries"].append(content[:100])
            elif role == "assistant":
                # 提取关键信息
                import re
                # 提取 task_id
                task_matches = re.findall(r'task_id["\s:]+([a-f0-9-]{36}|[a-f0-9]{32})', content, re.IGNORECASE)
                key_info["task_ids"].update(task_matches)
                
                # 提取 server_id
                server_matches = re.findall(r'server_id["\s:]+([a-f0-9-]{36}|[a-f0-9]{32})', content, re.IGNORECASE)
                key_info["server_ids"].update(server_matches)
                
                # 提取测试名称
                test_matches = re.findall(r'(superpi|unixbench|stream|fio|mlc|hping3)', content, re.IGNORECASE)
                key_info["test_names"].update([t.lower() for t in test_matches])
                
            elif role == "tool":
                # 从工具调用元数据中提取信息
                tool_name = metadata.get("tool_name", "")
                args = metadata.get("arguments", {})
                if isinstance(args, dict):
                    if "task_id" in args:
                        key_info["task_ids"].add(args["task_id"])
                    if "server_id" in args:
                        key_info["server_ids"].add(args["server_id"])
                    if "test_name" in args:
                        key_info["test_names"].add(args["test_name"])
        
        # 构建上下文摘要
        if key_info["server_ids"]:
            context_parts.append(f"**已知服务器ID**: {', '.join(key_info['server_ids'])}")
        if key_info["task_ids"]:
            context_parts.append(f"**已知任务ID**: {', '.join(key_info['task_ids'])}")
        if key_info["test_names"]:
            context_parts.append(f"**已知测试类型**: {', '.join(key_info['test_names'])}")
        if key_info["recent_queries"]:
            context_parts.append(f"**最近的用户请求**: {key_info['recent_queries'][-1]}")
        
        if context_parts:
            return "\n".join(context_parts)
        else:
            return "暂无关键上下文信息"
    
    def reset(self):
        """重置Agent状态"""
        super().reset()
        self.thoughts.clear()
        logger.info("ReAct Agent状态已重置")
