# 第三章 系统总体设计

## 3.1 设计目标与原则

Perfa 的总体目标是构建一套自然语言驱动的服务器性能测试平台，使用户能够通过 Web 页面和对话方式完成服务器管理、测试工具准备、Benchmark 执行、监控观察和报告查看。与传统脚本式测试方案相比，Perfa 不只关注单个测试命令的执行，还强调测试流程的组织、工具能力的封装、执行证据的保存和结果解释的可追溯性。因此，本章从系统总体架构出发，对 Perfa 的分层结构、核心流程、模块职责、接口设计、数据存储和部署拓扑进行说明，为第四章的详细设计与实现提供基础。

系统设计遵循可执行性原则。自然语言交互不能停留在生成建议文本的层面，用户提出测试请求后，系统需要能够真正定位目标服务器、检查节点 Agent、调用测试工具、获取任务状态并返回结果。为保证这一点，Perfa 将大语言模型编排层与真实执行层分离，模型负责意图理解、场景路由和结果总结，Node Agent 负责在被测节点上执行监控采集和压测任务。中间通过 MCP Server 暴露受控工具接口，避免模型直接接触系统命令。

系统设计遵循分层解耦原则。WebUI V2 负责交互展示，LangChain Agent 负责对话和工作流编排，MCP Server 负责能力封装和工具协议，Node Agent 负责节点侧真实操作。四层之间通过 HTTP、SSE 和 MCP 协议连接。每层只承担自身职责：前端不直接操作被测节点，Agent 层不直接执行 shell 命令，MCP 层不直接保存前端会话状态，Node Agent 不理解自然语言意图。这样的边界能够降低模块间耦合，使系统更容易维护和扩展。

系统设计遵循可观测与可回溯原则。性能测试任务通常持续时间较长，且结果会受到环境和负载影响。Perfa 在设计中保存任务 ID、工具调用、原始结果、错误记录、日志和报告结论，并通过 Prometheus 指标、VictoriaMetrics、Grafana 和 Trace ID 等机制为测试过程提供观测基础。报告模块不仅展示 AI 总结，也展示 raw results、task ids、tool calls 等原始证据，使用户可以从结论回溯到具体执行过程。

系统设计遵循 Harness 生命周期约束原则。通用 coding-agent harness 通常围绕 issue、代码工作区和合并请求组织任务，而 Perfa 的任务对象是服务器性能测试。系统不能让模型自由选择任意步骤，也不能在没有原始结果时给出“测试完成”的回答。因此，Perfa 将一次自然语言测试请求约束为“选择服务器、检查 Agent、检查工具、执行 Benchmark、获取结果、生成报告、保存证据”的固定生命周期。该设计吸收了长任务 Agent 工程中关于状态、验证和证据记录的思想，但服务于性能测试的可复现性和结果可信度。

系统设计遵循可扩展原则。服务器性能测试工具种类较多，不同场景需要不同测试组合。Perfa 在 Node Agent 中使用 ToolManager 和 Runner 机制管理工具，在 MCP Server 中使用 Tool 注册机制暴露能力，在 LangChain Agent 中使用场景路由和工作流图组织流程。新增工具、测试场景或报告分析逻辑时，可以在对应层进行扩展，而不必重写整条链路。

## 3.2 系统总体架构

Perfa 采用四层架构，自上而下分别为交互层、智能编排层、能力封装层和节点执行层。交互层由 WebUI V2 实现，负责用户输入、过程展示和结果呈现。智能编排层由 LangChain Agent 实现，负责理解用户请求、选择工作流、调用工具并生成最终回答。能力封装层由 MCP Server 实现，负责将服务器管理、Agent 生命周期、测试工具管理、Benchmark 调度和报告生成封装为 MCP Tool。节点执行层由 Node Agent 实现，运行在被测节点上，负责系统信息采集、工具安装与校验、压测执行、日志保存和 Prometheus 指标暴露。

图 3-1 展示了系统总体架构。浏览器访问 WebUI V2，前端通过 Next.js API 代理调用 LangChain Agent 的 OpenAI 兼容接口。LangChain Agent 通过 MCPToolAdapter 连接 MCP Server，加载并调用 MCP Tool。MCP Server 根据工具类型访问本地 SQLite 数据库或通过 AgentClient 调用 Node Agent。Node Agent 接收 HTTP 请求后执行工具管理、Benchmark 调度和系统监控，并将结果返回上层。监控数据由 Node Agent 的 metrics 端口暴露，再由 VictoriaMetrics 采集并由 Grafana 展示。

图 3-1 系统总体架构图

```text
浏览器
  -> WebUI V2
  -> LangChain Agent
  -> MCP Server
  -> Node Agent
  -> Benchmark Tool / Monitor

Node Agent Metrics
  -> VictoriaMetrics
  -> Grafana
```

四层架构的关键在于职责分离。WebUI V2 只处理用户交互和前端状态，不直接保存服务器 SSH 信息，也不直接访问 Node Agent。LangChain Agent 只处理对话、路由和工作流，不直接管理服务器数据库。MCP Server 作为工具能力中心，既向上提供标准 MCP Tool，又向下调用节点 API。Node Agent 则是唯一直接接触被测节点系统环境和压测工具的组件。这样的设计降低了大语言模型错误输出造成真实系统误操作的风险，也使各层可以独立测试。

表 3-1 给出了系统主要模块的职责划分。

| 模块 | 所在层次 | 主要输入 | 主要输出 | 核心职责 |
|---|---|---|---|---|
| WebUI V2 | 交互层 | 用户对话、页面操作 | SSE 消息、服务器列表、报告详情、监控视图 | 提供对话、服务器、报告和监控页面 |
| LangChain Agent | 智能编排层 | 用户请求、MCP 工具结果、工作流状态 | 最终回答、过程事件、工作流报告 | 意图识别、场景路由、工具调用和报告总结 |
| MCP Server | 能力封装层 | MCP 工具调用参数、服务器记录 | Tool 结果、任务 ID、报告数据 | 封装服务器管理、Agent 管理、工具管理、压测和报告能力 |
| Node Agent | 节点执行层 | HTTP API 请求、压测参数 | 系统状态、工具状态、Benchmark 结果、日志、metrics | 执行真实节点操作和资源监控 |
| VictoriaMetrics | 监控存储 | Prometheus 指标 | 时间序列查询结果 | 保存节点运行指标 |
| Grafana | 监控展示 | 时序数据源 | 可视化面板 | 展示资源监控数据 |

## 3.3 核心业务流程设计

Perfa 的核心业务流程以自然语言测试请求为起点。用户在对话页面输入测试需求，例如要求测试某台服务器的 CPU、磁盘或综合性能。前端通过流式接口将请求发送给 LangChain Agent。Agent 根据用户请求和当前上下文判断任务类型，如果属于性能测试场景，则进入工作流模式；如果属于普通问答或无法确定场景，则进入自由对话模式。工作流模式下，系统根据场景选择节点序列，依次完成服务器解析、Agent 状态检查、工具准备、测试执行、结果收集、报告生成和证据保存。

图 3-2 展示了自然语言测试请求的处理流程。

图 3-2 自然语言测试请求处理流程图

```text
用户输入测试需求
  -> WebUI V2 发送流式请求
  -> LangChain Agent 场景路由
  -> WorkflowEngine 选择场景图
  -> 选择服务器并检查 Agent
  -> 检查或安装测试工具
  -> MCPToolAdapter 调用 MCP Tool
  -> MCP Server 转发到 Node Agent
  -> Node Agent 执行 Benchmark
  -> 返回任务结果和日志
  -> LangChain Agent 生成报告
  -> ReportStore 保存证据
  -> WebUI V2 展示回答、进度和报告入口
```

Benchmark 执行流程采用异步任务思想。对于可能耗时较长的测试，MCP Server 调用 Node Agent 的运行接口后，Node Agent 返回 task id 和初始状态。上层系统随后通过任务状态查询接口获取进度，并在任务完成后获取结果。该模式避免对话接口长时间阻塞，也符合前端展示工作流进度的需求。Node Agent 内部使用 BenchmarkExecutor 管理当前任务，任务执行前检查工具状态，执行过程中保存日志，执行完成后保存结果。由于同一节点并发运行多个压测任务会影响结果，执行器通过锁限制同一时间只运行一个任务。这一点与 coding-agent harness 中追求多任务吞吐的设计不同，Perfa 更重视测试隔离和结果可解释性。

报告生成流程位于测试闭环末端。Perfa 支持两类报告来源：MCP Server 中的结构化报告工具和 LangChain Agent 工作流中的 LLM 辅助总结。工作流节点会优先尝试调用 `generate_report` Tool，若工具不可用或缺少有效服务器上下文，则根据已有测试结果降级生成 Markdown 报告。为增强报告解释性，系统还加入了基于 FurinaBench Markdown 文档的轻量级 Benchmark 知识库检索：报告节点会根据当前测试项检索 CPU、内存、存储或网络相关知识片段，并把片段和文件路径写入报告上下文。工作流结束后，AgentOrchestrator 将报告保存到 ReportStore，报告字段包含场景、服务器、状态、摘要、AI 结论、原始结果、错误信息、知识库片段、任务 ID、工具调用和 Trace ID。前端报告页读取报告列表和详情后，将总结、知识依据与原始证据分别展示。

图 3-3 展示了报告生成与证据回溯流程。

图 3-3 报告生成与证据回溯流程图

```text
Benchmark 结果 / 错误 / 工具调用
  -> Workflow generate_report 节点
  -> 检索 FurinaBench Benchmark 知识片段
  -> MCP generate_report Tool 或 LLM 生成
  -> AgentOrchestrator 持久化 report
  -> ReportStore JSON 文件
  -> WebUI ReportsPage
  -> AI 结论 + 知识依据 + 原始结果 + 任务 ID + 错误记录 + 工具调用
```

## 3.4 模块职责划分

WebUI V2 是系统的人机交互入口。其主页面包含 chat、servers、reports 和 monitor 四个页面。chat 页面负责用户自然语言输入、消息展示、SSE 流式解析和工作流进度展示；servers 页面负责展示服务器信息和触发 Agent 操作；reports 页面负责展示报告列表和报告详情；monitor 页面负责展示监控信息。WebUI V2 的设计目标是将对话式操作和结构化管理页面结合起来，使用户既可以用自然语言发起测试，也可以通过页面查看服务器、报告和监控状态。

LangChain Agent 是系统的智能编排中心。它对外提供 OpenAI 兼容接口 `/v1/chat/completions`，内部通过 AgentOrchestrator 管理会话、工具和工作流。场景路由模块根据关键词和 LLM 判断用户请求属于 quick_test、full_assessment、cpu_focus、storage_focus、network_focus 或 free_chat。工作流引擎根据场景执行对应节点，并通过流式事件向前端输出 thinking、tool_result、workflow_progress、summary 等过程信息。该层既连接用户自然语言，也连接 MCP 工具能力，是 Perfa 实现自然语言驱动测试的关键。

MCP Server 是能力封装和协议适配中心。它将服务器管理、Agent 生命周期、工具管理、Benchmark 和报告生成注册为 MCP Tool，并通过 API Key 对 SSE 接入进行基本鉴权。MCP Server 内部使用 SQLite 保存服务器、Agent 和任务记录，向下通过 AgentClient 访问 Node Agent。它既不直接运行测试工具，也不直接生成前端页面，而是负责把平台后端能力整理为上层 Agent 可调用的标准工具集合。

Node Agent 是节点侧执行中心。它启动时初始化 ToolManager、BenchmarkExecutor、Prometheus metrics 服务、Monitor 后台线程和 Flask API。ToolManager 负责压测工具生命周期管理，BenchmarkExecutor 负责任务执行与结果收集，Monitor 负责周期采集 CPU、内存、磁盘和网络指标，Flask API 负责向上暴露健康检查、系统状态、工具管理、Benchmark、日志和配置接口。Node Agent 的设计使被测节点具备独立执行能力，上层系统只需要通过 HTTP API 调用它。

监控和可观测性组件支撑测试过程解释。Node Agent 暴露 Prometheus 兼容指标，VictoriaMetrics 负责存储指标，Grafana 负责展示面板。OTel 和 Jaeger 作为可选链路追踪组件由启动脚本拉起，用于观察跨组件调用情况。由于本地完整链路脚本会启动 OTel / Jaeger，并检查 Jaeger 接口是否就绪，论文可以将其写作系统可观测性设计的一部分，但在具体结果分析中仍应以实际运行配置为准。

## 3.5 接口与数据流设计

Perfa 的接口设计围绕四条主要链路展开：对话链路、MCP 工具链路、节点执行链路和监控链路。对话链路从 WebUI V2 到 LangChain Agent，主要使用 HTTP 和 SSE。用户发起流式聊天请求后，LangChain Agent 以 OpenAI 兼容格式返回消息，其中 `choices[].delta.content` 承载最终回答内容，metadata 承载工作流进度、工具结果和总结信息。前端 SSE 解析器将正文和过程事件拆分展示，使长任务执行过程对用户可见。

MCP 工具链路从 LangChain Agent 到 MCP Server。MCPToolAdapter 通过 SSE 地址连接 MCP Server，初始化会话并加载工具列表。每个 MCP Tool 包含名称、描述和输入 schema，适配器将其包装为 LangChain 兼容工具。工具调用时，适配器建立临时连接，发送工具名称和参数，接收结构化结果或文本结果后返回给 Agent 编排层。该链路的设计使上层 Agent 不必关心具体业务接口路径，只需要面向工具语义进行调用。

节点执行链路从 MCP Server 到 Node Agent。以执行压测为例，MCP Server 的 `run_benchmark` Tool 先根据 server_id 查询服务器记录，构造 AgentClient，并向 Node Agent 的 `/api/benchmark/run` 接口提交请求。Node Agent 返回任务状态或执行结果后，MCP Server 再将其整理为 Tool 结果返回给 LangChain Agent。查询系统状态、安装工具、获取日志和生成报告也遵循类似模式。该链路的核心是 server_id、agent_id、task_id 等标识字段，它们将服务器记录、Agent 状态和测试任务关联起来。

监控链路与业务调用链路相对独立。Node Agent 在 8000 端口暴露 metrics，VictoriaMetrics 从该端口采集时间序列数据，Grafana 从 VictoriaMetrics 查询并展示。业务接口通过 8080 端口访问 Node Agent，监控指标通过 8000 端口暴露，两者分离可以避免监控抓取影响业务接口结构。LangChain Agent 和报告模块可以在需要时引用监控数据，但当前系统中更稳定的设计是先保证 Benchmark 结果、日志和基础指标可用，再逐步增强报告中的时序分析能力。

表 3-2 给出了主要接口链路。

| 链路 | 起点 | 终点 | 协议/接口 | 主要数据 |
|---|---|---|---|---|
| 对话请求 | WebUI V2 | LangChain Agent | `/v1/chat/completions`，HTTP/SSE | 用户消息、流式回答、metadata |
| 工具调用 | LangChain Agent | MCP Server | MCP over SSE | Tool name、arguments、Tool result |
| 节点执行 | MCP Server | Node Agent | HTTP API | server_id、task_id、benchmark params、result |
| 指标采集 | Node Agent | VictoriaMetrics | Prometheus metrics | CPU、内存、磁盘、网络指标 |
| 监控展示 | Grafana/WebUI | VictoriaMetrics/后端 API | HTTP 查询 | 时间序列、面板数据 |
| 报告展示 | WebUI V2 | LangChain Agent | `/v1/reports` | report list、report detail |

表 3-3 给出了 Perfa 的 Agent Harness 生命周期与证据要求。

| 生命周期阶段 | 主要检查 | 关键证据 |
|---|---|---|
| 选择服务器 | server_id 是否存在，服务器是否匹配用户选择 | server_id、server_ip、server_alias |
| 检查 Agent | Node Agent 是否部署并在线 | agent_id、agent_status、健康检查结果 |
| 检查工具 | 所需 Benchmark 工具是否安装 | available_tools、missing_tools、安装结果 |
| 执行 Benchmark | 是否返回 task_id，任务是否进入运行状态 | task_id、test_name、params |
| 获取结果 | 任务是否完成，结果是否可查询 | raw_results、duration、metrics、log_path |
| 生成报告 | 是否结合原始结果和知识库片段 | ai_report、knowledge_matches |
| 保存证据 | 是否持久化可复查字段 | raw_errors、tool_calls、trace_id、report_id |

## 3.6 数据存储设计

Perfa 的数据存储不是集中在单一数据库中，而是按数据类型分散在多个位置。MCP Server 使用 SQLite 保存服务器、Agent 和任务记录。数据库初始化时创建 servers、agents 和 tasks 三张表。servers 表保存 server_id、IP、SSH 端口、别名、Agent ID、Agent 端口、权限模式、标签、创建时间和更新时间等信息。agents 表保存 agent_id、server_id、状态、版本和最近在线时间。tasks 表保存 task_id、server_id、agent_id、test_name、params、status、started_at、completed_at 和 created_at 等字段。这些表为服务器管理、Agent 生命周期和 Benchmark 任务跟踪提供基础。

表 3-4 展示了 MCP Server 数据表设计。

| 数据表 | 主键 | 关键字段 | 作用 |
|---|---|---|---|
| servers | server_id | ip、port、alias、agent_id、agent_port、ssh_user、privilege_mode、tags | 保存被测服务器和 Agent 接入信息 |
| agents | agent_id | server_id、status、version、last_seen | 保存节点 Agent 状态 |
| tasks | task_id | server_id、agent_id、test_name、params、status、started_at、completed_at | 保存压测任务基础记录 |

LangChain Agent 使用轻量级 JSON 文件保存工作流报告。ReportStore 默认路径为 `data/langchain/reports.json`，以 JSON 数组形式保存报告对象。报告对象不仅包含标题、场景、服务器和状态，还包含 summary、ai_report、raw_results、raw_errors、knowledge_matches、task_ids、tool_calls、trace_id、query、session_id 和 conversation_id 等字段。其中 knowledge_matches 保存 Benchmark 知识库检索到的标题、路径、分类、评分和片段内容。这种设计便于前端快速展示报告，也便于后续迁移到数据库或向量存储。由于报告属于工作流结果归档，其结构比单纯 Benchmark 结果更接近用户可读的业务记录。

Node Agent 保存的数据主要包括 Benchmark 结果、任务日志、工作目录和监控指标。BenchmarkExecutor 在执行任务时创建日志文件，并通过 ResultCollector 收集测试结果。日志文件记录实际执行命令和工具输出，适合用于测试失败排查和结果复核。监控指标不直接保存在 Node Agent 本地业务数据库中，而是通过 metrics 端口暴露给外部时序数据库。这样的设计使节点执行端保持轻量，同时将长期时序数据交给专门组件处理。

监控数据由 VictoriaMetrics 负责存储，Grafana 负责展示。相比将所有指标写入业务数据库，时序数据库更适合处理周期性指标、范围查询和聚合计算。报告模块当前主要保存测试结果、工作流证据和 FurinaBench 知识库检索片段，未来若需要生成更深入的性能分析报告，可以根据 task_id、时间范围和 agent_id 查询对应时间段的监控指标，并把指标摘要写入报告。需要说明的是，当前知识增强采用本地 Markdown 关键词检索，不等同于已经实现完整的向量数据库 RAG 分析链路。

## 3.7 部署拓扑设计

Perfa 当前最稳定的部署模式是本地完整开发链路。统一启动入口为 `ops/scripts/start-all.sh`，脚本按顺序启动 Point、OTel / Jaeger、MCP Server、LangChain 后端和 WebUI V2，并通过 HTTP 或 HEAD 请求检查关键端口是否就绪。Point 包含监控栈和 Node Agent，MCP Server 默认监听 9000 端口，LangChain 后端默认监听 10000 端口，WebUI V2 默认监听 3002 端口。该模式适合本地开发、演示和毕业设计答辩，因为所有组件均在同一控制机上运行，部署和排障成本较低。

图 3-4 展示了本地完整开发链路。

图 3-4 本地完整部署拓扑图

```text
Browser
  -> WebUI V2 :3002
  -> LangChain Agent :10000
  -> MCP Server :9000
  -> Node Agent API :8080

Node Agent Metrics :8000
  -> VictoriaMetrics :8428
  -> Grafana :3000

OTel Collector :4317/:4318
  -> Jaeger UI :16686
```

系统也支持本地基础设施模式。该模式通过 `start-point.sh` 启动 VictoriaMetrics、Grafana 和 Node Agent，只保留监控栈与节点执行端，不启动 MCP Server、LangChain Agent 和 WebUI V2。该模式适合单独调试 Node Agent、测试监控采集或验证压测工具执行。由于它不包含自然语言编排和前端页面，不能代表完整 Perfa 平台，但对底层执行端开发有价值。

从代码结构看，Perfa 具备混合部署能力。LangChain Agent 通过 MCP SSE 地址连接 MCP Server，MCP Server 通过 AgentClient 访问 Node Agent，因此各组件不必全部位于同一机器。控制机可以运行 WebUI、LangChain Agent 和 MCP Server，远端服务器运行 Node Agent。MCP Server 的服务器管理和 Agent 部署工具可以保存远端节点 IP、SSH 信息、Agent 端口和权限模式，并通过 HTTP 调用远端 Agent。该模式更接近真实服务器性能测试场景，但仓库中最完整的一键启动脚本仍以本地完整链路为主，因此论文中应将混合部署表述为“代码和架构支持”，而不是夸大为已完全产品化的多节点集群管理平台。

表 3-5 对比了三种部署模式。

| 部署模式 | 启动入口 | 启动组件 | 适用场景 | 成熟度 |
|---|---|---|---|---|
| 本地完整链路 | `ops/scripts/start-all.sh` | Node Agent、监控栈、OTel/Jaeger、MCP Server、LangChain Agent、WebUI V2 | 本地开发、联调、答辩演示 | 最高 |
| 本地基础设施模式 | `ops/scripts/start-point.sh` | Node Agent、VictoriaMetrics、Grafana | 调试执行端和监控栈 | 较高 |
| 混合/远端节点模式 | 部分工具和配置支持 | 控制机组件 + 远端 Node Agent | 多服务器测试、远端节点执行 | 架构支持，仍需完善统一脚本 |

部署设计还需要考虑端口和健康检查。`status-all.sh` 会检查 Point、OTel、MCP Server、LangChain 后端和 WebUI V2，并列出 tmux 会话状态。该脚本说明 Perfa 已经具备基本运行状态检查能力。对于论文测试章节，可以使用这些脚本和接口作为系统可运行性的验证依据，例如检查 `/health`、`/sse?api_key=...`、`/v1/chat/completions` 和 WebUI 页面是否可访问。

## 3.8 本章小结

本章从总体设计角度说明了 Perfa 的设计目标、分层架构、核心业务流程、模块职责、接口与数据流、数据存储和部署拓扑。Perfa 通过 WebUI V2、LangChain Agent、MCP Server 和 Node Agent 四层结构，将自然语言交互、智能编排、工具能力封装和节点执行分离开来。系统既能够支持用户通过对话发起测试，也能够保存任务结果、日志、报告和监控指标等证据，为后续结果分析提供基础。

本章的重点在于建立系统整体视角。第三章说明了各模块之间如何协作，第四章将进一步深入到各子系统内部，结合源码说明 Node Agent 的监控与执行机制、MCP Server 的工具注册与调用机制、LangChain Agent 的工作流和报告持久化机制，以及 WebUI V2 的页面与数据交互实现。
