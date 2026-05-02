# 架构总览

## 系统目标

Perfa 的核心目标是让“自然语言驱动的服务器性能测试”落地为一套可执行系统：

- 前端负责交互与可视化。
- LangChain Agent 负责理解请求、规划流程、输出回答。
- MCP Server 负责把平台能力包装成标准 Tool。
- Node Agent 负责在被测节点上执行真实操作。

## 组件关系

```text
┌──────────────┐
│   webui-v2   │
└──────┬───────┘
       │ HTTP / SSE
┌──────▼──────────────────────────────────┐
│ src/langchain_agent/backend/main.py     │
│ OpenAI Compatible API                   │
└──────┬──────────────────────────────────┘
       │ MCP adapter
┌──────▼──────────────────────────────────┐
│ src/mcp_server/server.py                │
│ MCP Server over SSE                     │
└──────┬──────────────────────────────────┘
       │ HTTP
┌──────▼──────────────────────────────────┐
│ src/node_agent/main.py                  │
│ Monitor + ToolManager + Benchmark       │
└─────────────────────────────────────────┘
```

## 分层职责

### 1. 交互层

- `webui-v2/`
- 提供对话、服务器管理、报告、监控 UI
- 通过 Next.js API 代理访问 `langchain_agent` 后端

### 2. 智能编排层

- `src/langchain_agent/`
- OpenAI 兼容接口在 `backend/`
- 编排核心在 `core/orchestrator.py`
- MCP 接入在 `tools/mcp_adapter.py`
- 工作流逻辑在 `workflows/`

### 3. 能力封装层

- `src/mcp_server/`
- 对外暴露 MCP SSE 服务
- 内部把服务器管理、Agent 管理、压测、工具安装等封装为 Tool
- 存储使用本地 SQLite

### 4. 执行层

- `src/node_agent/`
- 本地系统信息采集、Prometheus 指标暴露、压测工具生命周期管理、压测任务执行

## 当前运行接口

| 组件 | 主要入口 | 说明 |
|------|----------|------|
| Node Agent | `src/node_agent/main.py` | 启动监控、Prometheus、Flask API、BenchmarkExecutor |
| MCP Server | `src/mcp_server/main.py` | 读取配置并启动 SSE MCP 服务 |
| LangChain Agent | `src/langchain_agent/backend/main.py` | FastAPI，提供 `/v1/chat/completions` 等 |
| Web UI | `webui-v2/src/app/page.tsx` | 主页面壳与多页面入口 |

## 主要数据流

### 对话与工具调用

```text
用户提问
  -> /v1/chat/completions
  -> Orchestrator
  -> MCPToolAdapter
  -> MCP Tool
  -> Node Agent API
  -> 返回工具结果
  -> Agent 生成最终回答
```

### 监控数据

```text
Node Agent Monitor
  -> Prometheus metrics (:8000)
  -> VictoriaMetrics
  -> Grafana
```

### 结果与状态

```text
Benchmark 执行
  -> Node Agent 本地结果 / 日志
  -> MCP Tool 查询与聚合
  -> LangChain Agent / Web UI 展示
```

## 需要注意的现实情况

- 代码中存在“当前实现”和“历史设计稿”并存的情况。
- 一些文档仍保留早期设想，例如更完整的 Agent 分层或部署图，不一定完全映射当前实现。
- 当前知识库以实际入口文件和目录结构为准。
