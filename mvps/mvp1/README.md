# MVP1（LangChain + MCP + SQLite）

## 目标
通过 LangChain 调 MCP 工具，支持多服务器注册与持久化，并在目标机执行：`sysbench cpu --threads=1 run`。

## 为什么选 SQLite（关系型）
- 本任务是结构化数据（服务器、测试记录、时间维度），关系型更合适。
- SQLite 足够轻量，零额外安装（Python 内置 `sqlite3`）。
- 后续可平滑迁移 PostgreSQL，不影响表结构思路。

## 当前实现
- `mcp_server.py` 提供工具：
  - `register_server(...)`
  - `list_registered_servers()`
  - `check_connection(server_alias)`
  - `benchmark_cpu(server_alias, threads=1, save_result=True)`
  - `get_cpu_benchmark_history(server_alias, limit=10)`
- `perfa_mvp1/db.py`：SQLite 持久化（`perfa.db`）
- `langchain_agent.py`：LangChain 通过 MCP 调用上述工具

## 使用
1. 安装依赖
```bash
pip install -r requirements.txt
```

2. 配置环境变量（参考 `.env.example`）
- `DEEPSEEK_API_KEY`
- `DEEPSEEK_BASE_URL`（可选，默认 `https://api.deepseek.com`）
- `PERFA_DB_PATH`（可选）


3. 启动 MCP Server（终端1）
```bash
python mcp_server.py
```

4. 运行 LangChain Agent（终端2）
```bash
python langchain_agent.py
```

## 直接用 MCP 的建议流程
1. `register_server(alias, host, username, password/key_file, ...)`
2. `check_connection(server_alias)`
3. `benchmark_cpu(server_alias, threads=1)`
4. `get_cpu_benchmark_history(server_alias)`

## 备注
- 目标服务器需安装 `sysbench`。
- 这是 MVP1：先打通多服务器持久化 + CPU 单项测试链路。
