# 图表数据清单

| Figure | Data file | Real/mock | Source | Script | Outputs |
|---|---|---|---|---|---|
| 图 3-1 系统总体架构图 | `figures/drawio/figure_3_1_system_architecture.drawio` | real-design | `codeknowledge/01-architecture-overview.md` | draw.io/manual | drawio xml |
| 图 3-2 用户请求处理流程图 | `figures/drawio/figure_3_2_request_flow.drawio` | real-design | `codeknowledge/00-map.md` | draw.io/manual | drawio xml |
| 图 3-3 报告生成与证据回溯流程图 | `figures/drawio/figure_3_3_report_trace_flow.drawio` | real-design | `src/langchain_agent/core/orchestrator.py`, `src/langchain_agent/backend/report_store.py`, `webui-v2/src/components/reports/ReportsPage.tsx` | draw.io/manual | drawio xml |
| 图 3-4 部署拓扑图 | `figures/drawio/figure_3_4_deployment_topology.drawio` | real-design | `codeknowledge/03-operations/*.md` | draw.io/manual | drawio xml |
| 图 4-1 Node Agent 内部结构图 | `figures/drawio/figure_4_1_node_agent_internal_structure.drawio` | real-design | `src/node_agent/main.py`, `src/node_agent/api/`, `src/node_agent/monitor/`, `src/node_agent/tool/`, `src/node_agent/benchmark/` | draw.io/manual | drawio xml |
| 图 4-2 Benchmark 任务生命周期图 | `figures/drawio/figure_4_2_benchmark_task_lifecycle.drawio` | real-design | `src/node_agent/benchmark/executor.py`, `src/node_agent/benchmark/task.py`, `src/node_agent/benchmark/result.py` | draw.io/manual | drawio xml |
| 图 4-3 MCP Tool 调用流程图 | `figures/drawio/figure_4_3_mcp_tool_call_flow.drawio` | real-design | `src/mcp_server/server.py`, `src/mcp_server/tools/benchmark_tools.py`, `src/mcp_server/agent_client/client.py`, `src/mcp_server/storage/database.py` | draw.io/manual | drawio xml |
| 图 4-4 LangChain Agent 工作流编排图 | `figures/drawio/figure_4_4_langchain_workflow_orchestration.drawio` | real-design | `src/langchain_agent/core/orchestrator.py`, `src/langchain_agent/workflows/router.py`, `src/langchain_agent/workflows/graph_builder.py`, `src/langchain_agent/tools/mcp_adapter.py` | draw.io/manual | drawio xml |
| 图 4-5 WebUI V2 页面与数据流图 | `figures/drawio/figure_4_5_webui_v2_page_dataflow.drawio` | real-design | `webui-v2/src/app/page.tsx`, `webui-v2/src/components/`, `webui-v2/src/lib/api.ts`, `webui-v2/src/lib/sse.ts` | draw.io/manual | drawio xml |
| 图 5-1 系统测试流程与验证链路图 | `figures/drawio/figure_5_1_system_test_validation_flow.drawio` | real-design | `chapters/05_testing_and_results.md`, `plan/experiment-protocol.md`, `codeknowledge/04-testing-and-debugging.md` | draw.io/manual | drawio xml |
| 图 5-2 监控指标采集链路图 | N/A | real-design | Node Agent metrics + VictoriaMetrics/Grafana 配置 | diagram/manual | png/svg/docx image |
| 图 4-6 报告知识增强边界图 | `figures/drawio/figure_4_6_report_knowledge_boundary.drawio` | real-design/reserved-boundary | `src/langchain_agent/core/orchestrator.py`, `src/langchain_agent/backend/report_store.py`, `codeknowledge/` | draw.io/manual | drawio xml |
