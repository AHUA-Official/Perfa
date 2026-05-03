# 表格 Schema

| Table | Purpose | Rows | Metrics | Data source | Replacement owner |
|---|---|---|---|---|---|
| 表 2-1 功能需求表 | 总结系统功能需求 | 服务器管理、Agent 管理、工具管理、压测、报告、监控、对话 | 功能描述、输入、输出、优先级 | Perfa 实现与需求分析 | controller |
| 表 2-2 非功能需求表 | 说明可用性、扩展性、安全性等约束 | 性能、可靠性、可扩展性、可维护性、安全 | 需求说明、设计响应 | 项目设计 | controller |
| 表 3-1 系统模块职责表 | 对应四层架构职责 | WebUI V2、LangChain Agent、MCP Server、Node Agent | 输入、输出、主要文件 | `codeknowledge/02-modules` | controller |
| 表 3-3 Agent Harness 生命周期与证据表 | 说明性能测试工作流硬约束 | 选择服务器、检查 Agent、检查工具、执行 Benchmark、获取结果、生成报告、保存证据 | 生命周期阶段、主要检查、关键证据 | `src/langchain_agent/workflows/nodes.py`, `AGENTS.md` | controller |
| 表 4-1 MCP Tool 分类表 | 展示工具能力封装 | 服务器管理、Agent 生命周期、工具管理、Benchmark、报告、知识库 | Tool 名称、职责 | `src/mcp_server/tools/` | controller |
| 表 4-4 工作流生命周期证据表 | 对应 workflow 节点和报告字段 | 服务器选择、工具检查、压测执行、结果收集、知识增强报告、归档 | 实现函数、输出字段 | `src/langchain_agent/workflows/nodes.py`, `src/langchain_agent/core/orchestrator.py` | controller |
| 表 5-1 测试环境表 | 记录测试环境 | 本机、远端节点、依赖服务 | OS、端口、服务版本 | 实际测试环境 | user/controller |
| 表 5-2 功能测试用例表 | 验证功能覆盖 | 健康检查、注册、安装、压测、查询、报告 | 输入、预期、实际、状态 | 实测记录 | controller |
| 表 5-3 接口测试结果表 | 汇总接口测试结果 | Node Agent、MCP Server、LangChain Agent、WebUI 代理 | 状态码、响应摘要 | curl/test scripts | controller |
| 表 5-4 压测结果汇总表 | 汇总典型压测任务结果 | fio、stream、unixbench、mlc 等 | 耗时、状态、关键指标 | 真实 benchmark 输出 | user/controller |
