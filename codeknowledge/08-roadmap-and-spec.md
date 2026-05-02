# 升级规格与路线图

这个文件吸收原 `doc/UPGRADE_SPEC.md` 中仍有价值的目标、规格、风险和实施路线信息。

## 三大升级方向

| 方向 | 核心目标 |
|------|----------|
| LangGraph 工作流编排 | 从自由 ReAct 循环升级为结构化测试场景 |
| 自研 Web 前端 | 从通用聊天前端升级为 Perfa 专属界面 |
| OTel + AI 故障分析 | 从黑盒执行升级为可观测、可诊断系统 |

## 工作流规格目标

目标场景包括：

- `quick_test`
- `full_assessment`
- `cpu_focus`
- `storage_focus`
- `network_focus`
- `free_chat`

目标节点抽象包括：

- `check_environment`
- `select_server`
- `check_tools`
- `install_tools`
- `run_benchmark`
- `wait_result`
- `collect_results`
- `generate_report`
- `handle_error`

原规格里最重要的现实约束是：

- 编排层可以有“并行”语义
- 但 Node Agent 当前实际执行模型仍然偏串行
- 所以设计上必须允许串行 fallback

## Web 前端规格目标

目标页面：

- 对话页
- 服务器管理页
- 报告页
- 监控 / 可观测性页

目标能力：

- SSE 流式回答
- 工作流进度条
- 结构化结果卡片
- 服务器与 Agent 状态展示
- 报告图表

原规格里定义过的目标 API 包括：

- `GET /v1/servers`
- `GET /v1/servers/{id}`
- `POST /v1/servers`
- `GET /v1/workflows/status/{sid}`
- `GET /v1/reports`
- `GET /v1/reports/{id}`
- `GET /v1/monitoring/metrics`

这些应视为设计目标，不是对当前代码状态的逐项断言。

## 可观测性规格目标

原规格定义过的核心 trace 名称包括：

- `agent.query`
- `agent.think`
- `agent.act`
- `workflow.node`
- `mcp.tool.execute`
- `mcp.sse.connect`
- `benchmark.execute`
- `benchmark.prepare`
- `benchmark.run`

原规格定义过的核心 metrics 包括：

- `perfa_agent_queries_total`
- `perfa_agent_query_duration_seconds`
- `perfa_tool_calls_total`
- `perfa_tool_call_duration_seconds`
- `perfa_llm_tokens_total`
- `perfa_benchmark_tasks_total`
- `perfa_benchmark_duration_seconds`
- `perfa_workflow_nodes_total`

这些名称反映的是系统观测设计目标集。

## 部署目标

升级规格中的目标部署组件包括：

- `Perfa Web`
- `LangChain Agent API`
- `MCP Server`
- `Node Agent`
- `OTel Collector`
- `Jaeger`
- `VictoriaMetrics`
- `Grafana`

说明平台目标是“测试执行 + 观测 + 展示”的闭环。

## 实施计划摘要

### Phase 1

- 工作流基础设施
- 场景图
- orchestrator 集成

### Phase 2

- Web 前端
- SSE 与 Markdown
- 服务器和报告页面

### Phase 3

- OTel SDK 注入
- Collector / Jaeger / VM 集成
- AI 故障分析
- 前端观测面板

## 风险与应对

| 风险 | 应对 |
|------|------|
| 工作流并行语义与串行执行模型冲突 | 保留串行 fallback |
| OTel 改造侵入逻辑 | 自动注入优先，关键路径再手动埋点 |
| 自研前端开发量超预期 | 优先对话与主流程页面 |
| 观测栈有资源开销 | 轻量部署，按需开启 |

## 论文/汇报映射

- ReAct 到结构化工作流的演进
- 前端交互与工作流可视化
- 分布式追踪与指标体系
- AI 故障分析与诊断

## 当前判断

`UPGRADE_SPEC` 适合作为历史规格稿，但其高价值内容已经被吸收进：

- [01-architecture-overview.md](./01-architecture-overview.md)
- [06-deep-dives/](./06-deep-dives/README.md)
- [07-history-and-operations-context.md](./07-history-and-operations-context.md)
- 本文件
