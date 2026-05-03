"""
Perfa - LangChain Agent Module

@file: workflows/graph_builder.py
@desc: LangGraph 工作流引擎 — 统一构建和注册所有场景图
@author: Perfa Team
@date: 2026-04-27
"""

from typing import Dict, Any, Optional

from langchain_agent.core.logger import get_logger
logger = get_logger()

from langchain_agent.workflows.state import WorkflowState, create_initial_state
from langchain_agent.workflows.router import ScenarioRouter, Scenario, SCENARIOS
from langchain_agent.workflows.scenarios.quick_test import build_quick_test_graph
from langchain_agent.workflows.scenarios.full_assessment import build_full_assessment_graph
from langchain_agent.workflows.scenarios.cpu_focus import build_cpu_focus_graph
from langchain_agent.workflows.scenarios.storage_focus import build_storage_focus_graph
from langchain_agent.workflows.scenarios.network_focus import build_network_focus_graph


class WorkflowEngine:
    """
    工作流引擎
    
    统一管理所有场景的 LangGraph 图，提供：
    - 场景路由（LLM 意图识别 → 场景选择）
    - 图构建和编译
    - 工作流执行
    """
    
    def __init__(self, tools: dict, llm=None, confidence_threshold: float = 0.7):
        """
        初始化工作流引擎
        
        Args:
            tools: MCP 工具字典 {tool_name: BaseTool}
            llm: LLM 实例（用于路由和报告生成）
            confidence_threshold: 路由置信度阈值
        """
        self.tools = tools
        self.llm = llm
        
        # 场景路由器
        self.router = ScenarioRouter(llm, confidence_threshold)
        
        # 构建所有场景图
        self.graphs = {}
        self._build_all_graphs()
        
        logger.info(f"工作流引擎初始化完成，已注册 {len(self.graphs)} 个场景")
    
    def _build_all_graphs(self):
        """构建并编译所有场景图"""
        try:
            self.graphs["quick_test"] = build_quick_test_graph(self.tools, self.llm)
            logger.info("✅ quick_test 场景图构建完成")
        except Exception as e:
            logger.error(f"❌ quick_test 场景图构建失败: {e}")
        
        try:
            self.graphs["full_assessment"] = build_full_assessment_graph(self.tools, self.llm)
            logger.info("✅ full_assessment 场景图构建完成")
        except Exception as e:
            logger.error(f"❌ full_assessment 场景图构建失败: {e}")
        
        try:
            self.graphs["cpu_focus"] = build_cpu_focus_graph(self.tools, self.llm)
            logger.info("✅ cpu_focus 场景图构建完成")
        except Exception as e:
            logger.error(f"❌ cpu_focus 场景图构建失败: {e}")
        
        try:
            self.graphs["storage_focus"] = build_storage_focus_graph(self.tools, self.llm)
            logger.info("✅ storage_focus 场景图构建完成")
        except Exception as e:
            logger.error(f"❌ storage_focus 场景图构建失败: {e}")
        
        try:
            self.graphs["network_focus"] = build_network_focus_graph(self.tools, self.llm)
            logger.info("✅ network_focus 场景图构建完成")
        except Exception as e:
            logger.error(f"❌ network_focus 场景图构建失败: {e}")
    
    async def route(self, query: str) -> Scenario:
        """
        路由用户查询到对应场景
        
        Args:
            query: 用户查询
            
        Returns:
            Scenario: 匹配的场景
        """
        return await self.router.route(query)
    
    async def run(self, scenario_name: str, query: str, session_id: str, server_id: Optional[str] = None) -> Dict[str, Any]:
        """
        执行指定场景的工作流
        
        Args:
            scenario_name: 场景名称
            query: 用户查询
            session_id: 会话 ID
            
        Returns:
            Dict: 工作流执行结果
        """
        import time
        start_time = time.time()
        
        logger.info(f"开始执行工作流，场景: {scenario_name}，查询: {query[:100]}")
        
        # 检查场景是否存在
        if scenario_name not in self.graphs:
            error_msg = f"未知场景: {scenario_name}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "scenario": scenario_name,
            }
        
        # 创建初始状态
        initial_state = create_initial_state(query, session_id, scenario_name)
        if server_id:
            initial_state["server_id"] = server_id
        
        try:
            # 执行工作流
            graph = self.graphs[scenario_name]
            final_state = await graph.ainvoke(initial_state)
            
            execution_time = time.time() - start_time
            
            # 提取结果
            result = {
                "success": final_state.get("status") == "completed",
                "scenario": scenario_name,
                "session_id": session_id,
                "query": query,
                "result": final_state.get("final_report", "未生成报告"),
                "execution_time": execution_time,
                "tool_calls": self._extract_tool_calls(final_state),
                "task_ids": final_state.get("task_ids", {}),
                "results": final_state.get("results", {}),
                "errors": final_state.get("errors", []),
                "knowledge_matches": final_state.get("knowledge_matches", []),
                "node_statuses": final_state.get("node_statuses", {}),
                "completed_nodes": final_state.get("completed_nodes", []),
                "server_id": final_state.get("server_id"),
                "server_ip": final_state.get("server_ip"),
            }
            
            logger.info(f"工作流执行完成，场景: {scenario_name}，耗时: {execution_time:.2f}s")
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"工作流执行异常: {e}")
            return {
                "success": False,
                "scenario": scenario_name,
                "session_id": session_id,
                "query": query,
                "error": str(e),
                "execution_time": execution_time,
                "tool_calls": [],
                "errors": [{"node": "workflow", "error": str(e)}],
            }
    
    async def run_with_stream(self, scenario_name: str, query: str, session_id: str):
        """
        流式执行工作流，逐步 yield 进度更新
        
        Yields:
            Dict: 进度更新事件
        """
        logger.info(f"开始流式工作流，场景: {scenario_name}")
        
        if scenario_name not in self.graphs:
            yield {"type": "error", "data": f"未知场景: {scenario_name}"}
            return
        
        initial_state = create_initial_state(query, session_id, scenario_name)
        graph = self.graphs[scenario_name]
        
        try:
            # 使用 astream 逐步获取状态更新
            async for event in graph.astream(initial_state):
                # LangGraph astream 返回 {node_name: state_update} 格式
                for node_name, state_update in event.items():
                    yield {
                        "type": "node_update",
                        "node": node_name,
                        "data": state_update,
                    }
            
            # 获取最终状态
            final_state = await graph.ainvoke(initial_state)
            yield {
                "type": "completed",
                "data": {
                    "result": final_state.get("final_report", ""),
                    "status": final_state.get("status", ""),
                    "node_statuses": final_state.get("node_statuses", {}),
                }
            }
            
        except Exception as e:
            yield {"type": "error", "data": str(e)}
    
    def _extract_tool_calls(self, final_state: dict) -> list:
        """从最终状态中提取工具调用记录"""
        tool_calls = []
        results = final_state.get("results", {})
        task_ids = final_state.get("task_ids", {})
        
        for test_name, result in results.items():
            tool_calls.append({
                "tool_name": "run_benchmark",
                "arguments": {
                    "test_name": test_name,
                    "task_id": task_ids.get(test_name, ""),
                },
                "result": result,
                "execution_time": 0,  # 各测试的耗时在 result 中
            })
        
        return tool_calls
    
    def get_available_scenarios(self) -> list:
        """获取可用场景列表"""
        return list(self.graphs.keys())
