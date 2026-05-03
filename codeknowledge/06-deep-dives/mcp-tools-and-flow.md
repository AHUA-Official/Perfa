# MCP Server: Tool 清单与调用链

## 入口文件

- `src/mcp_server/main.py`
- `src/mcp_server/server.py`

## 对外协议面

| 路径 | 作用 |
|------|------|
| `/sse` | MCP SSE 连接入口 |
| `/messages/` | MCP POST message 入口 |

## 认证模型

- 当前是 API Key 模式。
- 客户端可以通过查询参数或 `Authorization: Bearer <api_key>` 访问。
- `server.py` 中会在 SSE 入口先校验 Key，不通过则返回 `401`。

## Tool 分组

### 服务器管理

- `register_server`
- `list_servers`
- `remove_server`
- `get_server_info`
- `update_server_info`

### Agent 生命周期

- `deploy_agent`
- `check_agent_status`
- `get_agent_logs`
- `configure_agent`
- `uninstall_agent`

### 工具管理

- `install_tool`
- `uninstall_tool`
- `list_tools`
- `verify_tool`

### Benchmark

- `run_benchmark`
- `get_benchmark_status`
- `cancel_benchmark`
- `get_benchmark_result`
- `list_benchmark_history`

### 报告

- `generate_report`

## 典型调用链

### 注册服务器

```text
tool: register_server
  -> tools/server_tools.py
  -> paramiko 测试 SSH
  -> storage.Database.create_server()
```

### 执行压测

```text
tool: run_benchmark
  -> tools/benchmark_tools.py
  -> db.get_server(server_id)
  -> AgentClient(http://ip:agent_port)
  -> POST /api/benchmark/run
```

### 长任务模式

`run_benchmark` 是立即返回 `task_id` 的异步模式，上层再通过：

- `get_benchmark_status`
- `get_benchmark_result`
- `list_benchmark_history`

继续追踪任务结果。

### 查询服务器实时信息

```text
tool: get_server_info
  -> db.get_server()
  -> AgentClient.get_system_info()
  -> AgentClient.get_system_status()
```

## Tool 到 Node Agent 的桥

`src/mcp_server/agent_client/client.py` 是关键桥接层。它把 MCP Tool 内部调用统一转成对 Node Agent 的 HTTP 请求。

当前已封装的方法包括：

- `health_check`
- `get_status`
- `get_system_info`
- `get_system_status`
- `list_tools`
- `get_tool`
- `install_tool`
- `uninstall_tool`
- `run_benchmark`
- `get_benchmark_status`
- `get_benchmark_result`
- `list_benchmark_results`
- `cancel_benchmark`
- `get_current_task`
- `get_logs`

## 客户端接入说明

旧设计文档中还保留了 AI IDE 接入方式，当前仍有参考价值：

- Cursor 通过 MCP Server URL + API Key 接入
- VSCode Continue 通过 MCP context provider 接入
- 命令行可直接测试 `/sse` 和 MCP message 调用

这些属于“外部接入说明”，不是代码主逻辑，但对联调很有用。

## Agent 部署流

`deploy_agent` 设计上的主流程是：

1. 检查目标机环境
2. 创建安装目录
3. `rsync` 传输 `ops/` 和 `src/node_agent/`
4. 安装 Python 依赖
5. 调用 `ops/scripts/start-point.sh`
6. 验证 Agent 健康状态

## 关键文件索引

| 文件 | 作用 |
|------|------|
| `src/mcp_server/server.py` | MCP Server 组装、Tool 注册、SSE 接入 |
| `src/mcp_server/config.py` | 配置读取 |
| `src/mcp_server/storage/database.py` | 服务器和任务相关持久化 |
| `src/mcp_server/tools/base.py` | Tool 基类 |
| `src/mcp_server/tools/server_tools.py` | 服务器注册与查询 |
| `src/mcp_server/tools/agent_tools.py` | Agent 部署与生命周期 |
| `src/mcp_server/tools/tool_tools.py` | 工具安装与校验 |
| `src/mcp_server/tools/benchmark_tools.py` | 压测调度 Tool |
| `src/mcp_server/tools/report_tools.py` | 报告生成 |
| `src/mcp_server/agent_client/client.py` | 到 Node Agent 的 HTTP 适配器 |

## 改动建议

如果你要改：

- Tool schema，先看对应 `tools/*.py`
- Tool 注册入口，改 `server.py`
- Node Agent 调用格式，改 `agent_client/client.py`
