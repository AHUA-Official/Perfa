"""
Perfa - LangChain Agent Module

@file: workflows/scenarios/cpu_focus.py
@desc: CPU 专项评估场景 — 短测优先（sysbench + OpenSSL）
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


def build_cpu_focus_graph(tools: dict, llm=None):
    """
    构建 CPU 专项评估场景图
    
    流程: [环境检查] → [选择服务器] → [检查工具] → [安装缺失工具]
         → [sysbench CPU] → [sysbench Threads] → [OpenSSL Speed] → [收集结果] → [CPU专项报告]
    """
    graph = StateGraph(WorkflowState)
    
    required_tools = ["sysbench", "openssl_speed"]
    
    graph.add_node("check_environment", make_node(check_environment, tools=tools))
    graph.add_node("select_server", make_node(select_server, tools=tools))
    graph.add_node("check_tools", make_node(check_tools, required_tools=required_tools, tools=tools))
    graph.add_node("install_tools", make_node(install_tools, tools=tools))
    graph.add_node("sysbench_cpu_test", make_node(run_benchmark, test_name="sysbench_cpu", tools=tools))
    graph.add_node("sysbench_threads_test", make_node(run_benchmark, test_name="sysbench_threads", tools=tools))
    graph.add_node("openssl_speed_test", make_node(run_benchmark, test_name="openssl_speed", tools=tools))
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
        {"handle_error": "handle_error", "install_tools": "install_tools", "proceed": "sysbench_cpu_test"}
    )
    graph.add_conditional_edges(
        "install_tools",
        route_after_install,
        {"handle_error": "handle_error", "proceed": "sysbench_cpu_test"}
    )
    graph.add_edge("sysbench_cpu_test", "sysbench_threads_test")
    graph.add_edge("sysbench_threads_test", "openssl_speed_test")
    graph.add_edge("openssl_speed_test", "collect_results")
    graph.add_edge("collect_results", "generate_report")
    graph.add_edge("generate_report", END)
    graph.add_edge("handle_error", END)
    
    return graph.compile()
