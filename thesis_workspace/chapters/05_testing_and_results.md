# 第五章 系统测试与结果分析

## 5.1 测试目标与环境

系统测试的目标是验证 Perfa 是否能够支撑自然语言驱动的服务器性能测试平台闭环。前四章已经说明系统由 WebUI V2、LangChain Agent、MCP Server、Node Agent、监控栈和报告模块组成。第五章不再重复设计内容，而是围绕模块功能、接口可用性、运行状态和端到端链路进行验证。由于性能测试结果与硬件环境和服务状态密切相关，本章只使用本轮真实运行输出，不使用模拟数据冒充测试结果。无法完成的测试项会作为环境限制或待修复问题记录。

本轮测试在 `/home/ubuntu/Perfa` 项目目录下进行，测试日期为 2026 年 5 月 3 日。系统端口沿用项目默认配置：Node Agent API 为 8080，Node Agent metrics 为 8000，MCP Server 为 9000，LangChain Agent 为 10000，WebUI V2 为 3002，VictoriaMetrics 为 8428，Grafana 为 3000，Jaeger UI 为 16686。测试命令主要包括 `ops/scripts/status-all.sh`、若干 curl 接口检查和项目自带 unittest 脚本。由于当前环境没有安装 pytest，本章未使用 `python3 -m pytest` 结果，而采用可直接运行的 unittest 脚本和状态检查输出。

测试判定标准包括四类。接口可用性通过 HTTP 状态码和关键返回字段判断；模块功能通过测试脚本的 OK、FAILED、ERROR 输出判断；工作流能力通过场景路由、工具检查、Benchmark 节点和报告节点的测试结果判断；报告和前端能力通过报告页面契约、API helper 和 WebUI 页面访问结果判断。对于失败项，本章不将其隐藏，而是分析失败原因及其对系统可用性的影响。

考虑到 Perfa 的定位是服务器性能测试 Agent Harness，本章还增加证据完整性判定。一次工作流测试不能只看最终回答是否存在，还需要检查 task_id、raw_results、raw_errors、tool_calls、trace_id 和 knowledge_matches 等字段是否被保存或明确说明缺失原因。该判定来自长任务 Agent 工程中“不要提前宣布完成”的原则，但在 Perfa 中转化为性能测试证据清单。若报告只有 AI 结论而缺少原始结果或工具调用记录，则只能说明对话链路可用，不能证明压测任务完整闭环。

## 5.2 测试方案设计

测试方案按照系统分层组织。Node Agent 层重点验证执行器、工具管理、监控采集和 API 健康状态；MCP Server 层重点验证数据库和 AgentClient 等基础能力；LangChain Agent 层重点验证工作流节点、编排器和场景执行；WebUI V2 层重点验证页面契约、前端 API helper 和 Web 首页可访问性；运行状态层通过统一脚本检查本地完整链路是否启动。端到端 prompt-first 测试目录已经提供测试方案，但本轮执行 `test/test_prompt_cases.py` 时出现长时间无输出，未纳入通过结果。

图 5-1 展示了本章测试流程和各层验证结果之间的关系。

表 5-1 给出了测试环境与工具。

| 项目 | 内容 |
|---|---|
| 项目路径 | `/home/ubuntu/Perfa` |
| 测试日期 | 2026-05-03 |
| 主要脚本 | `ops/scripts/status-all.sh`、`test/node_agent/test_executor_runtime.py`、`test/mcp_server/test_database.py`、`test/mcp_server/test_tools.py`、`test/langchain_agent/test_workflow_nodes.py`、`test/webui_v2/test_pages_contract.py` |
| 服务端口 | 8080、8000、9000、10000、3002、8428、3000、16686 |
| 测试约束 | 当前环境缺少 pytest；部分服务接口在沙箱内存在连接不稳定现象 |

表 5-2 给出了测试用例设计。

| 编号 | 测试对象 | 测试命令或脚本 | 预期结果 |
|---|---|---|---|
| TC-1 | 本地完整链路 | `bash ops/scripts/status-all.sh` | 各核心服务就绪，tmux 会话存在 |
| TC-2 | Node Agent 健康检查 | `curl http://127.0.0.1:8080/health` | 返回 success=true 和 healthy 状态 |
| TC-3 | Node Agent 执行器 | `python3 test/node_agent/test_executor_runtime.py` | unittest 通过 |
| TC-4 | MCP 数据库 | `python3 test/mcp_server/test_database.py` | unittest 通过 |
| TC-5 | MCP Tool 与 Benchmark 知识库检索 | `python3 test/mcp_server/test_tools.py` | 工具 schema 和知识库检索测试通过 |
| TC-6 | LangChain 工作流节点 | `python3 test/langchain_agent/test_workflow_nodes.py` | unittest 通过 |
| TC-7 | LangChain Orchestrator | `python3 test/langchain_agent/test_orchestrator.py` | 编排器回归测试通过 |
| TC-8 | WebUI 页面契约 | `python3 test/webui_v2/test_pages_contract.py` | 页面关键文案和代理契约通过 |
| TC-9 | WebUI runtime helper | `python3 test/webui_v2/test_frontend_runtime.py` | 前端 helper 行为通过 |
| TC-10 | WebUI 首页 | `curl -I http://127.0.0.1:3002` | 返回 200 OK |
| TC-11 | Harness 证据清单 | 工作流报告对象和报告页字段检查 | task_ids、raw_results、tool_calls、knowledge_matches 可追溯 |

## 5.3 模块功能测试结果

Node Agent 执行器运行时测试通过。本轮执行 `python3 test/node_agent/test_executor_runtime.py`，输出显示运行 1 个测试用例，结果为 OK。该测试不依赖完整外部压测工具，主要用于验证执行器运行时行为。它可以支撑一个有限结论：Node Agent 的执行器基础逻辑在当前测试脚本覆盖范围内可运行。该结果不能替代真实 fio、stream 或 iperf3 压测结果，因此本章不将其扩展为“所有压测工具均已验证”。

MCP Server 数据库测试通过。本轮执行 `python3 test/mcp_server/test_database.py`，输出显示运行 2 个测试用例，结果为 OK。该结果说明服务器、Agent 或任务相关数据库操作在测试覆盖范围内符合预期。由于 MCP Server 的业务能力依赖服务器记录和 Agent 信息，数据库测试通过为上层工具调用提供了基础保障。该测试属于模块级验证，不能单独证明远端部署和所有 Tool 调用均成功。

MCP Tool 与 Benchmark 知识库检索测试通过。本轮执行 `python3 test/mcp_server/test_tools.py`，输出显示运行 4 个测试用例，结果为 OK。新增用例会实例化 `BenchmarkKnowledgeSearchTool`，使用 `benchmarkknowledge/FurinaBench-main` 作为知识库目录，并以“fio 随机读写 延迟”为查询条件进行检索。测试断言返回 success=true、matches 非空，且命中文件路径中包含 fio。该结果说明本地 FurinaBench Markdown 知识库能够被 MCP 工具读取和检索，为报告知识增强提供了可运行依据。

LangChain 工作流节点测试通过。本轮执行 `python3 test/langchain_agent/test_workflow_nodes.py`，输出显示运行 14 个测试用例，结果为 OK。测试日志中可以看到环境检查、工具检查、工具安装、Benchmark 节点和报告节点等流程。新增报告节点用例会模拟 `search_benchmark_knowledge` 工具返回 fio 文档片段，并断言 `generate_report` 节点把该片段写入 `knowledge_matches`。测试中也出现 hping3 任务长时间 running 后超时的情况，但该情况被测试脚本作为预期流程处理，最终测试仍为 OK。这说明工作流节点具备错误、超时和知识增强路径，而不是只覆盖成功路径。

Harness 证据清单在当前实现中得到部分验证。工作流节点测试覆盖了 server_id 选择、工具检查、工具安装失败、Benchmark 超时、报告节点知识库片段写入等路径；报告 API schema 和前端类型中也已经包含 raw_results、raw_errors、task_ids、tool_calls、trace_id 和 knowledge_matches 字段。受当前测试环境限制，本轮没有完成真实端到端 prompt-first 流程的完整报告字段截图，因此只能判定“模块级证据字段和报告节点逻辑通过”，不能把端到端证据清单写成已经完全验证。

运维脚本测试通过。本轮执行 `python3 test/ops/test_scripts.py`，输出显示运行 3 个测试用例，结果为 OK。测试过程中出现 “Package manager lock conflict” 提示，脚本仍完成测试。这说明相关脚本对包管理锁冲突有一定处理或检测能力。该结果对部署脚本可靠性有参考意义，但不能替代完整远端部署测试。

运行时回归测试通过。本轮执行 `python3 test/regressions/test_runtime_regressions.py`，输出显示运行 2 个测试用例，结果为 OK。回归测试用于防止已修复问题再次出现，结果通过说明当前代码在对应回归场景下保持稳定。由于回归测试覆盖范围通常较窄，本章仅将其作为辅助验证。

表 5-3 汇总了已通过的模块测试。

| 测试项 | 命令 | 运行结果 | 结论 |
|---|---|---|---|
| Node Agent 执行器 | `python3 test/node_agent/test_executor_runtime.py` | Ran 1 test，OK | 执行器基础逻辑通过 |
| MCP 数据库 | `python3 test/mcp_server/test_database.py` | Ran 2 tests，OK | 数据库基础操作通过 |
| MCP Tool 与知识库检索 | `python3 test/mcp_server/test_tools.py` | Ran 4 tests，OK | Tool schema 与 FurinaBench 检索通过 |
| LangChain 工作流节点 | `python3 test/langchain_agent/test_workflow_nodes.py` | Ran 14 tests，OK | 工作流节点和知识增强报告逻辑通过 |
| 运维脚本 | `python3 test/ops/test_scripts.py` | Ran 3 tests，OK | 脚本回归逻辑通过 |
| 运行时回归 | `python3 test/regressions/test_runtime_regressions.py` | Ran 2 tests，OK | 既有回归场景通过 |

## 5.4 接口与运行状态测试结果

本地完整链路状态检查通过。执行 `bash ops/scripts/status-all.sh` 后，输出显示 VictoriaMetrics、Grafana、Node Agent、OTel Collector、Jaeger、MCP Server、LangChain Backend 和 WebUI V2 均处于可用状态。MCP Server 的 `/sse?api_key=test-key-123` 返回 200 OK 和 `text/event-stream`，LangChain Backend 的 `/health` 返回 `{"status":"ok","port":10000}`，WebUI V2 返回 200 OK。tmux 会话检查显示 perfa-node-agent、perfa-mcp-server、perfa-langchain-backend 和 perfa-webui-v2 均存在。该结果说明本地完整开发链路在状态脚本检测时处于启动状态。

Node Agent 健康检查在本轮测试中成功返回。执行 `curl -sS --max-time 10 http://127.0.0.1:8080/health` 得到结果 `success=true`，data 中 status 为 healthy，并包含 uptime_seconds。Node Agent 日志中也记录了来自 127.0.0.1 的 `/health` 访问，返回状态码 200。该结果说明 Node Agent 的健康检查接口可用。

Node Agent 监控日志显示资源采集线程持续运行。`logs/node_agent.log` 中连续出现 `系统监控 [node-agent-001]` 日志，包含 CPU、Memory、Disk 和 NetConn 等字段。例如日志中出现 CPU 约 2.0% 至 19.0%、Memory 约 52.5% 至 53.0%、Disk 约 37.1%、NetConn 约 79 至 92 的记录。这些日志说明 Monitor 后台线程持续执行采集逻辑，监控模块并非只在启动阶段初始化。

接口测试中也发现了一个环境或访问层面的不稳定现象。虽然 `/health` 能成功访问，`status-all.sh` 也报告 Node Agent 运行中，但在当前沙箱内直接访问 `/api/status`、`/api/system/info`、`/api/tools` 和 `:8000/metrics` 时多次出现 `curl: (7) Couldn't connect to server`。该现象没有在日志中表现为 Node Agent 崩溃，监控日志仍持续输出。基于当前证据，更稳妥的结论是：本轮测试确认了健康检查和监控日志可用，但未能完成 Node Agent 其他 API 的直接接口验证。第五章不将这些接口写成通过。

WebUI V2 首页访问通过。执行 `curl -I -sS --max-time 10 http://127.0.0.1:3002` 返回 HTTP/1.1 200 OK，响应头包含 `X-Powered-By: Next.js` 和 `Content-Type: text/html; charset=utf-8`。该结果说明前端服务在 3002 端口可访问，可以支撑答辩演示中的页面入口。

表 5-4 汇总了运行状态和接口检查结果。

| 检查项 | 实际结果 | 判定 |
|---|---|---|
| 完整链路状态脚本 | 核心服务均显示运行，MCP/LangChain/WebUI 返回 200 或健康状态 | 通过 |
| Node Agent `/health` | 返回 success=true、status=healthy | 通过 |
| Node Agent 监控日志 | 连续输出 CPU、Memory、Disk、NetConn | 通过 |
| WebUI V2 首页 | HTTP 200 OK | 通过 |
| Node Agent `/api/status` 等接口 | 当前沙箱内连接失败 | 未通过本轮验证 |
| LangChain `/v1/reports` | 当前 curl 连接失败 | 未通过本轮验证 |

## 5.5 前端与编排层测试结果

WebUI 页面契约测试部分通过。本轮执行 `python3 test/webui_v2/test_pages_contract.py`，输出显示运行 4 个测试用例，其中 3 个通过，1 个失败。失败项为 `test_reports_and_monitor_pages_have_runtime_empty_state_and_proxies`，原因是测试期望 ReportsPage 中包含“暂无测试报告”文案，而当前源码中的空状态文案为“暂无报告，先跑一次完整测试工作流”。该失败不代表报告页面无法运行，而是说明前端文案契约与测试脚本之间存在不一致。该问题可以通过更新测试期望或恢复文案解决。

WebUI runtime helper 测试部分通过。本轮执行 `python3 test/webui_v2/test_frontend_runtime.py`，输出显示运行 5 个测试用例，其中 4 个通过，1 个错误。错误项发生在 `test_api_exposes_trace_and_latest_report_helpers`，脚本通过 Node.js 模拟 fetch，期望 getLatestReport 和 getTraceSummary helper 正确调用报告和 Trace 接口，但实际 Node 子进程返回非零状态。该错误说明前端报告/Trace helper 的契约需要进一步排查，可能与代理路径、编译产物或测试 mock URL 不一致有关。由于该测试直接关联报告详情和 Trace 摘要，后续修复优先级高于普通文案问题。

LangChain Orchestrator 回归测试未通过。本轮执行 `python3 test/langchain_agent/test_orchestrator.py`，输出显示运行 1 个测试用例，结果为 ERROR。错误信息为 `_WorkflowEngine.run() got an unexpected keyword argument 'server_id'`，说明 AgentOrchestrator 调用 WorkflowEngine.run 时传入了 server_id 参数，但测试中的 _WorkflowEngine.run 替身不接受该参数。该问题可能是测试桩与当前实现签名不同步，也可能提示运行时接口变更没有同步更新测试。由于真实工作流节点测试 13 项通过，该问题更接近编排器回归测试契约不一致，但仍需要修复以保证测试体系一致。

端到端 prompt-first 测试未纳入本轮通过结果。执行 `python3 test/test_prompt_cases.py` 后长时间无输出，可能与外部模型调用、服务连接或脚本等待逻辑有关。本轮没有获得可判定的 PASS/FAIL 输出，因此不将其写入已通过测试。`test/e2e_prompts/` 目录中的测试设计仍有价值，它能够记录 prompt、SSE metadata、workflow、最终回答、session detail、trace_id 和人工摘要页。后续在模型服务和网络条件稳定后，应重新运行这些场景测试。

表 5-5 汇总了前端与编排层测试中发现的问题。

| 测试项 | 结果 | 主要问题 | 影响 |
|---|---|---|---|
| WebUI 页面契约 | 4 项中 1 项失败 | 报告空状态文案与测试期望不一致 | 低，偏文案契约 |
| WebUI runtime helper | 5 项中 1 项错误 | 报告/Trace helper 测试子进程失败 | 中，需排查代理路径或 mock |
| LangChain Orchestrator 回归 | 1 项错误 | `server_id` 参数与测试桩签名不一致 | 中，需同步测试或接口 |
| Prompt-first E2E | 未完成 | 脚本长时间无输出 | 中，端到端证据不足 |

## 5.6 测试结果分析

从已完成测试看，Perfa 的底层模块和运行链路具备一定可用性。MCP 数据库、Node Agent 执行器、LangChain 工作流节点、运维脚本和运行时回归测试均通过，说明系统的核心模块并非只停留在设计层面。状态脚本显示本地完整链路已启动，WebUI 首页可以访问，Node Agent 健康检查成功，监控日志持续输出。这些结果支持论文前文关于“平台具备多组件协同基础”的论述。

测试也暴露了三个需要修复或补充验证的问题。其一，部分 Node Agent API 在当前沙箱内无法直接访问，虽然健康检查和监控日志正常，但 `/api/status`、`/api/system/info` 和 `/api/tools` 未在本轮验证中通过。后续需要排查端口监听、网络命名空间、Flask 路由或代理环境差异。其二，前端报告页面和 runtime helper 存在测试契约不一致，说明功能迭代后测试脚本没有完全同步。其三，LangChain Orchestrator 与 WorkflowEngine 的 server_id 参数在回归测试中出现签名不匹配，需要统一实现和测试桩。从 Harness 证据完整性角度看，还需要补充一次真实对话发起压测、生成报告并在 ReportsPage 中查看 task_ids、raw_results、tool_calls 和 knowledge_matches 的端到端截图或接口输出。

这些问题不否定系统总体设计，但说明当前版本距离“完全稳定的产品化平台”仍有距离。对于本科毕业论文而言，可以将其作为系统测试发现和后续改进方向，而不应回避。相比只列出成功测试，真实记录失败项更能说明测试过程具有有效性。后续在答辩前，建议优先修复 Node Agent API 直接访问问题和 Orchestrator 回归测试问题，再补跑 prompt-first E2E 场景，以增强端到端证据。

## 5.7 本章小结

本章对 Perfa 进行了模块测试、运行状态测试、接口测试和前端/编排层测试。测试结果表明，Node Agent 执行器、MCP 数据库、LangChain 工作流节点、运维脚本和运行时回归测试在本轮环境中通过；本地完整链路状态脚本显示核心服务已启动；WebUI V2 首页返回 200 OK；Node Agent 健康检查和监控日志能够证明节点端基础服务与监控线程可用。

本章同时记录了未通过或未完成的测试项，包括部分 Node Agent API 直接访问失败、WebUI 页面契约文案不一致、前端报告/Trace helper 测试错误、Orchestrator 回归测试参数签名不匹配，以及 prompt-first E2E 测试未得到可判定输出。这些问题为第六章总结与展望提供了依据，也为答辩前的工程修复给出了优先级。
