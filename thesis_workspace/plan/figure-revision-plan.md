# Perfa 毕业论文图表修订方案

## 总体判断

当前论文只有 5 张正式 draw.io 图源，数量偏少，且覆盖面不均衡。现有图主要集中在第三章总体设计和第四章报告边界，能够说明系统主链路，但不足以支撑软件工程本科毕业论文常见的“需求分析、系统设计、详细实现、测试验证”完整叙事。

从正文和项目代码看，Perfa 是工程设计与系统实现类论文，不是纯算法论文。图表应服务于三个目的：

- 让读者快速理解系统由哪些组件构成，以及组件之间如何通信。
- 让导师能看出每章不是文字堆砌，而是有需求、设计、实现、测试的工程闭环。
- 让答辩时可以围绕图讲清楚系统工作流程、核心模块和验证结果。

合理目标是正文保留 10-14 张图，配合已有表格使用。其中正式结构图、流程图建议 9-11 张；若后续补到真实运行截图或测试图，可增加到 12-14 张。

## 必须补充的图

| 建议图号 | 图名 | 所属章节 | 图表类型 | 依据材料 | 作用说明 |
|---|---|---|---|---|---|
| 图 2-1 | 系统功能需求结构图 | 第二章 | 功能分解图 | `chapters/02_related_technology_and_requirements.md` 2.6、FR-1 至 FR-7 | 把服务器管理、Agent 生命周期、工具管理、Benchmark、自然语言入口、报告、监控七类需求可视化，解决第二章只有表格、缺少需求总览图的问题。 |
| 图 3-1 | 系统总体架构图 | 第三章 | 分层架构图 | 已有 draw.io | 保留，但需要美化为四层结构，突出 WebUI V2、LangChain Agent、MCP Server、Node Agent、监控与报告存储。 |
| 图 3-2 | 自然语言测试请求处理流程图 | 第三章 | 业务流程图 | 已有 draw.io | 保留，用来说明用户一句话如何转成工作流、工具调用、Benchmark 和报告。 |
| 图 3-3 | 报告生成与证据回溯流程图 | 第三章 | 数据/证据流图 | 已有 draw.io | 保留，突出 raw results、task id、tool calls、errors 与 AI 报告之间的关系。 |
| 图 3-4 | 本地完整部署拓扑图 | 第三章 | 部署拓扑图 | 已有 draw.io、`ops/scripts/start-all.sh`、`codeknowledge/03-operations/*.md` | 保留，用来支撑部署设计和答辩演示环境。 |
| 图 4-1 | Node Agent 内部结构图 | 第四章 | 模块结构图 | `src/node_agent/main.py`、`api/`、`monitor/`、`tool/`、`benchmark/` | 必须补。第四章 4.1 是实现重点，只用表格不够。图中应展示 ToolManager、BenchmarkExecutor、Monitor、Flask API、ResultCollector、Runner 的关系。 |
| 图 4-2 | Benchmark 任务生命周期图 | 第四章 | 状态/流程图 | `src/node_agent/benchmark/executor.py`、`task.py`、`result.py` | 必须补。性能测试平台核心是长任务管理，应展示 pending/running/completed/failed/cancelled、日志、结果保存和并发锁。 |
| 图 4-3 | MCP Tool 调用流程图 | 第四章 | 调用序列图 | `src/mcp_server/server.py`、`tools/*.py`、`agent_client/client.py` | 必须补。说明 Agent 调用 MCP Tool 后如何查服务器、检查 Agent、转发 Node Agent API、返回 Tool result。 |
| 图 4-4 | LangChain Agent 工作流编排图 | 第四章 | 工作流结构图 | `src/langchain_agent/core/orchestrator.py`、`workflows/router.py`、`graph_builder.py` | 必须补。说明场景路由、WorkflowEngine、MCPToolAdapter、ReportStore 和流式事件。 |
| 图 4-5 | WebUI V2 页面与数据流图 | 第四章 | 前端页面结构图 | `webui-v2/src/app/page.tsx`、`components/*`、`src/lib/api.ts` | 必须补。说明 chat、servers、reports、monitor 四个页面与后端 API 代理、SSE 解析、报告展示的关系。 |
| 图 5-1 | 系统测试流程与验证链路图 | 第五章 | 测试流程图 | `chapters/05_testing_and_results.md`、`plan/experiment-protocol.md` | 必须补。第五章目前表很多但缺图，应展示状态检查、模块测试、接口测试、前端测试、问题记录的验证路径。 |

## 建议补充的图

| 建议图号 | 图名 | 所属章节 | 图表类型 | 依据材料 | 作用说明 |
|---|---|---|---|---|---|
| 图 2-2 | 非功能需求与设计映射图 | 第二章 | 需求-设计映射图 | 第二章 2.7、第三章设计原则 | 可选但推荐。把可扩展性、可维护性、可靠性、安全边界、可观测性、易用性映射到 Runner、MCP Tool、任务日志、API Key、metrics、WebUI。 |
| 图 4-6 | 报告生成与知识增强设计边界图 | 第四章 | 双区域结构图 | 已有 draw.io | 保留但建议改编号。当前叫图 4-1 会和 Node Agent 内部结构图冲突，建议挪到图 4-6。 |
| 图 5-2 | 监控指标采集链路图 | 第五章 | 监控链路图 | Node Agent metrics、VictoriaMetrics、Grafana 配置 | 推荐。与图 3-4 不同，本图聚焦测试过程中 CPU、内存、磁盘、网络指标如何采集、存储和展示。 |
| 图 5-3 | 测试结果通过情况统计图 | 第五章 | 简单柱状图/堆叠条形图 | 第五章表 5-3、5-4、5-5 | 推荐，但前提是只用真实测试结果。可展示“通过、失败、未完成”数量，增强测试章节直观性。 |

## 不建议补充的图

| 图名 | 不建议原因 |
|---|---|
| 每个压测工具单独一张执行图 | UnixBench、fio、stream、iperf3 等工具很多，逐个画会稀释重点；论文应突出平台抽象和执行机制。 |
| 大语言模型内部推理过程图 | 项目没有实现模型内部结构，画这种图容易变成泛泛技术介绍，且与软件工程实现关系弱。 |
| 完整 RAG 知识库架构图 | 当前代码只预留 ChromaDB/知识增强配置，不能写成已完整上线；只能画“扩展预留边界”。 |
| 纯 UI 截图堆叠图 | 截图可以放 1-2 张用于答辩或附录，但正文不宜用大量截图代替设计图。 |

## 推荐最终图表提纲

### 第二章 相关技术与需求分析

1. 图 2-1 系统功能需求结构图  
   展示七类功能需求：服务器管理、Agent 生命周期管理、测试工具管理、Benchmark 任务执行、自然语言测试入口、报告生成与归档、监控展示。图中可将用户角色放在左侧，将 Perfa 平台能力放在中间，将对应模块放在右侧。

2. 图 2-2 非功能需求与设计映射图（可选）  
   展示非功能需求如何落到代码设计：可扩展性对应 Runner 和 ToolManager；可维护性对应四层架构；可靠性对应任务状态、日志和超时处理；安全边界对应 MCP Tool 与 API Key；可观测性对应 metrics、logs、trace id；易用性对应 WebUI 和自然语言入口。

### 第三章 系统总体设计

3. 图 3-1 系统总体架构图  
   四层架构：交互层 WebUI V2、智能编排层 LangChain Agent、能力封装层 MCP Server、节点执行层 Node Agent，并加入 VictoriaMetrics、Grafana、ReportStore。

4. 图 3-2 自然语言测试请求处理流程图  
   从用户输入开始，经 WebUI SSE 请求、场景路由、工作流、MCP Tool、Node Agent Benchmark、结果返回、报告持久化、前端展示结束。

5. 图 3-3 报告生成与证据回溯流程图  
   展示 Benchmark 结果、错误记录、工具调用记录进入报告节点，最终保存到 ReportStore 并由 ReportsPage 同时展示 AI 结论和原始证据。

6. 图 3-4 本地完整部署拓扑图  
   展示 Browser、WebUI V2:3002、LangChain:10000、MCP:9000、Node Agent API:8080、metrics:8000、VictoriaMetrics:8428、Grafana:3000、OTel/Jaeger。

### 第四章 系统详细设计与实现

7. 图 4-1 Node Agent 内部结构图  
   展示 NodeAgent 启动后聚合的 Monitor、ToolManager、BenchmarkExecutor、APIServer、ResultCollector、Runner。重点突出 Node Agent 是真实执行端。

8. 图 4-2 Benchmark 任务生命周期图  
   展示任务从接收请求、检查工具、创建任务、运行 Runner、写日志、解析结果、保存 SQLite、返回状态的过程。可加入“同一节点单任务锁”。

9. 图 4-3 MCP Tool 调用流程图  
   展示 LangChain Agent 调用 run_benchmark Tool 时，MCP Server 如何校验 API Key、解析参数、查询 server_id、使用 AgentClient 调 Node Agent、返回结构化 Tool result。

10. 图 4-4 LangChain Agent 工作流编排图  
    展示 OpenAI 兼容接口、AgentOrchestrator、ScenarioRouter、WorkflowEngine、MCPToolAdapter、ReportStore、流式 metadata 事件。

11. 图 4-5 WebUI V2 页面与数据流图  
    展示主页面四个入口：ChatPage、ServersPage、ReportsPage、MonitorPage。ChatPage 通过 SSE 消费流式响应，ReportsPage 展示报告详情和原始证据。

12. 图 4-6 报告生成与知识增强设计边界图  
    已实现区域：Benchmark 结果、错误、工具调用、generate_report、ReportStore、ReportsPage。扩展预留区域：历史报告、codeknowledge、Embedding、Vector Store、RAG 增强。

### 第五章 系统测试与结果分析

13. 图 5-1 系统测试流程与验证链路图  
    展示测试从启动状态检查开始，依次覆盖 Node Agent、MCP 数据库、LangChain 工作流、WebUI 页面、运行状态和问题记录。适合放在 5.2 测试方案设计后。

14. 图 5-2 监控指标采集链路图  
    展示 Node Agent Monitor 采集 CPU、Memory、Disk、Network，经 Prometheus metrics 暴露到 VictoriaMetrics，再由 Grafana/WebUI 展示。

15. 图 5-3 测试结果通过情况统计图（可选）  
    根据第五章真实结果统计通过、失败、未完成项目数量。该图必须用真实测试结果，不允许使用 mock 数据。

## 绘图风格建议

- 统一使用白底、细线、低饱和配色，避免大面积渐变和装饰性背景。
- 所有图优先用 draw.io 制作，保留 `.drawio` 源文件，导出 PNG 后插入 Word。
- 架构图使用分层色块，流程图使用圆角矩形和菱形判断节点，部署图使用组件框和端口标注。
- 同一章图的颜色含义保持一致：WebUI 蓝色，LangChain 橙色，MCP 绿色，Node Agent 灰蓝色，监控紫灰色，报告/存储浅灰色。
- 图中文字不要超过正文一行宽度，避免把大段说明塞进图里。具体解释放在图下正文。

## 优先级

第一优先级：补图 4-1、4-2、4-3、4-4、4-5、5-1。这些图直接弥补第四章和第五章视觉支撑不足的问题。

第二优先级：补图 2-1、5-2，并调整已有图 4-1 为图 4-6。

第三优先级：根据真实测试结果补图 5-3，或在答辩材料中加入 1-2 张关键 WebUI 截图。

