# MCP Server

## 定位

`src/mcp_server/` 是平台能力封装层。它把服务器管理、Agent 管理、工具管理、压测、报告等能力注册成 MCP Tool，供上层 Agent 以标准协议调用。

## 代码入口

- 主入口: `src/mcp_server/main.py`
- 核心服务: `src/mcp_server/server.py`
- 配置: `src/mcp_server/config.py`
- 数据存储: `src/mcp_server/storage/`
- Tool 定义: `src/mcp_server/tools/`
- Node Agent 客户端: `src/mcp_server/agent_client/`

## 启动逻辑

`main.py` 的逻辑很薄：

1. `Config.from_env()` 读取环境变量
2. 初始化 `MCPServer`
3. 调用 `server.run()`

真正的注册和协议处理都在 `server.py`。

## 当前协议实现

### 对外暴露

- SSE 入口: `/sse`
- POST message 入口: `/messages/`

### 服务器框架

- MCP SDK: `mcp.server.Server`
- Web 容器: `Starlette`
- 运行方式: `uvicorn.run(...)`

## Tool 注册

当前 `MCPServer._register_tools()` 分成五组：

### 服务器管理

- `RegisterServerTool`
- `ListServersTool`
- `RemoveServerTool`
- `GetServerInfoTool`
- `UpdateServerInfoTool`

### Agent 生命周期

- `DeployAgentTool`
- `CheckAgentStatusTool`
- `GetAgentLogsTool`
- `ConfigureAgentTool`
- `UninstallAgentTool`

### 工具管理

- `InstallToolTool`
- `UninstallToolTool`
- `ListToolsTool`
- `VerifyToolTool`

### Benchmark

- `RunBenchmarkTool`
- `GetBenchmarkStatusTool`
- `CancelBenchmarkTool`
- `GetBenchmarkResultTool`
- `ListBenchmarkHistoryTool`

### 报告

- `GenerateReportTool`

## 数据依赖

- 本地数据库对象为 `Database(config.db_path)`
- 存储实现位于 `src/mcp_server/storage/`
- 每个 Tool 都继承 `BaseTool`

## 对下游的连接

MCP Server 不直接执行压测。它通过 `agent_client/` 去连接 Node Agent，再把结果转成 Tool 响应。

## 目录视图

```text
src/mcp_server/
├── main.py
├── server.py
├── config.py
├── agent_client/
├── storage/
├── tools/
└── examples/
```

## 配置与示例

- `examples/` 中有 Cursor 和 VSCode 的 MCP 配置样例
## 文档可信度判断

- Tool 数量、部署细节、内部调用路径应优先以 `server.py`、`tools/`、`agent_client/` 和 `ops/` 下的当前脚本为准。
