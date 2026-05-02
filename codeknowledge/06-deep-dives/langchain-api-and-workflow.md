# LangChain Agent: API、SSE 与工作流

## 入口文件

- `src/langchain_agent/backend/main.py`
- `src/langchain_agent/backend/openai_api.py`

## 当前主要 API

### OpenAI 兼容

| 路径 | 方法 | 作用 |
|------|------|------|
| `/` | GET | 根信息 |
| `/health` | GET | 健康检查 |
| `/v1/chat/completions` | POST | 同步或流式对话 |

### 扩展数据模型

从 `backend/schemas.py` 可以确认系统还维护了这些响应模型：

- `ServerInfo`
- `WorkflowStatusResponse`
- `ReportInfo` / `ReportDetail`
- `SessionSummary` / `SessionDetail`

这说明 `/v1` 下不仅有对话，也有服务器、报告、工作流和会话相关扩展端点。

## 对话调用链

### 同步模式

```text
POST /v1/chat/completions
  -> chat_completions()
  -> get_orchestrator()
  -> orchestrator.process_query()
  -> format_response_markdown()
```

### 流式模式

```text
POST /v1/chat/completions (stream=true)
  -> StreamingResponse(stream_chat_response)
  -> orchestrator.process_query_stream()
  -> SSE chunk 输出
```

## SSE 双通道设计

后端流式响应当前有两个层次：

- `delta.content`
  - 最终回答正文
- `metadata`
  - thinking、tool_result、workflow_progress、summary 等过程事件

这套设计直接对应前端 `webui-v2/src/lib/sse.ts` 的解析逻辑。

## 编排与工作流

### 编排核心

- `src/langchain_agent/core/orchestrator.py`

### 路由

- `src/langchain_agent/workflows/router.py`
- 当前预定义场景：
  - `quick_test`
  - `full_assessment`
  - `cpu_focus`
  - `storage_focus`
  - `network_focus`
  - `free_chat`

### 图构建

- `src/langchain_agent/workflows/graph_builder.py`
- `WorkflowEngine` 会构建多个场景图并支持 `route()`、`run()`、`run_with_stream()`

### 场景实现

- `src/langchain_agent/workflows/scenarios/quick_test.py`
- `src/langchain_agent/workflows/scenarios/full_assessment.py`
- `src/langchain_agent/workflows/scenarios/cpu_focus.py`
- `src/langchain_agent/workflows/scenarios/storage_focus.py`
- `src/langchain_agent/workflows/scenarios/network_focus.py`

## 关键文件索引

| 文件 | 作用 |
|------|------|
| `src/langchain_agent/backend/main.py` | FastAPI 应用入口 |
| `src/langchain_agent/backend/openai_api.py` | 对话接口、SSE 流式输出 |
| `src/langchain_agent/backend/schemas.py` | API 数据模型 |
| `src/langchain_agent/core/orchestrator.py` | 编排核心 |
| `src/langchain_agent/tools/mcp_adapter.py` | MCP 适配层 |
| `src/langchain_agent/agents/react_agent.py` | ReAct Agent |
| `src/langchain_agent/workflows/router.py` | 场景路由 |
| `src/langchain_agent/workflows/graph_builder.py` | 场景图管理 |
| `src/langchain_agent/workflows/nodes.py` | 工作流节点逻辑 |
| `src/langchain_agent/observability/` | tracing、metrics、故障分析 |

## 改动建议

如果你要改：

- OpenAI 兼容层，先看 `backend/openai_api.py`
- SSE 事件格式，前后端一起看 `openai_api.py` 和 `webui-v2/src/lib/sse.ts`
- 场景路由，先看 `workflows/router.py`
- 工作流执行图，先看 `workflows/graph_builder.py` 和 `workflows/scenarios/`
