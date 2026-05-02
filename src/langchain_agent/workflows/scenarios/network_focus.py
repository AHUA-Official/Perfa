"""
Perfa - LangChain Agent Module

@file: workflows/scenarios/network_focus.py
@desc: 网络专项评估场景 — 短测优先（iperf3 + hping3）
@author: Perfa Team
@date: 2026-04-27
"""

from langgraph.graph import StateGraph, END

from langchain_agent.workflows.state import WorkflowState
from langchain_agent.workflows.nodes import (
    make_node,
    check_environment,
    select_server,
    check_tools,
    install_tools,
    run_benchmark,
    collect_results,
    generate_report,
    handle_error,
    route_after_tool_check,
    route_after_server_selection,
    route_after_install,
)


async def _prepare_iperf3_target(state: WorkflowState, *, tools: dict = None) -> dict:
    host = state.get("iperf3_target_host") or "127.0.0.1"
    server_id = state.get("iperf3_target_server_id") or state.get("server_id")
    return {
        "iperf3_target_host": host,
        "iperf3_target_server_id": server_id,
        "node_statuses": {**state.get("node_statuses", {}), "prepare_iperf3_target": "completed"},
        "current_node": "prepare_iperf3_target",
    }


async def _run_iperf3_throughput(state: WorkflowState, *, tools: dict = None) -> dict:
    host = state.get("iperf3_target_host") or "127.0.0.1"
    return await run_benchmark(
        state,
        test_name="iperf3",
        test_params={"host": host, "time": 10, "parallel": 1, "auto_server": host in {"127.0.0.1", "localhost", "::1"}},
        tools=tools,
        result_key="iperf3_throughput",
    )


def build_network_focus_graph(tools: dict, llm=None):
    """
    构建网络专项评估场景图
    
    流程: [环境检查] → [选择服务器] → [检查工具] → [安装缺失工具]
         → [iperf3 吞吐测试] → [hping3 延迟测试] → [收集结果] → [网络专项报告]
    """
    graph = StateGraph(WorkflowState)
    
    required_tools = ["iperf3", "hping3"]
    
    graph.add_node("check_environment", make_node(check_environment, tools=tools))
    graph.add_node("select_server", make_node(select_server, tools=tools))
    graph.add_node("check_tools", make_node(check_tools, required_tools=required_tools, tools=tools))
    graph.add_node("install_tools", make_node(install_tools, tools=tools))
    graph.add_node("prepare_iperf3_target", make_node(_prepare_iperf3_target, tools=tools))
    graph.add_node("iperf3_throughput", make_node(_run_iperf3_throughput, tools=tools))
    graph.add_node("hping3_latency", make_node(run_benchmark,
        test_name="hping3", test_params={"count": 20, "interval": 1},
        tools=tools, result_key="hping3_latency"))
    
    graph.add_node("collect_results", make_node(collect_results))
    graph.add_node("generate_report", make_node(generate_report, llm=llm, tools=tools))
    graph.add_node("handle_error", make_node(handle_error))
    
    graph.set_entry_point("check_environment")
    graph.add_edge("check_environment", "select_server")
    graph.add_conditional_edges(
        "select_server",
        route_after_server_selection,
        {"handle_error": "handle_error", "proceed": "check_tools"}
    )
    graph.add_conditional_edges(
        "check_tools",
        route_after_tool_check,
        {"handle_error": "handle_error", "install_tools": "install_tools", "proceed": "prepare_iperf3_target"}
    )
    graph.add_conditional_edges(
        "install_tools",
        route_after_install,
        {"handle_error": "handle_error", "proceed": "prepare_iperf3_target"}
    )
    graph.add_edge("prepare_iperf3_target", "iperf3_throughput")
    graph.add_edge("iperf3_throughput", "hping3_latency")
    graph.add_edge("hping3_latency", "collect_results")
    graph.add_edge("collect_results", "generate_report")
    graph.add_edge("generate_report", END)
    graph.add_edge("handle_error", END)
    
    return graph.compile()
