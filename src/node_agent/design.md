# 守护进程 agent 的设计

## 守护进程 agent 的功能

1. monitor - 采集cpu、内存、磁盘等系统资源使用情况
2. tool - 管理对应的压力测试工具
3. benchmark - 管理对应的压力测试任务
4. api - 提供和mcp交互的接口

## 守护进程 agent 的架构

```
Agent
├── Main Thread              # 主线程
│   └── HTTP API Server     # 接收MCP Server指令
│
├── Monitoring Thread        # 监控线程（独立运行）
│   └── InfluxDB Writer     # 直写监控数据
│
├── Task Execution Thread    # 任务执行线程
│   └── SQLite Writer       # 写入任务结果
│
└── Log Pusher Thread        # 日志推送线程
    └── WebSocket Client    # 推送到MCP Server
```

## 数据流向

```
采集器 → InfluxDB (直写，不走MCP)
任务结果 → SQLite (直写)
日志 → MCP Server (WebSocket推送)
状态 → MCP Server (HTTP上报)
```

## API 路由设计

| 路由 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/api/run_benchmark` | POST | 执行压测任务 |
| `/api/cancel_task` | POST | 取消任务 |
| `/api/pause_task` | POST | 暂停任务 |
| `/api/resume_task` | POST | 恢复任务 |
| `/api/task_status/<task_id>` | GET | 查询任务状态 |
| `/api/start_monitoring` | POST | 启动监控 |
| `/api/stop_monitoring` | POST | 停止监控 |

## monitor 的实现

在monitor文件夹下，实现cpu、内存、磁盘等系统资源的采集，当前阶段只需要打log
启动main.py, 就可以把monitor的功能注册进去

## tool 的实现

在tool文件夹下，实现压力测试工具的生命周期管理功能。

支持的工具：unixbench, superpi, stream, mlc, fio, hping3

详细设计见 `doc/tool-api-design.md`

## benchmark 的实现（待开发）

### TaskExecutor 核心功能

- `run_benchmark(test_name, params)` - 执行压测
- `cancel_task(task_id)` - 取消任务
- `pause_task(task_id)` - 暂停任务 (SIGSTOP)
- `resume_task(task_id)` - 恢复任务 (SIGCONT)
- `get_task_status(task_id)` - 查询状态

### 任务状态

```python
class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
```