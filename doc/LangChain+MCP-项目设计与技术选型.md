# LangChain + MCP 项目设计与技术选型（简版）

## 1. 项目目标
做一个“对话式服务器性能测试工具”：用户在 AI IDE 里一句话发起测试，系统自动完成连接服务器、安装依赖、执行 CPU/内存/磁盘测试、生成选型建议。

## 2. 最小可用架构
```text
AI IDE
  ↓ (MCP)
MCP Server（Python）
  ↓
LangChain Agent（工具编排）
  ↓
SSH 执行器
  ↓
目标服务器（sysbench/fio/dd）
```

## 3. 技术选型（优先“简单可落地”）
- 语言：`Python 3.11+`
- LLM 编排：`LangChain`
- MCP：`FastMCP`（快速定义工具）
- 远程执行：`paramiko`
- 持久化：`SQLite`（后期可换 PostgreSQL）
- API（可选）：`FastAPI`
- 可视化（可选）：`Streamlit` 或 `Vue + ECharts`

## 4. 核心模块
1. `connect_server`：SSH 连接管理（支持密码/密钥）
2. `ensure_dependencies`：检测并安装 `sysbench/fio`（无权限则降级 `dd + /proc`）
3. `benchmark_cpu`
4. `benchmark_memory`
5. `benchmark_disk`
6. `benchmark_all`：一键全量测试
7. `compare_servers`：基于历史数据给选型建议

## 5. MCP 接口（最小集）
- `connect_server(host, username, auth, alias)`
- `benchmark_cpu(server, duration=30, threads=0)`
- `benchmark_memory(server, size="1G")`
- `benchmark_disk(server, mode="all", size="1G")`
- `benchmark_all(server)`
- `get_history(server)`
- `compare_servers(server_a, server_b)`

## 6. 数据库最小表设计
- `servers(id, alias, host, username, created_at)`
- `results(id, server_alias, type, metrics_json, created_at)`

## 7. 开发顺序（建议）
1. 先打通 SSH 连接 + 单项 CPU 测试
2. 再补内存/磁盘 + 自动安装
3. 接入 SQLite 历史记录
4. 最后接 LangChain Agent 和 `benchmark_all` 自动流程

## 8. 毕设可展示亮点
- 自然语言触发测试（LangChain）
- 标准化工具调用（MCP）
- 自动依赖处理与降级策略
- 多机历史对比与选型结论
