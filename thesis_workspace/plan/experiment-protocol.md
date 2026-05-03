# 第五章测试协议

## 测试目标

验证 Perfa 是否能够完成服务器性能测试平台的主要功能闭环，包括节点执行端、MCP 能力封装层、LangChain Agent 编排层、WebUI V2 前端交互和报告归档。

## 测试对象

- Node Agent API：健康检查、系统信息、监控状态、工具列表、Benchmark 任务、存储日志。
- MCP Server：数据库、工具注册、AgentClient、Tool 调用逻辑。
- LangChain Agent：OpenAI 兼容接口、场景路由、工作流节点。
- WebUI V2：页面结构、API 封装、报告和监控页面契约。
- 端到端链路：WebUI -> LangChain Agent -> MCP Server -> Node Agent。

## 测试环境

- 项目路径：`/home/ubuntu/Perfa`
- 测试日期：2026-05-03
- 运行环境：当前开发环境，以本地完整链路为主。
- 端口约定：Node Agent API 8080，metrics 8000，MCP Server 9000，LangChain Agent 10000，WebUI V2 3002。

## 测试方法

- 静态测试：运行 Python 单元测试和前端契约测试，验证模块逻辑。
- 接口测试：使用 curl 或测试脚本检查健康接口、状态接口和报告接口。
- 功能测试：运行 Node Agent 测试脚本，验证监控、工具、Benchmark 和存储模块。
- 端到端测试：运行 prompt-first e2e 场景脚本或记录其测试设计，用于验证自然语言工作流。
- 运行状态测试：使用 `ops/scripts/status-all.sh` 检查本地完整链路。

## 指标和判定

- 接口可用性：HTTP 状态码、success 字段、关键字段是否存在。
- 功能正确性：测试脚本 PASS/FAIL 数量。
- 工作流完整性：是否出现 workflow metadata、task_id、report_id、trace_id 等关键证据。
- 报告可追溯性：报告是否包含 AI 结论、raw_results、raw_errors、task_ids 和 tool_calls。
- 结果真实性：只使用真实命令输出；未运行的测试只写作规划或限制。

## 数据边界

第五章不使用 mock 数据冒充实验结果。若某项测试因环境、依赖或服务未启动无法完成，应记录为未完成或环境限制，不写成已通过。
