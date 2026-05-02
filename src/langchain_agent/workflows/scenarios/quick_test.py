"""
Perfa - LangChain Agent Module

@file: workflows/scenarios/quick_test.py
@desc: 快速测试场景 — 单项测试，5步完成
@author: Perfa Team
@date: 2026-04-27
"""

from langgraph.graph import StateGraph, END

from langchain_agent.workflows.state import WorkflowState
from langchain_agent.workflows.nodes import (
    make_node,
    check_environment,
    select_server,
    run_benchmark,
    collect_results,
    generate_report,
    handle_error,
    route_after_server_selection,
)


def build_quick_test_graph(tools: dict, llm=None):
    """
    构建快速测试场景图
    
    流程: [环境检查] → [选择服务器] → [执行单一测试] → [获取结果] → [生成摘要]
    """
    graph = StateGraph(WorkflowState)
    
    # 添加节点（使用 make_node 包装 async 函数）
    graph.add_node("check_environment", make_node(check_environment, tools=tools))
    graph.add_node("select_server", make_node(select_server, tools=tools))
    graph.add_node("run_test", make_node(_run_quick_test, tools=tools))
    graph.add_node("collect_results", make_node(collect_results))
    graph.add_node("generate_report", make_node(generate_report, llm=llm, tools=tools))
    graph.add_node("handle_error", make_node(handle_error))
    
    # 定义边
    graph.set_entry_point("check_environment")
    graph.add_edge("check_environment", "select_server")
    graph.add_conditional_edges(
        "select_server",
        route_after_server_selection,
        {"handle_error": "handle_error", "proceed": "run_test"}
    )
    graph.add_edge("run_test", "collect_results")
    graph.add_edge("collect_results", "generate_report")
    graph.add_edge("generate_report", END)
    graph.add_edge("handle_error", END)
    
    return graph.compile()


async def _run_quick_test(state: WorkflowState, *, tools: dict = None) -> dict:
    """
    快速测试的执行节点
    
    从用户查询中识别要运行的测试类型，执行单项测试。
    """
    query = state.get("query", "").lower()
    test_name = _infer_test_name(query)
    logger.info(f"[QuickTest] 推断测试类型: {test_name}")
    
    return await run_benchmark(state, test_name=test_name, tools=tools)


def _infer_test_name(query: str) -> str:
    """从查询中推断测试名称"""
    query_lower = query.lower()
    
    test_keywords = {
        "unixbench": ["unixbench", "cpu综合", "cpu综合性能"],
        "superpi": ["superpi", "super_pi", "pi计算", "浮点"],
        "stream": ["stream", "内存带宽", "内存性能"],
        "fio": ["fio", "磁盘", "io", "硬盘", "存储io"],
        "mlc": ["mlc", "内存延迟", "延迟测试"],
        "hping3": ["hping3", "网络延迟", "网络", "ping", "丢包"],
    }
    
    for test_name, keywords in test_keywords.items():
        for kw in keywords:
            if kw in query_lower:
                return test_name
    
    return "unixbench"


from langchain_agent.core.logger import get_logger
logger = get_logger()
