"""
Perfa - LangChain Agent Module

@file: workflows/state.py
@desc: LangGraph 工作流状态定义
@author: Perfa Team
@date: 2026-04-27
"""

from typing import TypedDict, Annotated, List, Dict, Any, Optional
from langgraph.graph.message import add_messages


class WorkflowState(TypedDict, total=False):
    """
    LangGraph 工作流共享状态
    
    所有节点共享此状态，通过 LangGraph 的状态机机制自动传递和更新。
    使用 total=False 使得所有字段都是可选的（适配不同场景的需求差异）。
    """
    # ========== 输入 ==========
    query: str                            # 原始用户查询
    session_id: str                       # 会话 ID
    scenario: str                         # 场景名称 (quick_test/full_assessment/cpu_focus/storage_focus/network_focus)
    
    # ========== 执行上下文 ==========
    server_id: Optional[str]              # 目标服务器 ID
    server_ip: Optional[str]              # 目标服务器 IP
    iperf3_target_host: Optional[str]     # iperf3 目标地址
    iperf3_target_server_id: Optional[str]# iperf3 目标服务器 ID
    agent_id: Optional[str]               # Agent ID
    agent_status: Optional[str]           # Agent 运行状态
    available_tools: List[str]            # 已安装的工具列表
    missing_tools: List[str]              # 需要安装的工具
    
    # ========== 任务追踪 ==========
    task_ids: Dict[str, str]              # {test_name: task_id} 测试任务 ID 映射
    results: Dict[str, Any]               # {test_name: result_data} 测试结果映射
    errors: List[Dict[str, Any]]          # 错误列表 [{node, error, detail}]
    
    # ========== 工作流进度 ==========
    current_node: str                     # 当前执行的节点名
    completed_nodes: List[str]            # 已完成的节点列表
    node_statuses: Dict[str, str]         # {node_name: pending/running/completed/failed}
    
    # ========== 输出 ==========
    messages: Annotated[list, add_messages]  # LangGraph 消息历史（自动合并）
    final_report: Optional[str]           # 最终报告
    status: str                           # workflow 状态: running/completed/failed


def create_initial_state(query: str, session_id: str, scenario: str) -> WorkflowState:
    """创建初始工作流状态"""
    return WorkflowState(
        query=query,
        session_id=session_id,
        scenario=scenario,
        server_id=None,
        server_ip=None,
        iperf3_target_host=None,
        iperf3_target_server_id=None,
        agent_id=None,
        agent_status=None,
        available_tools=[],
        missing_tools=[],
        task_ids={},
        results={},
        errors=[],
        current_node="",
        completed_nodes=[],
        node_statuses={},
        messages=[],
        final_report=None,
        status="running",
    )
