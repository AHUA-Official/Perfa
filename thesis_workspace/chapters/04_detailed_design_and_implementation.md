# 第四章 系统详细设计与实现

## 4.1 Node Agent 执行端设计与实现

Node Agent 是 Perfa 中最接近被测服务器的组件，负责真实资源监控、工具生命周期管理、压测任务执行和结果保存。与上层 Agent 和 MCP Server 不同，Node Agent 直接运行在目标节点上，需要处理系统命令、后台线程、HTTP API、任务并发控制和本地日志文件等工程问题。该组件的设计目标是把节点侧操作封装为稳定接口，使上层系统只需通过 HTTP API 提交请求，而不必直接登录服务器执行命令。

Node Agent 的启动入口位于 `src/node_agent/main.py`。系统启动时会按固定顺序初始化 ToolManager、BenchmarkExecutor、Prometheus metrics 服务、Monitor 后台线程和 Flask API 服务器。该顺序体现了执行端的依赖关系：工具管理器需要先注册各类测试工具，BenchmarkExecutor 依赖工具管理器判断工具是否可用，监控模块需要在节点启动后持续采集资源指标，HTTP API 服务器则将这些能力暴露给 MCP Server 或本地测试脚本。Prometheus metrics 服务默认监听 8000 端口，Flask API 默认监听 8080 端口，业务接口和监控指标分离有利于后续运维和数据采集。

图 4-1 展示了 Node Agent 内部结构及其主要模块关系。

监控模块由 `Monitor` 和多个 Collector 组成。`Monitor` 保存 agent_id、采样间隔和启用的指标类型，启动后在后台线程中循环执行采集逻辑。默认采样间隔为 5 秒，启用 CPU、memory、disk 和 network 四类指标。CPUCollector 使用 psutil 获取 CPU 使用率、核心数和频率，并更新 Prometheus Gauge 指标；MemoryCollector 采集物理内存和 Swap 使用情况；DiskCollector 采集磁盘容量和 I/O 计数；NetworkCollector 采集网络收发字节、包数和连接数。每个采集器不仅返回 Python 字典供日志使用，也会更新 Prometheus 指标，使外部时序数据库能够抓取节点状态。

监控采集采用后台线程而不是阻塞主流程。这样设计的原因在于，Node Agent 需要同时处理 HTTP API 请求和压测任务。如果监控采集占用主线程，压测接口或工具管理接口会受到影响。当前实现中，Monitor 线程在 `running` 标志控制下循环采集，采集异常会记录日志并等待下一个周期，不会导致整个 Node Agent 退出。该设计提高了执行端稳定性，也符合服务器监控任务长期运行的特点。

工具管理模块由 `ToolManager` 统一维护。系统注册的工具覆盖 CPU、内存、磁盘和网络四类测试，包括 UnixBench、SuperPi、sysbench、OpenSSL、stress-ng、7z、STREAM、MLC、fio、hping3 和 iperf3。ToolManager 对外提供 install_tool、check_tool、uninstall_tool、list_tools、install_all 和 check_all 等方法。每个具体工具类负责自身安装、卸载、状态检测和基本信息返回。通过这种方式，Node Agent 将工具差异封装在工具类内部，上层只面对统一的工具名称和状态字段。

工具管理接口位于 `src/node_agent/api/routes/tool.py`。接口包括列出工具、查询单个工具状态、安装工具和卸载工具。安装和卸载接口在执行前会检查是否有 Benchmark 任务正在运行，如果当前节点正在压测，则直接拒绝工具变更请求。该设计避免测试过程中修改二进制或依赖包造成竞态。例如 fio 任务正在运行时卸载 fio，会导致测试结果不可解释，甚至造成任务失败。通过 API 层拦截，Node Agent 将测试执行和工具变更隔离开来。

BenchmarkExecutor 是节点执行端的核心。它负责管理任务生命周期、限制并发任务、调用 Runner、保存日志和收集结果。执行器内部维护当前任务、任务字典、Runner 字典和结果采集器，并使用可重入锁保护当前任务状态。系统限制同一时刻只运行一个 Benchmark 任务，这是性能测试场景中的合理约束。因为多个压测任务同时执行会争用 CPU、磁盘、内存和网络资源，导致结果失去独立性。任务进入执行流程后，执行器会检查工具状态，调用 Runner.prepare，创建工作目录和日志文件，清理执行现场，构建命令，启动子进程，持续读取输出，并在任务结束后解析结果。

图 4-2 展示了 Benchmark 任务从请求校验到结果持久化的生命周期。

Runner 机制用于适配不同测试工具。每个 Runner 对应一种测试类型，负责构造命令、设置超时时间、解析输出和返回指标。Node Agent 当前注册了 fio、stream、unixbench、mlc、superpi、hping3、sysbench_cpu、sysbench_memory、sysbench_threads、openssl_speed、stress_ng、iperf3 和 7z_b 等 Runner。这样的设计将“任务调度通用逻辑”和“具体工具执行逻辑”分离。BenchmarkExecutor 不需要理解每个工具的输出格式，Runner 也不需要关心 HTTP API 和任务队列。新增测试工具时，只需要新增工具类和 Runner 类，并在启动阶段注册。

Benchmark API 位于 `src/node_agent/api/routes/benchmark.py`。`/api/benchmark/run` 接收 test_name 和 params，检查 BenchmarkExecutor 是否初始化、请求体是否存在、test_name 是否有效，以及当前是否已有任务运行。请求合法时，接口调用 executor.run_benchmark 并返回任务结果。系统还提供取消、暂停、恢复、当前任务、任务列表、任务状态、结果查询和日志路径查询等接口。这些接口为 MCP Server 的 Benchmark Tool 提供基础，也便于本地测试脚本直接验证节点执行能力。

结果保存由 ResultCollector 负责。它在本地数据目录下创建 SQLite 数据库 `benchmark_results.db` 和日志目录。每次任务执行时，ResultCollector 创建日志文件，写入任务 ID、测试名称、开始时间和参数，并在执行过程中追加命令输出。任务完成后，ResultCollector 将任务 ID、测试名称、状态、开始时间、结束时间、耗时、参数、指标、主机名、系统信息、内核版本、CPU 型号、日志文件和错误信息保存到 benchmark_results 表中。该设计使测试结果不依赖单次 HTTP 响应保存，即使上层请求结束，也可以通过 task_id 再次查询历史结果。

Node Agent 的 API 服务器基于 Flask 实现。APIServer 在初始化时创建 Flask 应用，将 NodeAgent 实例存入 app.config，并注册 health、monitor、tool 和 benchmark 等蓝图。根路由返回静态控制面板页面，便于本地检查节点状态。所有业务路由都通过统一 response 工具返回 success 或 error_response，使 API 响应结构相对一致。对于上层 MCP Server 而言，这种结构便于 AgentClient 统一解析 success 字段和 data 字段。

表 4-1 总结了 Node Agent 的关键子模块。

| 子模块 | 输入 | 处理过程 | 输出 |
|---|---|---|---|
| Monitor | agent_id、采样配置 | 后台线程周期调用 CPU、内存、磁盘、网络采集器 | 指标字典、Prometheus metrics、日志 |
| ToolManager | 工具名称、类别、权限配置 | 调用具体工具类执行检查、安装、卸载 | 工具状态、版本、路径、安装结果 |
| BenchmarkExecutor | test_name、params | 检查工具、创建任务、调用 Runner、保存日志、收集结果 | task_id、任务状态、BenchmarkResult |
| ResultCollector | BenchmarkTask、metrics | 创建日志文件、写入 SQLite、查询历史结果 | 结果记录、日志路径 |
| APIServer | HTTP 请求 | 注册蓝图、分发路由、统一响应 | JSON API、静态控制面板 |

## 4.2 MCP Server 能力封装层设计与实现

MCP Server 位于 LangChain Agent 和 Node Agent 之间，承担能力封装、协议接入和节点调用转发职责。它的设计目标不是替代 Node Agent 执行真实操作，而是把服务器管理、Agent 生命周期、工具管理、Benchmark 和报告生成组织为标准 MCP Tool，使上层智能体可以通过统一工具接口访问平台能力。

MCP Server 的核心入口位于 `src/mcp_server/server.py`。启动时，系统从环境变量读取 host、port、api_key 和 db_path 等配置，初始化 SQLite 数据库，创建 MCP SDK Server 对象，并调用 `_register_tools()` 注册全部工具。工具注册分为五类：服务器管理、Agent 生命周期管理、测试工具管理、Benchmark 管理和智能报告生成。每个工具继承 BaseTool，提供 name、description、input_schema 和 execute 方法。通过这种结构，MCP Server 可以向上层返回工具列表，也可以根据工具名称和参数调用对应 execute 逻辑。

MCP Server 对外提供 `/sse` 和 `/messages/` 两类协议入口。`/sse` 用于建立 MCP SSE 连接，`/messages/` 用于处理后续消息。SSE 接入阶段会检查查询参数或 Authorization header 中的 API Key，若与配置不匹配则返回 401。该机制不是完整用户权限系统，但为 MCP 调用提供了基本访问边界。通过 SSE 连接，LangChain Agent 可以获取 MCP Server 暴露的工具列表，并发起工具调用。

SQLite 数据库用于保存服务器、Agent 和任务基础记录。servers 表保存被测服务器的 IP、SSH 端口、别名、Agent ID、Agent 端口、权限模式和标签；agents 表保存 Agent 状态、版本和最近在线时间；tasks 表保存压测任务的服务器、Agent、测试名称、参数和状态。该数据库不保存全部 Benchmark 指标，详细结果由 Node Agent 的 ResultCollector 保存。MCP Server 保存的是跨节点管理所需的索引信息，Node Agent 保存的是节点本地执行证据。这种分工降低了中心数据库压力，也符合节点执行结果靠近数据源保存的原则。

AgentClient 是 MCP Server 到 Node Agent 的桥接层。它封装了健康检查、系统信息、系统状态、工具管理、Benchmark、日志和配置更新等 HTTP 请求。MCP Tool 不直接拼接所有 HTTP 细节，而是调用 AgentClient 方法。例如 run_benchmark Tool 先根据 server_id 查询服务器记录，再构造 `http://{server.ip}:{server.agent_port}` 形式的 AgentClient，检查 Agent 是否在线，更新权限配置，检查当前任务，然后向 Node Agent 提交 Benchmark 请求。该过程把服务器记录、节点状态和测试执行串联起来。

Benchmark Tool 是 MCP Server 中与性能测试最直接相关的工具。RunBenchmarkTool 定义了支持的测试枚举和各测试参数 schema，覆盖 unixbench、stream、fio、superpi、mlc、hping3、sysbench、openssl、stress-ng、iperf3 和 7z 等测试。执行时，它检查服务器是否存在、是否已部署 Agent、Agent 是否在线、当前是否已有任务运行，然后调用 Node Agent 的 run_benchmark 接口。若工具未安装，则返回明确错误，提示先调用 install_tool。该设计使大语言模型可以根据错误信息决定后续步骤，例如先安装工具再重试测试。

图 4-3 展示了 MCP Tool 调用从 LangChain Agent 到 Node Agent 的转发流程。

Agent 生命周期工具体现了 Perfa 对远端节点管理的支持。DeployAgentTool 通过 SSH 连接目标服务器，检查 Python、pip、Docker 和 Docker Compose 等运行环境，使用 rsync 传输项目文件，并调用 `ops/scripts/start-point.sh` 或 node_agent 专用启动脚本拉起远端基础设施。部署失败时，工具会尝试收集进程、端口、本地健康检查和日志等诊断信息，避免只返回笼统失败。这部分实现使 Perfa 不只是本地测试页面，也具备向远端服务器部署执行端的能力。由于统一的一键混合部署脚本仍需完善，论文中将该能力定位为“代码支持远端节点部署和诊断”，而不是完整产品化集群管理。

工具管理类 Tool 将 MCP 调用转发为 Node Agent 的工具接口。InstallToolTool、UninstallToolTool、ListToolsTool 和 VerifyToolTool 分别对应工具安装、卸载、列表和校验。由于 Node Agent 会在压测运行期间拒绝安装和卸载，MCP Server 即使收到上层请求，也会得到明确错误结果。这种错误会向上传递给 LangChain Agent，使工作流能够记录失败原因。

报告 Tool 位于 `src/mcp_server/tools/report_tools.py`。GenerateReportTool 支持 single、comparison 和 diagnosis 三类报告。单次报告根据 task_id 或最近一次测试结果生成摘要和基础分析；对比报告获取多次任务结果并计算与基准的差异；诊断报告在基础报告上识别问题并给出建议。除结构化报告工具外，MCP Server 还注册了 `search_benchmark_knowledge` 工具，用于检索本地 FurinaBench Benchmark 知识库中的 Markdown 文档。该工具面向 fio、UnixBench、stream、iperf3 等测试项返回标题、路径、分类、评分和文本片段，为报告生成提供方法解释和注意事项依据。报告 Tool 中还预留了从 VictoriaMetrics 查询 CPU、内存和磁盘 I/O 指标的逻辑。当前报告生成以结构化规则、测试结果字段和本地文档检索增强为主，不应夸大为完整的向量数据库 RAG 报告系统。

表 4-2 总结了 MCP Server 的主要 Tool 分组。

| Tool 分组 | 代表 Tool | 输入 | 输出 | 设计作用 |
|---|---|---|---|---|
| 服务器管理 | register_server、list_servers | IP、SSH 信息、标签 | server_id、服务器列表 | 建立被测节点索引 |
| Agent 生命周期 | deploy_agent、check_agent_status | server_id、部署参数 | Agent 状态、日志、诊断信息 | 管理节点执行端 |
| 工具管理 | install_tool、list_tools | server_id、tool_name | 工具状态、安装结果 | 准备测试环境 |
| Benchmark | run_benchmark、get_benchmark_result | server_id、test_name、params、task_id | task_id、状态、结果 | 调度真实压测任务 |
| 报告 | generate_report | server_id、task_id、report_type | 结构化报告、诊断建议 | 汇总测试结果 |
| 知识库 | search_benchmark_knowledge | query、test_name、category、limit | Benchmark 文档片段和来源路径 | 增强报告解释依据 |

## 4.3 LangChain Agent 智能编排层设计与实现

LangChain Agent 是 Perfa 中连接自然语言和工具调用的编排层。它对外提供 OpenAI 兼容接口，对内加载 MCP Tool，并在工作流模式和 ReAct 模式之间选择执行路径。该层不直接操作服务器，而是通过 MCPToolAdapter 调用 MCP Server 暴露的工具。其核心价值在于将用户的自然语言请求转换为可执行测试流程，并将工具结果组织为用户可读的回答和报告。

LangChain Agent 的 Web API 入口为 `src/langchain_agent/backend/main.py`。FastAPI 应用注册 `/v1` 路由，并在 startup 阶段初始化 Orchestrator。根接口返回服务信息，`/health` 返回健康状态，`/v1/chat/completions` 提供 OpenAI 兼容对话接口。OpenAI 兼容接口便于前端和其他工具以通用格式接入，也使 Perfa 的 Agent 后端可以复用常见聊天客户端的数据结构。

AgentOrchestrator 是编排层核心。初始化时，它创建 ConversationMemory、ReportStore、ErrorHandler、LLM、MCP 工具列表、ReActAgent 和 WorkflowEngine。LLM 使用 OpenAI 兼容形式接入智谱 GLM 模型，MCP 工具来自 MCPToolAdapter 加载结果。Orchestrator 支持 auto 和 react 两种执行模式。auto 模式下，系统优先使用场景路由和工作流处理结构化性能测试请求；无法匹配场景或属于普通对话时，再进入 ReAct 模式。这种设计避免所有请求都进入自由工具调用循环，提高常见性能测试任务的稳定性。

MCPToolAdapter 负责把 MCP Tool 转换为 LangChain 可用工具。它连接 MCP Server 的 SSE 地址，初始化 MCP 会话，获取工具列表，并根据工具 inputSchema 动态创建参数模型。工具调用时，适配器过滤 None 参数，建立临时 SSE 连接，调用 MCP Tool，并解析 structuredContent 或 TextContent。该适配层解决了 MCP 协议对象和 LangChain 工具对象之间的差异，使 Orchestrator 可以像调用普通 LangChain Tool 一样调用 MCP Server 能力。

场景路由模块将用户请求映射为测试场景。系统定义了 quick_test、full_assessment、cpu_focus、storage_focus、network_focus 和 free_chat。路由过程先进行关键词快速匹配，如果请求中包含“全面”“CPU”“磁盘”“网络”“fio”“iperf3”等关键词，则直接选择相应场景；若未命中，则调用 LLM 输出 JSON 格式路由结果。路由结果包含 scenario、confidence 和 reason，低于阈值时回退到 free_chat。该设计兼顾效率和灵活性，对明确性能测试请求快速响应，对模糊请求保留模型判断能力。

工作流引擎用于执行结构化测试流程。WorkflowEngine 构建多个场景图，并支持 route、run 和 run_with_stream。场景节点通常包括环境检查、工具检查、运行具体 Benchmark、收集结果和生成报告。节点执行过程中会更新 node_statuses、completed_nodes 和 current_node。流式模式下，这些状态会通过 metadata 发送给前端，使用户可以看到测试当前处于哪个阶段。与单轮工具调用相比，工作流更适合性能测试这种多步骤任务。

图 4-4 展示了 LangChain Agent 在场景路由、工作流执行、MCP 工具适配和报告持久化之间的编排关系。

报告持久化是 Orchestrator 的重要功能。当工作流返回结果后，`_persist_workflow_report()` 会根据场景、服务器元数据、AI 报告、原始结果、错误记录、任务 ID、工具调用和 Trace ID 构造报告对象，并保存到 ReportStore。报告 ID 使用随机 UUID，标题由场景标签和服务器信息组成，summary 从 AI 报告中抽取前 180 个字符。保存后的 report_id 会写回工作流结果，前端可以根据服务器获取最新报告。该机制把一次对话中的测试过程沉淀为可独立查看的报告记录。

LangChain Agent 的流式输出采用正文与过程事件分离的设计。最终回答通过 `delta.content` 发送，过程信息通过 metadata 发送。过程事件包括 thinking、tool_result、workflow_progress 和 summary 等类型。前端接收到正文后更新聊天消息内容，接收到过程事件后更新事件列表或工作流进度。这种双通道设计适合性能测试场景，因为用户既需要最终结论，也需要知道系统是否正在检查工具、运行测试或生成报告。

从 Agent Harness 角度看，LangChain Agent 的核心实现不是让模型自由调用任意工具，而是把性能测试流程固定为可验证的生命周期。`WorkflowEngine` 构建 quick_test、full_assessment、cpu_focus、storage_focus 和 network_focus 等场景图，节点状态通过 `node_statuses`、`completed_nodes` 和 `current_node` 在状态对象中传递。通用节点函数负责检查环境、选择服务器、检查工具、安装缺失工具、执行 Benchmark、收集结果和生成报告。每个节点都返回结构化状态更新，失败时写入 errors，而不是只把错误写进自然语言回答。这样的设计借鉴了长任务 Agent harness 中“状态文件、进度记录和验证门槛”的思想，但 Perfa 的验证对象换成了服务器性能测试证据。

为避免 Agent 提前宣布完成，Perfa 将关键证据字段写入工作流结果和持久化报告。Benchmark 节点只有在获取 task_id 后才会进入轮询流程，超时或失败会记录到 errors；报告持久化时会保存 raw_results、raw_errors、task_ids、tool_calls、trace_id 和 knowledge_matches。前端报告页也按这些字段拆分展示。由此，用户可以判断一次测试是否真正执行、是否有原始结果、是否有工具调用记录、是否有知识库来源。这种“证据清单”比单纯保存 AI 结论更适合性能测试场景。

表 4-3 总结了 LangChain Agent 的关键对象。

| 对象 | 所在文件 | 主要职责 |
|---|---|---|
| FastAPI App | `backend/main.py` | 提供健康检查和 OpenAI 兼容 API |
| AgentOrchestrator | `core/orchestrator.py` | 管理 LLM、工具、记忆、工作流和报告 |
| MCPToolAdapter | `tools/mcp_adapter.py` | 加载 MCP Tool 并包装为 LangChain Tool |
| ScenarioRouter | `workflows/router.py` | 将用户请求路由到测试场景 |
| WorkflowEngine | `workflows/graph_builder.py` | 构建并执行场景工作流 |
| ReportStore | `backend/report_store.py` | 持久化工作流报告 |

表 4-4 总结了工作流生命周期节点和证据字段的对应关系。

| 生命周期阶段 | 代表实现 | 主要输出字段 |
|---|---|---|
| 服务器选择 | `check_environment`、`select_server` | server_id、server_ip、agent_id、agent_status |
| 工具检查 | `check_tools`、`install_tools` | available_tools、missing_tools、tool_install_failed |
| 压测执行 | `run_benchmark` | task_ids、node_statuses、errors |
| 结果收集 | `collect_results` | results、result_summary |
| 知识增强报告 | `generate_report` | final_report、knowledge_matches、status |
| 持久化归档 | `_persist_workflow_report()` | report_id、raw_results、raw_errors、tool_calls、trace_id |

## 4.4 WebUI V2 交互层设计与实现

WebUI V2 是 Perfa 面向用户的主要界面。它基于 Next.js 14、React、TypeScript、Ant Design、Tailwind CSS、Zustand 和 ECharts 构建，既提供聊天式入口，也提供服务器、报告和监控等结构化页面。与只提供聊天框的系统不同，Perfa 前端需要展示长任务进度、服务器状态、历史报告和原始证据，因此页面结构和状态管理更接近完整控制台应用。

主页面位于 `webui-v2/src/app/page.tsx`，导航项包括 chat、servers、reports 和 monitor。页面使用 Ant Design Layout 和 Menu 组织主界面，并通过 React 状态控制当前页面。chat 页面对应自然语言测试入口，servers 页面对应被测服务器管理，reports 页面对应报告归档，monitor 页面对应资源监控展示。主页面还集成会话列表、会话搜索、新建对话和删除会话等功能，使用户可以回到历史测试上下文。

ChatPage 是对话页核心组件。它从 Zustand store 中获取消息、会话 ID、加载状态和消息更新方法，并维护服务器列表和当前选中的服务器。用户发送消息时，前端先将用户消息加入本地消息列表，再创建一条空的 assistant 流式消息。随后 ChatPage 调用 `/v1/chat/completions`，传入 model、messages、stream、session_id、conversation_id 和 server_id。server_id 来自用户选择的服务器或在线服务器，从而将自然语言请求与具体被测节点关联起来。

前端通过 `consumeSSEStream` 解析后端流式响应。正文 chunk 会追加到 assistant 消息内容中；summary 事件会写入消息摘要；workflow 事件会更新工作流状态；trace_id 和 jaeger_url 会写入消息元数据。流结束后，前端将消息标记为非流式，并在存在 trace_id 时请求 Trace 摘要，在存在服务器 ID 时请求最新报告。这样一次对话不仅产生文本回答，还能自动关联工作流状态、Trace 信息和报告对象。

WorkflowProgress 组件用于展示工作流执行进度。性能测试任务通常需要经历多个阶段，如果前端只显示“正在生成”，用户无法判断系统是否卡住。通过 workflowStatus 中的 scenario、node_statuses、completed_nodes 和 current_node，前端能够显示当前场景和节点状态。该设计与后端 WorkflowEngine 的状态输出对应，使用户在测试过程中获得持续反馈。

ReportsPage 展示测试报告归档。页面加载报告列表后，以卡片形式展示报告类型、场景标签、执行状态、测试数量、服务器信息、创建时间和摘要。点击报告后，抽屉中展示报告详情，包括服务器、场景、状态、Trace ID、来源、摘要、AI 结论、原始结果、任务 ID、错误记录和工具调用。该页面体现了 Perfa 对证据回溯的重视：用户既能阅读 AI 生成的结论，也能检查 raw_results 和 tool_calls，避免报告成为不可验证的自然语言文本。

前端 API 封装集中在 `webui-v2/src/lib/api.ts`。该文件定义 ChatCompletionRequest、ServerInfo、WorkflowStatus、ReportInfo、ReportDetail、TraceSummary 和 SessionSummary 等类型，并封装聊天、服务器、报告、Trace 和会话相关请求。TypeScript 类型有助于减少前后端字段不一致造成的问题。由于前端通过 `/api` 代理访问后端，浏览器端不需要直接访问 LangChain Agent、MCP Server 或 Node Agent 的真实地址，后续也更容易加入统一鉴权。

图 4-5 展示了 WebUI V2 的页面组织、状态管理和前后端数据流。

表 4-5 总结了 WebUI V2 的主要页面。

| 页面 | 关键组件 | 输入 | 输出 | 作用 |
|---|---|---|---|---|
| 对话页 | ChatPage、ChatInput、ChatMessage、WorkflowProgress | 用户消息、服务器选择 | 流式回答、过程事件、报告入口 | 自然语言测试入口 |
| 服务器页 | ServersPage | 服务器 API 数据、用户操作 | 服务器列表、Agent 操作结果 | 管理被测服务器 |
| 报告页 | ReportsPage | 报告列表和详情 | AI 结论、原始结果、错误记录、工具调用 | 展示测试归档 |
| 监控页 | MonitorPage | 指标数据 | 监控图表和状态 | 观察节点资源 |

## 4.5 报告生成与知识增强设计

报告生成是 Perfa 区别于普通压测脚本的重要能力。传统脚本通常只输出命令结果，用户需要人工整理指标、截图、错误日志和结论。Perfa 将报告生成纳入工作流，使测试执行完成后能够自动形成结构化记录，并在前端报告页保存和展示。该模块既体现了系统工作量，也体现了自然语言 Agent 与真实性证据之间的边界设计。

当前系统的报告生成由两条路径组成。第一条路径是 MCP Server 的 GenerateReportTool，它根据 Node Agent 中的 Benchmark 结果生成 single、comparison 或 diagnosis 类型报告。单次报告提取测试名称、状态、耗时、指标摘要和分析结果；对比报告获取多次任务结果，并计算与基准结果的差异；诊断报告在基础报告上识别 CPU、内存或性能瓶颈问题，并给出建议。该路径更偏结构化规则分析，优点是来源明确、字段稳定。

第二条路径是 LangChain Agent 工作流中的 LLM 辅助生成。`generate_report` 节点会优先调用 MCP 报告工具，若工具不可用、server_id 不存在或调用失败，则将已有 results、errors、scenario、server_ip 和用户需求组织为 Prompt，让 LLM 生成 Markdown 格式性能评估报告。若 LLM 也不可用，系统会降级为简单报告生成函数。通过多级降级设计，报告模块不会因为单个工具失败而完全中断，系统可以尽可能向用户返回可读结果。

报告持久化由 AgentOrchestrator 和 ReportStore 完成。工作流结果进入 `_persist_workflow_report()` 后，会被整理为包含 id、type、title、scenario、server_id、server_ip、created_at、status、summary、ai_report、raw_results、raw_errors、knowledge_matches、task_ids、tool_calls、trace_id、query、session_id 和 conversation_id 的对象。ReportStore 将这些对象保存为 JSON 数组，并支持列表查询和按 ID 查询。该结构既适合前端展示，也适合后续扩展为数据库表或向量索引。

前端报告页将报告拆成“AI 结论”“原始结果”“知识依据”和“任务与错误”四个视角。AI 结论用于快速阅读，原始结果用于检查各测试项输出，知识依据用于展示 FurinaBench 文档检索到的标题、路径、分类和片段，任务与错误用于追踪 task_id、raw_errors 和 tool_calls。这样的展示方式避免了只给用户一段不可验证总结的风险。对指导教师而言，该页面也能展示系统从测试执行、知识检索到证据归档的闭环，而不只是调用大模型生成文字。

知识增强设计需要区分已实现能力和扩展预留。当前已实现的部分是基于 `benchmarkknowledge/FurinaBench-main` 的本地 Markdown 检索增强。`src/mcp_server/tools/knowledge_tools.py` 会扫描知识库下的 Markdown 文件，清洗标题、路径和正文，根据 query、test_name、category 以及工具别名进行打分，返回最相关的片段。LangChain 工作流中的 `generate_report` 节点会按测试项调用该工具，将检索结果加入 LLM Prompt，并通过 `knowledge_matches` 字段保存到报告对象。该实现不依赖外部向量数据库，优点是可复现、可测试、引用路径明确，适合作为毕业设计阶段的轻量知识增强能力。

扩展预留部分是向量化 RAG。项目中存在 `codeknowledge/06-deep-dives/`，其内容类似 DeepWiki，用于说明模块接口、调用链和关键文件，当前主要服务于开发维护和论文材料整理。代码中也存在 ChromaDB 配置类，字段包括 collection_name、search_top_k、search_score_threshold 和 embedding_model，并在注释中说明用于历史查询、测试结果持久化和向量检索的未来功能。合理的后续方案是：将工作流报告、Benchmark 结果、错误记录、FurinaBench 文档和 codeknowledge 文档切分为知识片段，通过 embedding 模型写入向量数据库；生成报告时，根据当前测试场景、工具名称、错误类型和服务器标签检索相似历史报告或相关知识文档；LLM 在生成总结时同时参考当前原始结果和检索片段，并在报告中保留引用来源。该方案可以提升报告解释能力，但需要额外实现文档切分、向量入库、检索排序、引用标注和过期数据处理。因此，本文将当前能力表述为“轻量级本地知识库检索增强”，而不是完整 RAG 报告生成。

图 4-6 展示了报告生成与知识增强的设计边界。

```text
已实现链路:
Benchmark 结果 / 错误 / 工具调用
  -> FurinaBench Markdown 知识库检索
  -> generate_report Tool 或 LLM 报告节点
  -> ReportStore
  -> ReportsPage 展示 AI 结论、知识依据与原始证据

扩展预留链路:
历史报告 / FurinaBench 文档 / codeknowledge 文档
  -> Embedding
  -> Vector Store
  -> 相似报告和知识片段检索
  -> RAG 增强报告生成
```

## 4.6 本章小结

本章围绕 Perfa 的核心代码实现进行了详细说明。Node Agent 作为执行端，完成监控采集、工具管理、压测任务执行、日志记录和结果保存；MCP Server 作为能力封装层，将服务器管理、Agent 生命周期、工具管理、Benchmark 和报告能力组织为标准 Tool；LangChain Agent 作为智能编排层，提供 OpenAI 兼容接口、场景路由、工作流执行、MCP 工具适配和报告持久化；WebUI V2 作为交互层，提供对话、服务器、报告和监控页面，并通过 SSE 展示长任务过程。

报告生成与知识增强设计是系统闭环的重要组成部分。当前系统已经实现结构化报告、LLM 辅助总结、FurinaBench 本地知识库检索、报告持久化和前端证据回溯，并为历史测试向量检索和 RAG 增强报告预留了配置与数据基础。下一章将基于这些模块设计测试方案，通过接口测试、功能测试和端到端流程验证系统是否能够稳定完成自然语言驱动的服务器性能测试任务。
