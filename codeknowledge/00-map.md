# 仓库地图

## 一句话理解项目

Perfa 是一个面向服务器性能测试的多组件系统：

- `src/node_agent/` 运行在被测节点上，负责监控、工具管理、压测执行和 HTTP API。
- `src/mcp_server/` 暴露 MCP SSE 服务，把节点管理、工具操作、压测和报告能力封装成 Tool。
- `src/langchain_agent/` 提供 OpenAI 兼容对话 API，内部通过编排器和 MCP 适配器调用 MCP Tool。
- `webui-v2/` 是当前主用前端，提供对话、服务器、报告、监控页面。

## 当前主线目录

```text
Perfa/
├── codeknowledge/        # 统一知识库
├── ops/                  # 统一的运行、部署、compose 与运维资源
├── doc/                  # 历史方案文档、升级记录
├── src/
│   ├── node_agent/       # 被测节点守护进程
│   ├── mcp_server/       # MCP Server
│   └── langchain_agent/  # 对话 Agent / OpenAI 兼容 API
├── test/                 # Node Agent API 测试脚本与说明
├── webui/                # 旧前端（ChatGPT-Next-Web）
└── webui-v2/             # 当前主用前端
```

## 阅读路径

### 如果你想快速理解系统

- 先看 [01-architecture-overview.md](./01-architecture-overview.md)
- 再看 `02-modules/` 下四个核心模块分册

### 如果你要启动系统

- 看 [03-operations/runtime-and-ports.md](./03-operations/runtime-and-ports.md)
- 再看 [03-operations/deployment-and-startup.md](./03-operations/deployment-and-startup.md)

### 如果你要改接口或联调

- Node Agent API: `02-modules/node-agent.md`
- MCP Tool 层: `02-modules/mcp-server.md`
- OpenAI 兼容 API / SSE: `02-modules/langchain-agent.md`
- 前端代理与页面结构: `02-modules/webui-v2.md`

### 如果你在核对旧文档是否还能信

- 看 [05-doc-source-index.md](./05-doc-source-index.md)

## 当前代码层面的主链路

```text
用户
  -> webui-v2
  -> langchain_agent backend (/v1/chat/completions)
  -> AgentOrchestrator + MCPToolAdapter
  -> mcp_server (/sse, /messages/)
  -> tool execute()
  -> node_agent HTTP API
  -> benchmark / monitor / tool manager
```

## 当前代码中的辅助目录

- `ops/assets/vm/` - VictoriaMetrics 抓取配置
- `ops/assets/grafana/` - Grafana dashboard 与 provisioning 资源
- `ops/assets/otel/` - OTel Collector 配置
- `ops/compose/` - Compose 文件
- `ops/scripts/` - 启动、停止、状态与部署脚本
- `src/mcp_server/examples/` - Cursor 和 VSCode 的 MCP 配置示例
- `test/node_agent/` - Node Agent 接口测试脚本

## 当前判断

- `webui-v2/` 是当前主前端。
- `webui/` 是旧方案，除非明确需要兼容，否则不应作为主文档入口。
- `doc/PROGRESS.md` 对理解最近演进很有价值，但它是阶段性记录，不应代替模块文档。
- `src/node_agent/design.md` 和 `src/mcp_server/mcp_design.md` 有参考价值，但部分内容属于设计视角，不完全等于当前代码状态。
