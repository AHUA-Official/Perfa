"""
Perfa - LangChain Agent Module

@file: workflows/scenarios/full_assessment.py
@desc: 全面性能评估场景 — 默认短测全项测试
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


async def _run_iperf3_network(state: WorkflowState, *, tools: dict = None) -> dict:
    host = state.get("iperf3_target_host") or "127.0.0.1"
    return await run_benchmark(
        state,
        test_name="iperf3",
        test_params={"host": host, "time": 10, "parallel": 1, "auto_server": host in {"127.0.0.1", "localhost", "::1"}},
        tools=tools,
        result_key="network_test",
    )


def build_full_assessment_graph(tools: dict, llm=None):
    """
    构建全面性能评估场景图
    
    流程:
    [环境检查] → [选择服务器] → [检查工具] → [安装缺失工具]
         → [CPU测试] → [内存测试] → [磁盘IO测试] → [网络测试]
         → [收集所有结果] → [生成综合报告]
    """
    graph = StateGraph(WorkflowState)
    
    required_tools = ["sysbench", "fio", "iperf3", "hping3", "openssl_speed"]
    
    # 添加节点
    graph.add_node("check_environment", make_node(check_environment, tools=tools))
    graph.add_node("select_server", make_node(select_server, tools=tools))
    graph.add_node("check_tools", make_node(check_tools, required_tools=required_tools, tools=tools))
    graph.add_node("install_tools", make_node(install_tools, tools=tools))
    graph.add_node("prepare_iperf3_target", make_node(_prepare_iperf3_target, tools=tools))
    
    graph.add_node("cpu_test", make_node(run_benchmark, test_name="sysbench_cpu", tools=tools))
    graph.add_node("memory_test", make_node(run_benchmark, test_name="sysbench_memory", tools=tools))
    graph.add_node("disk_test", make_node(run_benchmark, test_name="fio", tools=tools))
    graph.add_node("network_test", make_node(_run_iperf3_network, tools=tools))
    
    graph.add_node("collect_results", make_node(collect_results))
    graph.add_node("generate_report", make_node(generate_report, llm=llm, tools=tools))
    graph.add_node("handle_error", make_node(handle_error))
    
    # 定义边
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
        {
            "handle_error": "handle_error",
            "install_tools": "install_tools",
            "proceed": "cpu_test",
        }
    )
    graph.add_conditional_edges(
        "install_tools",
        route_after_install,
        {"handle_error": "handle_error", "proceed": "cpu_test"}
    )

    graph.add_edge("cpu_test", "memory_test")
    graph.add_edge("memory_test", "disk_test")
    graph.add_edge("disk_test", "prepare_iperf3_target")
    graph.add_edge("prepare_iperf3_target", "network_test")
    
    graph.add_edge("network_test", "collect_results")
    graph.add_edge("collect_results", "generate_report")
    graph.add_edge("generate_report", END)
    graph.add_edge("handle_error", END)
    
    return graph.compile()
