# 历史与运行上下文

这个文件吸收了旧文档中仍然有价值、但不适合散落在各处的内容：

- 当前联调环境
- 环境变量与运行方式
- 近期升级阶段
- 关键决策与已知限制
- 历史方案与当前主线的关系

## 当前联调环境

根据最近一轮进度记录，项目存在一个“本地 + 远端混合”运行形态：

- 本地运行：
  - `LangChain Agent API`，端口 `10000`
  - `webui-v2`，端口 `3002`
- 远端运行：
  - `MCP Server`，`118.25.19.83:9000`
  - `Node Agent`，`49.234.47.133:8080`

这说明仓库的运行方式不只是一种“全本地开发模式”。

## 当前重要环境变量

### LangChain Agent

```bash
ZHIPU_API_KEY=<智谱 AI Key>
ZHIPU_BASE_URL=https://open.bigmodel.cn/api/paas/v4
ZHIPU_MODEL=glm-4-flash
MCP_API_KEY=test-key-123
```

### OpenTelemetry

```bash
OTEL_EXPORTER_OTLP_ENDPOINT=localhost:4317
OTEL_CONSOLE_EXPORT=true
```

## 常用启动方式

### LangChain Agent API

```bash
cd /home/ubuntu/Perfa/src
python3 -c "import uvicorn; from langchain_agent.backend.main import app, API_PORT; uvicorn.run(app, host='0.0.0.0', port=API_PORT)"
```

注意：这一层需要从 `src/` 启动，避免包导入路径错误。

### Web UI V2

```bash
cd /home/ubuntu/Perfa/webui-v2
npm run dev
```

### MCP Server 本地启动

```bash
cd /home/ubuntu/Perfa/src/mcp_server
python3 main.py
```

## 历史演进摘要

### 最初方案

最早的简版设计更像：

```text
AI IDE -> MCP Server -> LangChain Agent -> SSH 执行器 -> 目标服务器
```

它强调的是“最小可落地原型”：

- `paramiko`
- SQLite
- 简单 MCP Tool
- 先把 SSH 与单项测试打通

### 当前实现

当前已经演进成更完整的多组件系统：

- Node Agent 独立部署在被测节点
- MCP Server 负责统一 Tool 封装
- LangChain Agent 同时支持 ReAct 与 Workflow
- Web UI V2 提供专属前端
- OTel 已进入代码层

## 升级阶段总结

### Phase 1

- 引入 LangGraph 工作流
- 加入 5 个测试场景和 1 个 free_chat 场景

### Phase 2

- 从旧 `webui/` 过渡到 `webui-v2/`
- 后端扩展了服务器、报告、会话等 API

### Phase 3

- 接入 OTel tracing / metrics
- 引入 AI 故障分析器

## 最近实现状态

根据最后一份进度记录，当前可视为：

- Phase 1 已完成
- Phase 2 主体完成
- Phase 3 主体完成

仍待继续推进的事项包括：

- 前端可观测性面板
- OTel Collector + Jaeger 实际启动联调
- 全链路集成测试
- 报告图表与监控增强

## 关键决策

- Node Agent 当前串行执行任务，因此工作流层虽然支持多场景编排，但真正压测执行不做并行假设。
- 场景路由置信度阈值设为 `0.7`，低于阈值走 `free_chat`。
- 保留两套前端曾是阶段性决策，但当前主线是 `webui-v2/`。
- OTel 初始化采取优雅降级，缺依赖时不让核心功能崩掉。
- 服务器状态查询优先走实时接口，而不是依赖注册时的静态字段。

## 已知历史 Bug 与经验

- `npm install` 国内镜像问题：项目曾通过 `npmmirror` 加速。
- 从错误目录启动 LangChain Agent 会导致模块导入失败。
- MCP 参数里传 `null` 曾导致问题，后续适配器做了 `None` 过滤。
- 服务器状态字段曾有命名不一致问题，后来通过实时查询补正。

## 历史修改重点

最近一轮大改动主要集中在这些目录：

- `src/langchain_agent/workflows/`
- `src/langchain_agent/observability/`
- `src/langchain_agent/backend/`
- `webui-v2/`
- `ops/assets/otel/`

如果你在追代码演进，优先从这些目录看起。

## 当前仍未完成的事项

- OTel Collector + Jaeger 实际运行与联调
- 前端可观测性面板
- 更完整的全链路集成测试
- 报告图表与监控展示增强
