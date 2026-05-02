# Node Agent: 接口清单与调用链

## 入口文件

- `src/node_agent/main.py`
- `src/node_agent/api/server.py`
- `src/node_agent/api/routes/`

## HTTP 接口清单

### 健康与状态

| 路径 | 方法 | 作用 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/api/status` | GET | Agent 状态、监控状态、当前任务 |

### 监控与系统信息

| 路径 | 方法 | 作用 |
|------|------|------|
| `/api/monitor/start` | POST | 启动监控 |
| `/api/monitor/stop` | POST | 停止监控 |
| `/api/monitor/status` | GET | 监控状态 |
| `/api/system/info` | GET | 系统静态信息 |
| `/api/system/status` | GET | 实时资源状态 |
| `/api/storage/usage` | GET | 存储占用 |
| `/api/storage/cleanup` | POST | 清理日志、工作目录、旧结果 |
| `/api/storage/logs` | GET | 日志文件列表 |
| `/api/storage/logs/<log_name>` | GET | 读取日志内容 |
| `/api/config` | GET / POST | 查询或更新 Agent 配置 |

### 工具管理

| 路径 | 方法 | 作用 |
|------|------|------|
| `/api/tools` | GET | 列出工具 |
| `/api/tools/<tool_name>` | GET | 查询工具状态 |
| `/api/tools/<tool_name>/install` | POST | 安装工具 |
| `/api/tools/<tool_name>/uninstall` | POST | 卸载工具 |

### Benchmark

| 路径 | 方法 | 作用 |
|------|------|------|
| `/api/benchmark/run` | POST | 启动压测 |
| `/api/benchmark/cancel` | POST | 取消任务 |
| `/api/benchmark/pause` | POST | 暂停任务 |
| `/api/benchmark/resume` | POST | 恢复任务 |
| `/api/benchmark/current` | GET | 当前任务 |
| `/api/benchmark/tasks` | GET | 历史任务列表 |
| `/api/benchmark/tasks/<task_id>` | GET | 单任务状态 |
| `/api/benchmark/results` | GET | 结果列表 |
| `/api/benchmark/results/<task_id>` | GET | 单任务结果 |
| `/api/benchmark/logs/<task_id>` | GET | 日志路径 |

## 请求调用链

### 启动链路

```text
main.py
  -> NodeAgent.start()
  -> ToolManager
  -> BenchmarkExecutor
  -> start_http_server(:8000)
  -> Monitor.start()
  -> APIServer.run_background(:8080)
```

### 压测执行链路

```text
POST /api/benchmark/run
  -> benchmark.py: run_benchmark()
  -> agent.benchmark_executor.run_benchmark()
  -> runner 执行真实工具
  -> 结果写入 result_collector / 日志文件
```

### 日志查询链路

```text
GET /api/storage/logs/<log_name>
  -> monitor.py: get_log_content()
  -> 校验文件名，防路径遍历
  -> 读取最后 N 行
  -> HTML 转义后返回
```

### 工具安装链路

```text
POST /api/tools/<name>/install
  -> tool.py: install_tool()
  -> ToolManager.install_tool()
  -> 对应 *_tools.py 实现
```

## 关键约束

- Benchmark 运行期间禁止安装和卸载工具，`tool.py` 中有显式拦截。
- 同一时刻只能跑一个压测任务，`benchmark.py` 会先检查 `executor.is_busy()`。
- 日志读取接口只允许 `.log` 文件，并显式阻断 `..` 和 `/`。
- `/api/config` 当前可动态调整监控间隔、监控指标和最大并发任务数。

## 关键文件索引

| 文件 | 作用 |
|------|------|
| `src/node_agent/main.py` | 总启动入口 |
| `src/node_agent/api/server.py` | Flask App 组装与蓝图注册 |
| `src/node_agent/api/routes/health.py` | 健康与 Agent 状态 |
| `src/node_agent/api/routes/monitor.py` | 监控、系统信息、存储 |
| `src/node_agent/api/routes/tool.py` | 工具管理接口 |
| `src/node_agent/api/routes/benchmark.py` | 压测任务接口 |
| `src/node_agent/benchmark/executor.py` | 压测调度核心 |
| `src/node_agent/benchmark/runners/` | 各工具 Runner |
| `src/node_agent/tool/manager.py` | 工具生命周期管理 |
| `src/node_agent/monitor/monitor.py` | 监控线程管理 |

## 改动建议

如果你要改：

- 接口行为，先看 `api/routes/`
- 执行策略，先看 `benchmark/executor.py`
- 新增工具，先看 `tool/` 和 `benchmark/runners/`
