# LangChain Agent

## 定位

`src/langchain_agent/` 是对话与编排层，负责把用户请求转成工具调用，并以 OpenAI 兼容 API 的形式对外提供服务。

## 当前主入口

- Web API 入口: `src/langchain_agent/backend/main.py`
- 主要路由: `src/langchain_agent/backend/openai_api.py`
- 编排核心: `src/langchain_agent/core/orchestrator.py`
- MCP 适配器: `src/langchain_agent/tools/mcp_adapter.py`
- Agent 实现: `src/langchain_agent/agents/react_agent.py`
- 工作流: `src/langchain_agent/workflows/`

## FastAPI 层

`backend/main.py` 当前负责：

- 加载 `.env`
- 创建 FastAPI 应用
- 配置 CORS
- 注册 `/v1` 路由
- 在 startup 阶段初始化编排器

默认端口读取 `LANGCHAIN_API_PORT`，默认值是 `10000`。

## OpenAI 兼容接口

核心端点在 `backend/openai_api.py`：

- `POST /v1/chat/completions`
- 同步和流式两种返回模式
- 流式模式通过 `StreamingResponse` 返回 SSE

### 流式事件设计

当前实现已经把流拆成两类：

- `choices[].delta.content`
  - 承载最终展示给用户的正文
- `metadata`
  - 承载思考、工具调用、工作流进度、统计等过程事件

这说明前端可以区分“最终回答”和“过程面板”。

## 编排层结构

### `AgentOrchestrator`

- 位于 `core/orchestrator.py`
- 负责组织会话、调用 Agent、连接 MCP Tool

### `MCPToolAdapter`

- 位于 `tools/mcp_adapter.py`
- 对接 MCP SSE 服务
- 是 LangChain Agent 与 MCP Server 的桥

### `workflows/`

当前是重要子系统，目录中可见：

- `router.py`
- `nodes.py`
- `graph_builder.py`
- `state.py`
- `scenarios/`

这说明系统已经不仅是单纯 ReAct，还叠加了工作流化执行能力。

## 可观测性

`observability/` 是这个模块的重点增量，包含：

- `tracer.py`
- `metrics.py`
- `instrument_agent.py`
- `instrument_server.py`
- `failure_analyzer.py`

从现有代码和进度文档看，这一层已经接入到 Agent、后端 API、MCP Server、Node Agent 的链路中。

## 目录视图

```text
src/langchain_agent/
├── backend/
├── core/
├── agents/
├── tools/
├── workflows/
├── observability/
├── prompts/
├── start.sh
└── start_backend.sh
```

## 文档可信度判断

- `doc/PROGRESS.md` 对这个模块的近期演进最有帮助，特别是 workflow 和 OTel 改造。
- `src/langchain_agent/PHASE2_DESIGN.md` 可作为阶段设计参考，但当前代码入口仍以 `backend/`、`core/`、`workflows/` 为准。
