# Perfa 系统升级规格说明书

> 版本: v1.0 | 日期: 2026-04-27 | 状态: **待审批**

---

## 一、升级目标概述

本次升级针对三个核心方向，解决"业务流编排能力不足"和"工作量不够"的核心问题：

| # | 升级方向 | 解决的问题 | 预估工时 |
|---|---------|-----------|---------|
| 1 | **LangGraph 工作流编排** | 单 Agent ReAct 自由循环→结构化 DAG 工作流，定义 5 个测试场景模板 | 3-5 天 |
| 2 | **自研 Web 前端替换 ChatGPT-Next-Web** | 消除"借用前端"问题，实现 Perfa 专属 UI | 3-4 天 |
| 3 | **OpenTelemetry 可观测性 + AI 故障分析** | 系统运行状态不可见→全链路遥测，任务失败→AI 自动诊断 | 2-3 天 |

**总计: 8-12 天**

---

## 二、LangGraph 工作流编排

### 2.1 现状问题

当前 `react_agent.py` 的核心逻辑：

```python
while iteration < self.max_iterations:
    thought = await self._think(query, tool_calls, context)
    if thought.get("is_final"): break
    tool_result = await self._act(tool_name, tool_args)
```

问题：
- 自由循环，没有预定义的业务阶段
- 每次都靠 LLM 决策下一步，效率低、易跑偏
- 无法表达"先检查环境→再装工具→再跑测试→再出报告"的结构化流程
- 同一个 Agent 既做规划又做执行，职责混乱

### 2.2 目标架构

引入 LangGraph，将 Agent 从单一 ReAct 循环重构为 **结构化状态机 + 场景模板**：

```
用户输入 → 场景路由器（LLM 意图识别）
              │
              ├── 快速测试场景 (quick_test)
              ├── 全面性能评估场景 (full_assessment)
              ├── CPU 专项场景 (cpu_focus)
              ├── 存储专项场景 (storage_focus)
              ├── 网络专项场景 (network_focus)
              └── 自由对话场景 (free_chat) → 走原 ReAct 循环
```

每个场景是一个 LangGraph `StateGraph`，定义明确的节点和边：

#### 场景 1: `quick_test` — 快速测试

```
[环境检查] → [选择服务器] → [执行单一测试] → [获取结果] → [生成摘要]
```
- 适用: "帮我测一下这台服务器的 CPU"
- 固定 5 步，无分支

#### 场景 2: `full_assessment` — 全面性能评估

```
[环境检查] → [选择服务器] → [检查工具] → [安装缺失工具]
     → [并行: CPU测试 + 内存测试] → [磁盘IO测试] → [网络测试]
     → [收集所有结果] → [生成综合报告]
```
- 适用: "全面评估这台服务器的性能"
- 包含并行执行、条件分支（工具未安装则安装）

#### 场景 3: `cpu_focus` — CPU 专项评估

```
[环境检查] → [选择服务器] → [检查工具] → [UnixBench测试]
     → [SuperPI测试] → [收集结果] → [CPU专项报告]
```
- 适用: "详细测试 CPU 性能"

#### 场景 4: `storage_focus` — 存储专项评估

```
[环境检查] → [选择服务器] → [检查工具] → [FIO 随机读测试]
     → [FIO 顺序写测试] → [MLC 内存延迟测试] → [收集结果] → [存储专项报告]
```
- 适用: "测试磁盘和内存性能"

#### 场景 5: `network_focus` — 网络专项评估

```
[环境检查] → [选择服务器] → [检查工具] → [hping3 延迟测试]
     → [hping3 丢包测试] → [收集结果] → [网络专项报告]
```
- 适用: "测试网络性能"

### 2.3 核心数据结构

#### WorkflowState (LangGraph 状态)

```python
from typing import TypedDict, Annotated, List, Dict, Any, Optional
from langgraph.graph.message import add_messages

class WorkflowState(TypedDict):
    # 输入
    query: str                        # 原始用户查询
    session_id: str                   # 会话 ID
    scenario: str                     # 场景名称 (quick_test/full_assessment/...)
    
    # 执行上下文
    server_id: Optional[str]          # 目标服务器 ID
    server_ip: Optional[str]          # 目标服务器 IP
    agent_id: Optional[str]           # Agent ID
    agent_status: Optional[str]       # Agent 运行状态
    available_tools: List[str]        # 已安装的工具列表
    missing_tools: List[str]          # 需要安装的工具
    
    # 任务追踪
    task_ids: Dict[str, str]          # {test_name: task_id}
    results: Dict[str, Any]           # {test_name: result_data}
    errors: List[Dict[str, Any]]      # 错误列表
    
    # 输出
    messages: Annotated[list, add_messages]  # LangGraph 消息历史
    final_report: Optional[str]       # 最终报告
    status: str                       # workflow 状态: running/completed/failed
```

### 2.4 新增文件结构

```
src/langchain_agent/
├── workflows/                    # 新增目录
│   ├── __init__.py
│   ├── state.py                  # WorkflowState 定义
│   ├── router.py                 # 场景路由器（LLM 意图识别→场景选择）
│   ├── nodes.py                  # 通用节点函数（环境检查、服务器选择、结果收集等）
│   ├── scenarios/                # 场景模板目录
│   │   ├── __init__.py
│   │   ├── quick_test.py         # 快速测试场景
│   │   ├── full_assessment.py    # 全面评估场景
│   │   ├── cpu_focus.py          # CPU 专项场景
│   │   ├── storage_focus.py      # 存储专项场景
│   │   └── network_focus.py      # 网络专项场景
│   └── graph_builder.py          # LangGraph 构建器（注册所有场景图）
├── agents/
│   ├── react_agent.py            # 保留，用于 free_chat 场景
│   └── ...
```

### 2.5 场景路由器设计

```python
# workflows/router.py

SCENARIO_PROMPT = """根据用户查询，判断属于哪个测试场景：

- quick_test: 单项快速测试，如"测一下CPU"、"跑个fio"
- full_assessment: 全面性能评估，如"全面评估"、"完整测试"
- cpu_focus: CPU 深度测试，如"详细CPU测试"、"CPU性能分析"
- storage_focus: 存储/内存测试，如"磁盘性能"、"内存带宽"
- network_focus: 网络测试，如"网络延迟"、"网络质量"
- free_chat: 闲聊或非测试请求

用户查询: {query}

以 JSON 返回: {{"scenario": "...", "confidence": 0.0-1.0, "reason": "..."}}
"""
```

置信度 < 0.7 时走 `free_chat`（原 ReAct 循环）。

### 2.6 通用节点设计

| 节点名 | 功能 | 输入 | 输出 |
|-------|------|------|------|
| `check_environment` | 检查 MCP Server 连接、Agent 状态 | query | agent_status, available_tools |
| `select_server` | 从 list_servers 选择目标服务器 | query | server_id, server_ip, agent_id |
| `check_tools` | 检查所需工具是否已安装 | available_tools, required_tools | missing_tools |
| `install_tools` | 安装缺失工具 | missing_tools | available_tools (更新) |
| `run_benchmark` | 执行压测 | server_id, test_name, params | task_id |
| `wait_result` | 等待测试完成并获取结果 | task_id | result_data |
| `collect_results` | 收集所有测试结果 | results | formatted_results |
| `generate_report` | 生成分析报告 | results, scenario | final_report |
| `handle_error` | 错误处理节点 | errors | error_report |

### 2.7 full_assessment 场景详细图

```python
from langgraph.graph import StateGraph, END

def build_full_assessment_graph():
    graph = StateGraph(WorkflowState)
    
    # 添加节点
    graph.add_node("check_environment", check_environment)
    graph.add_node("select_server", select_server)
    graph.add_node("check_tools", check_tools)
    graph.add_node("install_tools", install_tools)
    graph.add_node("cpu_test", lambda s: run_benchmark(s, "unixbench"))
    graph.add_node("memory_test", lambda s: run_benchmark(s, "stream"))
    graph.add_node("disk_test", lambda s: run_benchmark(s, "fio"))
    graph.add_node("network_test", lambda s: run_benchmark(s, "hping3"))
    graph.add_node("collect_all", collect_results)
    graph.add_node("generate_report", generate_report)
    
    # 定义边
    graph.set_entry_point("check_environment")
    graph.add_edge("check_environment", "select_server")
    graph.add_edge("select_server", "check_tools")
    graph.add_conditional_edges("check_tools", route_after_tool_check,
        {"install": "install_tools", "proceed": "cpu_test"})
    graph.add_edge("install_tools", "cpu_test")
    
    # 并行: CPU + 内存同时执行
    # LangGraph 通过 fan-out/fan-in 实现并行
    graph.add_edge("cpu_test", "disk_test")
    graph.add_edge("memory_test", "disk_test")  # fan-in
    
    graph.add_edge("disk_test", "network_test")
    graph.add_edge("network_test", "collect_all")
    graph.add_edge("collect_all", "generate_report")
    graph.add_edge("generate_report", END)
    
    return graph.compile()
```

### 2.8 与现有代码的集成

修改 `orchestrator.py` 的 `process_query` 方法：

```python
async def process_query(self, query, session_id=None, mode="auto"):
    if mode == "auto":
        # 1. 场景路由
        scenario = await self.workflow_router.route(query)
        
        if scenario.name == "free_chat":
            # 走原 ReAct 循环
            return await self.agent.run(query, session_id=session_id, ...)
        else:
            # 走 LangGraph 工作流
            result = await self.workflow_engine.run(scenario.name, query, session_id)
            return result
    else:
        # 兼容原有 react 模式
        return await self.agent.run(query, session_id=session_id, ...)
```

### 2.9 依赖新增

```
langgraph>=0.2.0
```

---

## 三、自研 Web 前端替换 ChatGPT-Next-Web

### 3.1 现状问题

- 当前使用 `yidadaa/chatgpt-next-web` Docker 镜像作为前端
- 这是第三方开源项目，不是自己开发的工作
- 界面是通用 ChatGPT 风格，不体现 Perfa 的服务器性能测试专业特性
- 毕设答辩时"前端是别人的"是个明显减分项

### 3.2 目标

开发 Perfa 专属 Web 前端，替换 ChatGPT-Next-Web，具备：

1. **对话交互** — 与 Agent 后端通信（复用 OpenAI 兼容 API）
2. **测试场景可视化** — 展示工作流执行进度（LangGraph 节点状态）
3. **服务器管理面板** — 展示已注册服务器列表、Agent 状态
4. **测试报告展示** — 结构化展示性能测试结果（图表+表格）

### 3.3 技术选型

| 层 | 技术 | 理由 |
|----|------|------|
| 框架 | **Next.js 14** (App Router) | React 生态主流，SSR 支持好 |
| UI 库 | **Ant Design 5** | 中文友好，表格/图表组件丰富 |
| 图表 | **ECharts** (via echarts-for-react) | 性能数据可视化首选 |
| 状态 | **Zustand** | 轻量，适合中小项目 |
| 请求 | **fetch** + EventSource | SSE 流式输出 + 常规 API |
| 样式 | **Tailwind CSS** | 快速开发 |

### 3.4 页面设计

#### 3.4.1 整体布局

```
┌──────────────────────────────────────────────────┐
│  Perfa Logo  │  对话  │  服务器  │  报告  │  设置  │
├──────────┬───────────────────────────────────────┤
│          │                                       │
│  会话    │        主内容区                        │
│  列表    │                                       │
│          │                                       │
│  (侧边)  │                                       │
│          │                                       │
├──────────┴───────────────────────────────────────┤
│  输入框: [输入测试指令...]              [发送]     │
└──────────────────────────────────────────────────┘
```

#### 3.4.2 对话页面

- 左侧: 会话历史列表
- 右侧: 对话主区域
  - 用户消息气泡
  - Agent 回复（支持 Markdown 渲染）
  - **工作流进度条**: 显示当前场景的节点执行进度
    ```
    [✅环境检查] → [✅选择服务器] → [🔄执行CPU测试] → [⬜内存测试] → [⬜报告]
    ```
  - **测试结果卡片**: 结构化展示测试结果（非纯文本）
    ```
    ┌─ UnixBench 结果 ────────────────┐
    │ 单核分数: 1523    多核分数: 8432  │
    │ 并行效率: 69.2%                  │
    │ [📊 查看详细图表]                │
    └──────────────────────────────────┘
    ```
  - 性能统计（耗时、工具调用次数）
- 输入区: 支持文本输入，提供场景快捷按钮
  - `[🚀 快速测试]` `[📊 全面评估]` `[💾 存储测试]` `[🌐 网络测试]`

#### 3.4.3 服务器管理页面

- 服务器列表表格（IP、别名、Agent 状态、标签）
- 服务器详情（硬件信息、监控指标摘要）
- Agent 部署操作按钮

#### 3.4.4 报告页面

- 历史测试报告列表
- 报告详情（ECharts 图表 + 结构化数据）
- 多次测试对比视图

### 3.5 后端 API 扩展

在现有 OpenAI 兼容 API 基础上，新增以下端点：

```
GET  /v1/servers                    # 获取服务器列表
GET  /v1/servers/{id}               # 获取服务器详情
POST /v1/servers                    # 注册服务器
GET  /v1/workflows/status/{sid}     # 获取工作流执行状态（供前端轮询/SSE）
GET  /v1/reports                    # 获取报告列表
GET  /v1/reports/{id}               # 获取报告详情
GET  /v1/monitoring/metrics         # 获取监控指标摘要
```

### 3.6 文件结构

```
webui/
├── package.json
├── next.config.js
├── tailwind.config.js
├── tsconfig.json
├── public/
│   └── perfa-logo.svg
├── src/
│   ├── app/
│   │   ├── layout.tsx              # 全局布局
│   │   ├── page.tsx                # 对话页（首页）
│   │   ├── servers/
│   │   │   └── page.tsx            # 服务器管理
│   │   ├── reports/
│   │   │   └── page.tsx            # 报告列表
│   │   └── reports/[id]/
│   │       └── page.tsx            # 报告详情
│   ├── components/
│   │   ├── chat/
│   │   │   ├── ChatMessage.tsx     # 消息气泡
│   │   │   ├── ChatInput.tsx       # 输入框+快捷按钮
│   │   │   ├── WorkflowProgress.tsx # 工作流进度条
│   │   │   └── ResultCard.tsx      # 测试结果卡片
│   │   ├── servers/
│   │   │   ├── ServerTable.tsx     # 服务器列表表格
│   │   │   └── ServerDetail.tsx    # 服务器详情
│   │   └── reports/
│   │       ├── ReportList.tsx      # 报告列表
│   │       └── ReportChart.tsx     # ECharts 图表
│   ├── lib/
│   │   ├── api.ts                  # API 客户端
│   │   └── sse.ts                  # SSE 流式处理
│   └── store/
│       └── useChatStore.ts         # Zustand 状态
└── Dockerfile                      # 生产构建
```

### 3.7 部署方式

- 开发: `npm run dev` (端口 3001)
- 生产: `npm run build && npm start`，或 Docker
- 替换原 `docker-compose.yml` 中的 `yidadaa/chatgpt-next-web` 镜像

---

## 四、OpenTelemetry 可观测性 + AI 故障分析

### 4.1 现状问题

- 系统运行状态完全不可见：Agent 在做什么、工具调用耗时、哪个阶段卡住了——全部靠日志
- 任务失败时只返回一个 error 字符串，没有智能分析
- 毕设缺少"系统可观测性"这一重要工程维度

### 4.2 目标架构

```
┌─────────────────────────────────────────────────────────┐
│                    Perfa 系统组件                         │
│                                                          │
│  LangChain Agent ──┐                                    │
│  MCP Server    ────┤  OTel SDK (自动+手动 Instrument)   │
│  Node Agent    ────┤         │                          │
│                   ─┼─────────┼──→ OTel Collector        │
│                     │         │        │                 │
│                     │         │   ┌────┴────┐           │
│                     │         │   │         │           │
│                     │         │   ▼         ▼           │
│                     │    Jaeger    VictoriaMetrics       │
│                     │   (Traces)    (Metrics)           │
│                     │                                   │
│                     └──→ 失败事件 ──→ AI 故障分析器     │
│                                      │                  │
│                                      ▼                  │
│                                   故障报告              │
└─────────────────────────────────────────────────────────┘
```

### 4.3 Instrumentation 范围

#### 4.3.1 Traces（分布式追踪）

| 组件 | Span 名称 | 属性 |
|------|----------|------|
| LangChain Agent | `agent.query` | query, session_id, scenario |
| LangChain Agent | `agent.think` | iteration, model, tokens |
| LangChain Agent | `agent.act` | tool_name, tool_args |
| LangChain Agent | `workflow.node` | node_name, scenario, status |
| MCP Server | `mcp.tool.execute` | tool_name, server_id |
| MCP Server | `mcp.sse.connect` | client_id |
| Node Agent | `benchmark.execute` | test_name, task_id |
| Node Agent | `benchmark.prepare` | test_name |
| Node Agent | `benchmark.run` | test_name, exit_code |

#### 4.3.2 Metrics（指标）

| 指标名 | 类型 | 标签 | 说明 |
|--------|------|------|------|
| `perfa_agent_queries_total` | Counter | scenario, status | 查询总数 |
| `perfa_agent_query_duration_seconds` | Histogram | scenario | 查询耗时 |
| `perfa_tool_calls_total` | Counter | tool_name, status | 工具调用数 |
| `perfa_tool_call_duration_seconds` | Histogram | tool_name | 工具调用耗时 |
| `perfa_llm_tokens_total` | Counter | model, type(prompt/completion) | Token 用量 |
| `perfa_benchmark_tasks_total` | Counter | test_name, status | 压测任务数 |
| `perfa_benchmark_duration_seconds` | Histogram | test_name | 压测耗时 |
| `perfa_workflow_nodes_total` | Counter | scenario, node, status | 工作流节点执行数 |

#### 4.3.3 Logs（结构化日志）

通过 OTel Logs Bridge 将现有 Python logging 输出接入 OTel Collector。

### 4.4 技术选型

| 组件 | 技术 | 版本 | 说明 |
|------|------|------|------|
| OTel SDK | `opentelemetry-sdk` + `opentelemetry-instrumentation` | ≥1.20 | Python SDK |
| 自动 Instrument | `opentelemetry-instrumentation-auto-instrumentation` | ≥0.40b0 | 自动注入 |
| HTTP Instrument | `opentelemetry-instrumentation-fastapi` / `flask` | ≥0.40b0 | 框架自动注入 |
| OTel Collector | `otel/opentelemetry-collector-contrib` | latest | 统一收集 |
| Trace 后端 | **Jaeger** | latest | 链路追踪 UI |
| Metrics 后端 | **VictoriaMetrics** (已有) | existing | 复用现有 VM |

### 4.5 OTel Collector 配置

```yaml
# deploy/otel-collector-config.yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:
    timeout: 5s
    send_batch_size: 1024

exporters:
  jaeger:
    endpoint: jaeger:14250
    tls:
      insecure: true
  prometheusremotewrite:
    endpoint: http://victoriametrics:8428/api/v1/write
  file:
    path: /tmp/perfa-otel-logs.json

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch]
      exporters: [jaeger]
    metrics:
      receivers: [otlp]
      processors: [batch]
      exporters: [prometheusremotewrite]
    logs:
      receivers: [otlp]
      processors: [batch]
      exporters: [file]
```

### 4.6 Instrumentation 代码注入方式

#### 方式一：Agent 侧（LangChain Agent）

在 `react_agent.py` 和 `workflows/nodes.py` 中手动埋点：

```python
from opentelemetry import trace, metrics

tracer = trace.get_tracer("perfa.agent")
meter = metrics.get_meter("perfa.agent")

query_counter = meter.create_counter("perfa_agent_queries_total")
tool_duration = meter.create_histogram("perfa_tool_call_duration_seconds")

# 在 _think 方法中
with tracer.start_as_current_span("agent.think") as span:
    span.set_attribute("iteration", iteration)
    thought, content = await self._think(query, tool_calls, context)
    span.set_attribute("is_final", thought.get("is_final", False))
```

#### 方式二：MCP Server 侧

在 `server.py` 启动时自动 Instrument：

```python
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.starlette import StarletteInstrumentor

# 在 Starlette app 创建后
StarletteInstrumentor().instrument_app(app)
```

#### 方式三：Node Agent 侧

在 `main.py` 启动时注入 Flask Instrument + 手动 Span：

```python
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor

FlaskInstrumentor().instrument_app(self.api_server.app)
RequestsInstrumentor().instrument()
```

### 4.7 AI 故障分析器

当任务失败时，自动收集相关遥测数据，交给 LLM 进行智能分析。

#### 触发条件

```python
# 在 BenchmarkExecutor._execute_task 的 except 分支中
if task.status == TaskStatus.FAILED:
    await self.failure_analyzer.analyze(task, trace_context)
```

#### 故障分析流程

```
1. 任务失败 → 收集遥测数据
   ├── Trace: 该任务的完整调用链
   ├── Metrics: 执行期间的系统指标
   ├── Logs: 相关日志条目
   └── Context: 任务参数、服务器信息

2. 构造分析 Prompt
   """
   以下是一次性能测试任务失败的信息：
   
   任务: {test_name} ({task_id})
   服务器: {server_ip}
   错误信息: {error}
   
   调用链追踪:
   {trace_summary}
   
   执行期间指标:
   CPU: {cpu_metrics}
   内存: {mem_metrics}
   
   日志:
   {relevant_logs}
   
   请分析失败原因，给出：
   1. 根因分析
   2. 可能的解决步骤
   3. 是否需要人工介入
   """

3. 调用 LLM → 生成结构化故障报告

4. 存储故障报告 → 推送到前端展示
```

#### 故障报告结构

```python
class FailureReport(TypedDict):
    task_id: str
    test_name: str
    server_id: str
    error_original: str           # 原始错误
    root_cause: str               # AI 分析的根因
    severity: str                 # low/medium/high/critical
    suggested_fixes: List[str]    # 建议修复步骤
    needs_human: bool             # 是否需要人工介入
    trace_summary: str            # 追踪摘要
    metrics_snapshot: Dict        # 指标快照
    analyzed_at: str              # 分析时间
```

#### 新增文件

```
src/langchain_agent/
├── observability/                # 新增目录
│   ├── __init__.py
│   ├── tracer.py                 # OTel Tracer 配置
│   ├── metrics.py                # OTel Metrics 配置
│   ├── instrument_agent.py       # Agent 侧 Instrumentation
│   ├── instrument_server.py      # MCP Server 侧 Instrumentation
│   └── failure_analyzer.py       # AI 故障分析器
```

### 4.8 前端集成

在自研 Web 前端中新增 **可观测性面板**：

- 链路追踪: 嵌入 Jaeger UI (iframe) 或通过 Jaeger API 查询展示
- 指标看板: 嵌入 Grafana (iframe) 展示 Perfa 自定义 Dashboard
- 故障报告: 在对话中作为特殊消息类型展示

---

## 五、部署架构更新

### 5.1 Docker Compose 更新

```yaml
# deploy/docker-compose.yml (更新后)
services:
  # === 原有服务 ===
  mcp-server:
    build: ../src/mcp_server
    ports: ["9000:9000"]
    environment:
      - OTEL_EXPORTER_OTLP_ENDPOINT=otel-collector:4317
      - OTEL_SERVICE_NAME=perfa-mcp-server

  langchain-agent:
    build: ../src/langchain_agent
    ports: ["10000:10000"]
    environment:
      - OTEL_EXPORTER_OTLP_ENDPOINT=otel-collector:4317
      - OTEL_SERVICE_NAME=perfa-agent

  # === 新增服务 ===
  perfa-web:                      # 替换 chatgpt-next-web
    build: ../webui
    ports: ["3001:3000"]
    environment:
      - NEXT_PUBLIC_API_URL=http://langchain-agent:10000

  otel-collector:                 # OTel Collector
    image: otel/opentelemetry-collector-contrib:latest
    ports:
      - "4317:4317"   # gRPC
      - "4318:4318"   # HTTP
    volumes:
      - ./otel-collector-config.yaml:/etc/otelcol-contrib/config.yaml

  jaeger:                         # 链路追踪
    image: jaegertracing/all-in-one:latest
    ports:
      - "16686:16686"  # UI
      - "14250:14250"  # gRPC (from collector)

  victoriametrics:                # 已有，新增 OTel 写入
    image: victoriametrics/victoria-metrics:latest
    ports: ["8428:8428"]
```

### 5.2 端口规划（更新）

| 服务 | 端口 | 说明 |
|------|------|------|
| Perfa Web (前端) | 3001 | 自研前端 |
| LangChain Agent API | 10000 | OpenAI 兼容 API + 扩展 API |
| MCP Server | 9000 | SSE 端点 |
| Node Agent | 8080 | 被测节点 API |
| OTel Collector | 4317/4318 | OTLP 接收 |
| Jaeger UI | 16686 | 链路追踪 |
| VictoriaMetrics | 8428 | 指标存储 |
| Grafana | 3000 | 监控看板 |

---

## 六、实施计划

### Phase 1: LangGraph 工作流 (Day 1-5)

| 天 | 任务 | 产出 |
|----|------|------|
| D1 | 定义 WorkflowState，实现通用节点(nodes.py)，实现路由器(router.py) | 工作流基础设施 |
| D2 | 实现 quick_test + cpu_focus 场景 | 2 个场景可用 |
| D3 | 实现 full_assessment 场景（含并行） | 核心场景可用 |
| D4 | 实现 storage_focus + network_focus 场景 | 5 个场景全部完成 |
| D5 | 集成到 orchestrator.py，端到端测试 | 工作流上线 |

### Phase 2: 自研 Web 前端 (Day 4-8，与 Phase 1 部分并行)

| 天 | 任务 | 产出 |
|----|------|------|
| D4 | 项目初始化(Next.js+AntD+Tailwind)，实现布局和对话页面 | 基础对话可用 |
| D5 | 实现 SSE 流式输出、Markdown 渲染、工作流进度条 | 对话体验完整 |
| D6 | 实现服务器管理页面、后端扩展 API | 服务器管理可用 |
| D7 | 实现报告页面（ECharts 图表） | 报告展示可用 |
| D8 | 美化 UI、Docker 构建、替换 docker-compose | 前端上线 |

### Phase 3: OTel 可观测性 + AI 故障分析 (Day 7-12，与 Phase 2 部分并行)

| 天 | 任务 | 产出 |
|----|------|------|
| D7 | OTel SDK 配置，Agent 侧 Tracer/Metrics 注入 | Agent 可观测 |
| D8 | MCP Server + Node Agent 侧 Instrumentation | 全链路追踪 |
| D9 | OTel Collector 部署，Jaeger + VictoriaMetrics 集成 | 追踪/指标 UI 可用 |
| D10 | 实现 FailureAnalyzer，集成到 BenchmarkExecutor | AI 故障分析可用 |
| D11 | 前端可观测性面板（Jaeger/Grafana 嵌入） | 统一 UI |
| D12 | 端到端集成测试、修复、文档更新 | 全部完成 |

---

## 七、论文可写内容映射

| 升级项 | 论文章节 | 可写内容 |
|--------|---------|---------|
| LangGraph 工作流 | 第X章 系统设计 | ReAct vs 结构化工作流对比、5种场景模板设计、DAG并行执行 |
| LangGraph 工作流 | 第X章 实验评估 | 场景模板执行成功率 vs 自由ReAct、任务完成时间对比、步骤数对比 |
| 自研Web前端 | 第X章 系统实现 | 前端架构设计、工作流可视化、SSE流式交互 |
| OTel可观测性 | 第X章 系统设计 | 分布式追踪设计、指标体系、AI故障分析架构 |
| OTel可观测性 | 第X章 实验评估 | 链路追踪开销(<5%)、故障分析准确率、MTTR(平均恢复时间)降低 |

---

## 八、风险与应对

| 风险 | 概率 | 应对 |
|------|------|------|
| LangGraph 并行执行与现有串行 MCP 调用冲突 | 中 | full_assessment 场景中 CPU+内存测试可串行 fallback，不强制并行 |
| OTel SDK 对现有代码侵入性大 | 低 | 优先使用自动 Instrumentation，手动埋点仅限关键路径 |
| 自研前端开发时间超预期 | 中 | 优先保证对话页+工作流进度条，服务器/报告页可简化 |
| Jaeger/VM 部署资源占用 | 低 | Jaeger all-in-one 内存 < 500MB，VM 已在用 |

---

**审批确认:**

- [ ] 我已阅读上述规格说明
- [ ] 同意按此方案实施
- [ ] 需要修改（请注明）: _______________
