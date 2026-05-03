# 方法-实验可追溯映射

| Contribution | Method module | Experiment | Table/Figure | Allowed claim | Evidence status |
|---|---|---|---|---|---|
| 自然语言驱动服务器性能测试 | LangChain Agent + MCP Tool + Node Agent | Prompt-first E2E 或接口链路测试 | 表 5-4 | 系统具备自然语言请求到测试流程的编排能力 | 已部分实测 |
| 节点执行端压测能力 | Node Agent ToolManager + BenchmarkExecutor | Node Agent 测试脚本、Benchmark 快速测试 | 表 5-2, 表 5-3 | Node Agent 能执行工具管理和压测任务 | 已部分实测 |
| 监控与可观测性 | Monitor + Prometheus metrics | `/metrics`、状态接口、监控测试脚本 | 表 5-2 | 系统具备基础指标采集能力 | 已部分实测 |
| MCP 能力封装 | MCP Server Tool + AgentClient | MCP 单元测试、工具注册检查 | 表 5-3 | MCP Server 能封装并转发平台能力 | 已部分实测 |
| 报告归档和证据回溯 | ReportStore + ReportsPage | 报告接口/前端契约测试 | 表 5-4 | 报告包含结论与原始证据字段 | 已部分实测 |
