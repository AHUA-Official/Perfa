# Perfa 升级实施进度追踪

> 最后更新: 2026-04-28 00:50 | 当前阶段: Phase 1-3 主体完成，剩余前端面板 + 全局集成测试

---

## 项目上下文（会话恢复必读）

### 项目概述
Perfa 是一个基于 LangChain 的服务器性能测试平台（UESTC 本科毕设），当前架构：
- **LangChain Agent** (`src/langchain_agent/`): ReAct + LangGraph 工作流双模式，通过 MCP 协议调用 20 个工具
- **MCP Server** (`src/mcp_server/`): 20 个工具注册，SSE 协议，端口 9000
- **Node Agent** (`src/node_agent/`): 被测节点上的压测执行器，串行执行，Flask API 端口 8080
- **Web 前端 V1** (`webui/`): 开源方案 ChatGPT-Next-Web (Docker, 端口 3001)
- **Web 前端 V2** (`webui-v2/`): 自研 Next.js 14 + AntD 5 (端口 3002)
- **OTel 可观测性**: OTel Collector + Jaeger (部署配置已就绪，尚未启动)

### 升级规格文档
- `doc/UPGRADE_SPEC.md` — 完整升级规格说明书

### 当前运行服务（tmux 会话）
- `perfa-agent` — LangChain Agent API（端口 10000），已启用 OTel
- `perfa-webui` — Web 前端 V2（端口 3002）
- MCP Server 在远程服务器 `118.25.19.83:9000` 上运行（不在本机 tmux）
- Node Agent 在被测服务器 `49.234.47.133:8080` 上运行

### 启动命令
```bash
# Agent API（必须从 src/ 目录启动）
cd /home/ubuntu/Perfa/src && OTEL_CONSOLE_EXPORT=true python3 -c "import uvicorn; from langchain_agent.backend.main import app, API_PORT; uvicorn.run(app, host='0.0.0.0', port=API_PORT)"

# Web 前端 V2
cd /home/ubuntu/Perfa/webui-v2 && npm run dev

# MCP Server（如需本地启动）
cd /home/ubuntu/Perfa/src/mcp_server && python3 -m mcp_server
```

### 关键代码位置

| 模块 | 文件 | 说明 |
|------|------|------|
| Agent 核心 | `src/langchain_agent/agents/react_agent.py` | ReAct Agent，含 OTel span 埋点（run/_think/_act） |
| 编排器 | `src/langchain_agent/core/orchestrator.py` | AgentOrchestrator，含 _init_otel() + OTel span |
| 工作流节点 | `src/langchain_agent/workflows/nodes.py` | 9 个通用节点，make_node 自动注入 OTel span + 故障分析器 |
| 工作流引擎 | `src/langchain_agent/workflows/graph_builder.py` | WorkflowEngine，5 个场景 |
| 场景路由 | `src/langchain_agent/workflows/router.py` | 关键词+LLM 路由，6 个场景定义 |
| MCP 适配器 | `src/langchain_agent/tools/mcp_adapter.py` | MCPToolAdapter，过滤 None 参数 |
| 配置 | `src/langchain_agent/core/config.py` | LLMConfig(ZhipuAI GLM-5), MCPConfig, AgentConfig |
| 后端 API | `src/langchain_agent/backend/openai_api.py` | OpenAI 兼容 API + 扩展端点（含服务器实时状态查询） |
| 后端入口 | `src/langchain_agent/backend/main.py` | FastAPI app，端口 10000，含 load_dotenv() |
| 数据模型 | `src/langchain_agent/backend/schemas.py` | ChatRequest/Response/ServerInfo/WorkflowStatus/Report 等 |
| OTel Tracer | `src/langchain_agent/observability/tracer.py` | TracerProvider + OTLP/Console 导出 |
| OTel Metrics | `src/langchain_agent/observability/metrics.py` | 8 个核心指标 + record_benchmark/tool_call/llm 便捷函数 |
| OTel Agent 埋点 | `src/langchain_agent/observability/instrument_agent.py` | @traced 装饰器、SpanContext、指标便捷函数 |
| OTel Server 埋点 | `src/langchain_agent/observability/instrument_server.py` | StarletteInstrumentor 注入 |
| AI 故障分析 | `src/langchain_agent/observability/failure_analyzer.py` | LLM 诊断 + 规则降级，集成到 handle_error |
| MCP Server | `src/mcp_server/server.py` | 含 StarletteInstrumentor OTel 注入 |
| Node Agent | `src/node_agent/main.py` | 含 FlaskInstrumentor OTel 注入 |
| 前端主页 | `webui-v2/src/app/page.tsx` | 对话页，AntD Menu 侧边栏 |
| 前端服务器页 | `webui-v2/src/components/servers/ServersPage.tsx` | 服务器管理 + 注册 Modal |
| 前端 API | `webui-v2/src/lib/api.ts` | API_BASE = '/api' |
| 前端 SSE | `webui-v2/src/lib/sse.ts` | SSE 流式解析 |
| Next.js 代理 | `webui-v2/next.config.js` | /api/v1/* → http://localhost:10000/v1/* |

### 环境变量
```
# src/langchain_agent/.env
ZHIPU_API_KEY=<智谱AI API Key>
ZHIPU_BASE_URL=https://open.bigmodel.cn/api/paas/v4
ZHIPU_MODEL=glm-4-flash
MCP_API_KEY=test-key-123

# OTel（可选，启动时设置）
OTEL_EXPORTER_OTLP_ENDPOINT=localhost:4317  # OTLP gRPC 端点
OTEL_CONSOLE_EXPORT=true                     # 控制台导出（调试）
```

### 端口
| 服务 | 端口 | 状态 |
|------|------|------|
| MCP Server | 9000 | 远程 118.25.19.83 |
| LangChain Agent API | 10000 | ✅ 运行中 |
| Perfa Web V1 (ChatGPT-Next-Web) | 3001 | Docker |
| Perfa Web V2 (自研) | 3002 | ✅ 运行中 |
| OTel Collector | 4317/4318 | ⬜ 未启动（需 Docker） |
| Jaeger UI | 16686 | ⬜ 未启动（需 Docker） |
| VictoriaMetrics | 8428 | Docker |
| Grafana | 3000 | Docker |
| Node Agent API | 8080 | 49.234.47.133 |
| Node Agent Metrics | 8000 | 49.234.47.133 |

### 已注册测试服务器
- **49.234.47.133** (alias: Test Server, server_id: d431b000-d943-474f-a392-18dce93b0b47)
  - Agent 状态: online
  - Agent 版本: 1.0.0
  - Agent ID: node-agent-001

---

## 实施进度

### Phase 1: LangGraph 工作流编排 ✅ 完成

| 步骤 | 状态 | 说明 |
|------|------|------|
| 1.1 创建 `workflows/state.py` | ✅ | WorkflowState TypedDict + create_initial_state |
| 1.2 创建 `workflows/router.py` | ✅ | ScenarioRouter + 6 场景定义，关键词匹配+LLM 路由 |
| 1.3 创建 `workflows/nodes.py` | ✅ | 9 个通用节点函数，含 OTel span 自动注入 |
| 1.4 创建 `workflows/graph_builder.py` | ✅ | WorkflowEngine，统一构建注册5个场景图 |
| 1.5-1.9 创建 5 个场景 | ✅ | quick_test / full_assessment / cpu_focus / storage_focus / network_focus |
| 1.10 修改 `orchestrator.py` 集成工作流 | ✅ | process_query 新增 auto/react/workflow 三种模式 |
| 1.11 添加 langgraph 依赖 | ✅ | requirements.txt 添加 langgraph>=0.2.0 |
| 1.12 端到端测试 | ✅ | 场景路由正常，工作流节点执行正确 |

### Phase 2: 自研 Web 前端 ✅ 主体完成

> 两套前端并存：`webui/`(开源 ChatGPT-Next-Web, Docker 3001) 和 `webui-v2/`(自研 Next.js, 3002)

| 步骤 | 状态 | 说明 |
|------|------|------|
| 2.1 初始化 Next.js 项目 | ✅ | `webui-v2/` 目录，手动创建，npm 淘宝镜像 |
| 2.2 全局布局 + 对话页基础 | ✅ | AntD 暗色主题侧边栏 + 对话消息流 + 快捷场景按钮 |
| 2.3 SSE 流式 + Markdown | ✅ | `lib/sse.ts` 流式解析 + react-markdown + react-syntax-highlighter |
| 2.4 工作流进度条 | ✅ | `WorkflowProgress` 组件，4 种节点状态 |
| 2.5 测试结果卡片 | ✅ | `ResultCard` 组件 |
| 2.6 服务器管理页 | ✅ | `ServersPage.tsx` + 注册 Modal（含 SSH 表单）+ 详情 Drawer |
| 2.7 报告页 | ✅ | `ReportsPage.tsx` 卡片布局 |
| 2.8 后端扩展 API | ✅ | 7 个端点已实现: /v1/servers, /v1/servers/register, /v1/servers/{id}, /v1/workflows/status/{id}, /v1/reports, /v1/reports/{id} |
| 2.9 服务器实时状态 | ✅ | list_servers API 调用 check_agent_status 获取实时状态 |
| 2.10 Docker 构建 | ✅ | Dockerfile 已创建 |

### Phase 3: OTel 可观测性 + AI 故障分析 ✅ 主体完成

| 步骤 | 状态 | 说明 |
|------|------|------|
| 3.1 OTel SDK 配置 | ✅ | observability/tracer.py + metrics.py（8 个指标） |
| 3.2 Agent 侧 Instrumentation | ✅ | react_agent.py: run/_think/_act 三层 span + 指标记录；nodes.py: make_node 自动注入 span + 压测指标 |
| 3.3 Orchestrator 集成 | ✅ | _init_otel() 初始化 + process_query 顶层 span + 活跃会话指标 |
| 3.4 MCP Server Instrumentation | ✅ | instrument_server.py + server.py StarletteInstrumentor 注入 |
| 3.5 Node Agent Instrumentation | ✅ | main.py FlaskInstrumentor + OTel Tracer 初始化 |
| 3.6 AI 故障分析器 | ✅ | failure_analyzer.py（LLM 诊断 + 规则降级）→ 集成到 nodes.py handle_error |
| 3.7 Instrumentation 辅助 | ✅ | instrument_agent.py（@traced 装饰器、SpanContext、指标便捷函数） |
| 3.8 OTel 依赖声明 | ✅ | 三个 requirements.txt 均已添加 opentelemetry 依赖 |
| 3.9 部署配置 | ✅ | deploy/otel/otel-collector-config.yaml + docker-compose.yml（Collector + Jaeger） |
| 3.10 端到端验证 | ✅ | Agent 重启成功，OTel Tracing+Metrics 初始化正常，控制台导出可用 |

### 剩余工作 ⬜

| 步骤 | 状态 | 说明 |
|------|------|------|
| 3.11 前端可观测性面板 | ⬜ | webui-v2 添加监控页，嵌入 Jaeger UI + Grafana iframe |
| 4.1 启动 OTel Collector + Jaeger | ⬜ | `cd deploy/otel && docker compose up -d`，配置 OTEL_EXPORTER_OTLP_ENDPOINT |
| 4.2 全局集成测试 | ⬜ | 完整流程测试：前端→Agent→工作流→MCP→压测→OTel→故障分析 |
| 4.3 前端优化 | ⬜ | ECharts 图表、报告详情页、监控数据展示 |
| 4.4 文档整理 | ⬜ | 更新 README、部署文档 |

---

## 已修复的 Bug 记录

| 问题 | 原因 | 修复 |
|------|------|------|
| npm install 极慢 | 默认源国内访问慢 | `npm config set registry https://registry.npmmirror.com` |
| `ServerOutlined` 不存在 | AntD Icons v5 没有 | 改用 `DesktopOutlined` |
| SyntaxHighlighter 类型错误 | 版本不匹配 | `@types/react-syntax-highlighter: ^15.5.13`，`style as any` |
| 静态生成 server/client 冲突 | layout 混用 | 提取 `AntdProvider` 为独立 `'use client'` 组件 |
| MCP tools count = 0 | .env 未加载 | main.py 添加 `load_dotenv()` |
| MCP register_server None 参数错误 | MCP 不接受 null | mcp_adapter.py 过滤 None 值 |
| 前端看不到服务器 | API_BASE 和 rewrite 路径错误 | API_BASE=''/api'' + rewrite `/api/v1/:path*` |
| select_server 总选第一台 | 字段名错误 | `get("id")` → `get("server_id", get("id"))` + IP 匹配 |
| 前端 JSON 解析 500 错误 | 非 JSON 响应 | ServersPage 添加 try/catch |
| 服务器状态"未知" | list_servers 用 status 字段，MCP 返回 agent_status | 调用 check_agent_status 获取实时状态 + agent_status 映射 |
| Agent 模块找不到 | 从 langchain_agent/ 目录启动 | 必须从 `src/` 目录启动：`cd src && python3 -c ...` |

---

## 已修改文件清单

### Phase 1 新增
```
src/langchain_agent/workflows/__init__.py
src/langchain_agent/workflows/state.py
src/langchain_agent/workflows/router.py
src/langchain_agent/workflows/nodes.py        ← OTel span + 故障分析器
src/langchain_agent/workflows/graph_builder.py
src/langchain_agent/workflows/scenarios/__init__.py
src/langchain_agent/workflows/scenarios/quick_test.py
src/langchain_agent/workflows/scenarios/full_assessment.py
src/langchain_agent/workflows/scenarios/cpu_focus.py
src/langchain_agent/workflows/scenarios/storage_focus.py
src/langchain_agent/workflows/scenarios/network_focus.py
```

### Phase 2 新增
```
webui-v2/  （整个目录）
```

### Phase 2 修改
```
src/langchain_agent/backend/openai_api.py     ← 扩展 API + 实时状态查询
src/langchain_agent/backend/schemas.py         ← ServerInfo/WorkflowStatus/Report schemas
src/langchain_agent/backend/main.py            ← load_dotenv()
```

### Phase 3 新增
```
src/langchain_agent/observability/__init__.py
src/langchain_agent/observability/tracer.py
src/langchain_agent/observability/metrics.py
src/langchain_agent/observability/instrument_agent.py
src/langchain_agent/observability/instrument_server.py
src/langchain_agent/observability/failure_analyzer.py
src/node_agent/requirements.txt                ← 新建
deploy/otel/otel-collector-config.yaml
deploy/otel/docker-compose.yml
```

### Phase 3 修改
```
src/langchain_agent/requirements.txt           ← +opentelemetry 依赖
src/mcp_server/requirements.txt                ← +opentelemetry 依赖
src/mcp_server/server.py                       ← +StarletteInstrumentor
src/node_agent/main.py                         ← +FlaskInstrumentor + OTel 初始化
src/langchain_agent/agents/react_agent.py      ← +OTel span (run/_think/_act)
src/langchain_agent/core/orchestrator.py       ← +_init_otel() + 顶层 span + 指标
src/langchain_agent/workflows/nodes.py         ← +OTel span + 故障分析器集成
```

---

## 决策记录

| 日期 | 决策 | 原因 |
|------|------|------|
| 2026-04-27 | LangGraph 并行执行先串行 fallback | Node Agent 有 is_busy() 串行限制，Agent 侧并行无意义 |
| 2026-04-27 | 路由器置信度阈值 0.7 | 低于此值走原 ReAct，保证兼容性 |
| 2026-04-27 | 前端用 Next.js 14 + AntD 5 | React 生态主流，中文友好，表格/图表组件丰富 |
| 2026-04-28 | 保留两套前端方案 | webui/ 保留 ChatGPT-Next-Web 开源方案，webui-v2/ 自研，并存 |
| 2026-04-28 | npm 镜像切换淘宝源 | 国内访问默认源极慢，npmmirror.com 秒级安装 |
| 2026-04-28 | OTel 初始化优雅降级 | ImportError 时 warning 而非崩溃，不影响核心功能 |
| 2026-04-28 | 故障分析器 LLM+规则双模式 | LLM 不可用时自动降级到规则推断 |
| 2026-04-28 | 服务器状态实时查询 | list_servers API 调用 check_agent_status，而非依赖静态字段 |

---

## 明天待做（优先级排序）

1. **启动 OTel Collector + Jaeger** — `cd deploy/otel && docker compose up -d`，然后设置 `OTEL_EXPORTER_OTLP_ENDPOINT=localhost:4317` 重启 Agent
2. **前端可观测性面板** — webui-v2 添加监控页，iframe 嵌入 Jaeger UI (16686) + Grafana (3000)
3. **全链路集成测试** — 前端→Agent→工作流→MCP→压测→OTel trace→Jaeger 可视化
4. **ECharts 图表** — 报告详情页添加性能指标图表
5. **文档整理** — 更新 README、部署文档
