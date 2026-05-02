"""
Perfa - LangChain Agent Module

@file: workflows/scenarios/storage_focus.py
@desc: 存储专项评估场景 — FIO + MLC + Stream 测试
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
)


def build_storage_focus_graph(tools: dict, llm=None):
    """
    构建存储专项评估场景图
    
    流程: [环境检查] → [选择服务器] → [检查工具] → [安装缺失工具]
         → [FIO 随机读] → [FIO 顺序写] → [MLC] → [Stream]
         → [收集结果] → [存储专项报告]
    """
    graph = StateGraph(WorkflowState)
    
    required_tools = ["fio", "mlc", "stream"]
    
    graph.add_node("check_environment", make_node(check_environment, tools=tools))
    graph.add_node("select_server", make_node(select_server, tools=tools))
    graph.add_node("check_tools", make_node(check_tools, required_tools=required_tools, tools=tools))
    graph.add_node("install_tools", make_node(install_tools, tools=tools))
    
    graph.add_node("fio_randread", make_node(run_benchmark,
        test_name="fio", test_params={"rw": "randread", "bs": "4k", "size": "1G"},
        tools=tools, result_key="fio_randread"))
    graph.add_node("fio_seqwrite", make_node(run_benchmark,
        test_name="fio", test_params={"rw": "write", "bs": "1M", "size": "1G"},
        tools=tools, result_key="fio_seqwrite"))
    graph.add_node("mlc_test", make_node(run_benchmark, test_name="mlc", tools=tools))
    graph.add_node("stream_test", make_node(run_benchmark, test_name="stream", tools=tools))
    
    graph.add_node("collect_results", make_node(collect_results))
    graph.add_node("generate_report", make_node(generate_report, llm=llm, tools=tools))
    graph.add_node("handle_error", make_node(handle_error))
    
    graph.set_entry_point("check_environment")
    graph.add_edge("check_environment", "select_server")
    graph.add_edge("select_server", "check_tools")
    graph.add_conditional_edges(
        "check_tools",
        route_after_tool_check,
        {"install_tools": "install_tools", "proceed": "fio_randread"}
    )
    graph.add_edge("install_tools", "fio_randread")
    
    graph.add_edge("fio_randread", "fio_seqwrite")
    graph.add_edge("fio_seqwrite", "mlc_test")
    graph.add_edge("mlc_test", "stream_test")
    
    graph.add_edge("stream_test", "collect_results")
    graph.add_edge("collect_results", "generate_report")
    graph.add_edge("generate_report", END)
    graph.add_edge("handle_error", END)
    
    return graph.compile()
