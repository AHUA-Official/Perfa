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

## 依赖管理

### Python 依赖

```txt
# requirements.txt
flask>=2.0.0           # HTTP API 服务
prometheus-client>=0.15.0  # 指标暴露
psutil>=5.9.0          # 系统监控
# 注：sqlite3 为 Python 内置，无需安装
```

### 安装依赖

```bash
pip install flask prometheus-client psutil
```

## api 的实现

### 技术选型

| 选项 | 优点 | 缺点 | 选择 |
|------|------|------|------|
| **Flask** ✅ | 轻量、成熟、易集成 | 功能相对简单 | ✅ 守护进程足够 |
| FastAPI | 异步、自动文档 | 需要 async 改造现有代码 | ❌ 过度设计 |
| http.server | Python 内置 | 功能简陋 | ❌ 不够实用 |

### API 模块结构

```
api/
├── __init__.py          # 模块导出
├── server.py            # APIServer - HTTP 服务器
├── routes/              # 路由模块
│   ├── __init__.py
│   ├── health.py        # 健康检查路由
│   ├── benchmark.py     # 压测相关路由
│   ├── tool.py          # 工具管理路由
│   └── monitor.py       # 监控相关路由
└── responses.py         # 统一响应格式
```

### 统一响应格式

```python
# 成功响应
{
    "success": true,
    "data": {...},
    "message": "操作成功"
}

# 错误响应
{
    "success": false,
    "error": {
        "code": "TASK_RUNNING",
        "message": "已有任务在运行",
        "details": {...}
    }
}
```

### 完整 API 路由设计

#### 1. 健康检查

```
GET /health
GET /api/status
```

**响应**:
```json
{
    "success": true,
    "data": {
        "agent_id": "node-agent-001",
        "uptime_seconds": 3600,
        "monitor_running": true,
        "current_task": null,
        "version": "1.0.0"
    }
}
```

#### 2. 监控相关

```
POST /api/monitor/start
POST /api/monitor/stop
GET  /api/monitor/status
```

**启动监控请求**:
```json
{
    "interval": 5,
    "enabled_metrics": ["cpu", "memory", "disk", "network"]
}
```

**监控状态响应**:
```json
{
    "success": true,
    "data": {
        "running": true,
        "interval": 5,
        "enabled_metrics": ["cpu", "memory", "disk", "network"],
        "last_collect_time": "2026-03-12T14:30:00"
    }
}
```

#### 3. 工具管理

```
GET    /api/tools                    # 列出所有工具
GET    /api/tools/<tool_name>        # 查询工具状态
POST   /api/tools/<tool_name>/install   # 安装工具
POST   /api/tools/<tool_name>/uninstall # 卸载工具
```

**工具列表响应**:
```json
{
    "success": true,
    "data": {
        "tools": [
            {
                "name": "stream",
                "category": "mem",
                "status": "installed",
                "binary_path": "/opt/benchmark/stream"
            },
            {
                "name": "unixbench",
                "category": "cpu",
                "status": "not_installed"
            }
        ],
        "count": 6
    }
}
```

#### 4. 压测任务

```
POST   /api/benchmark/run            # 执行压测
POST   /api/benchmark/cancel         # 取消任务
POST   /api/benchmark/pause          # 暂停任务
POST   /api/benchmark/resume         # 恢复任务
GET    /api/benchmark/current        # 当前任务
GET    /api/benchmark/tasks          # 任务列表
GET    /api/benchmark/tasks/<task_id> # 任务状态
GET    /api/benchmark/results/<task_id> # 获取结果
GET    /api/benchmark/results        # 结果列表
GET    /api/benchmark/logs/<task_id> # 获取日志
```

#### 5. 监控与系统信息

```
GET    /api/system/info              # 获取系统静态信息（hostname, os, cpu等）
GET    /api/system/status            # 获取系统当前状态（实时CPU、内存、磁盘、网络）
POST   /api/monitor/start            # 启动监控
POST   /api/monitor/stop             # 停止监控
GET    /api/monitor/status           # 监控状态
```

**系统信息响应**:
```json
{
    "success": true,
    "data": {
        "system": {
            "hostname": "node-001",
            "os": "Linux 5.15.0",
            "arch": "x86_64",
            "cpu_model": "Intel(R) Xeon(R) CPU E5-2680",
            "cpu_cores": "32",
            "memory_total_gb": "128.0",
            "kernel": "5.15.0-91-generic",
            "machine_id": "a1b2c3d4e5f6"
        },
        "labels": {
            "hostname": "node-001",
            "machine_id": "a1b2c3d4e5f6"
        }
    }
}
```

**系统状态响应（实时）**:
```json
{
    "success": true,
    "data": {
        "cpu": {
            "percent": 15.5,
            "count": 32,
            "freq_mhz": 2400.0
        },
        "memory": {
            "total_gb": 128.0,
            "available_gb": 64.5,
            "used_gb": 63.5,
            "percent": 49.6
        },
        "swap": {
            "total_gb": 8.0,
            "used_gb": 0.5,
            "percent": 6.25
        },
        "disk": {
            "total_gb": 500.0,
            "used_gb": 250.5,
            "free_gb": 249.5,
            "percent": 50.1
        },
        "network": {
            "bytes_sent": 12345678,
            "bytes_recv": 87654321,
            "connections": 45
        },
        "load_average": {
            "1min": 1.5,
            "5min": 2.0,
            "15min": 1.8
        },
        "uptime_seconds": 86400
    }
}
```

#### 6. 存储管理

```
GET    /api/storage/usage          # 获取存储使用情况（数据库、日志大小）
GET    /api/storage/logs            # 列出日志文件
POST   /api/storage/cleanup        # 清理存储空间
```

**存储使用情况响应**:
```json
{
    "success": true,
    "data": {
        "data_dir": "/var/lib/node_agent",
        "working_dir": "/tmp/benchmark_work",
        "database": {
            "path": "/var/lib/node_agent/benchmark_results.db",
            "size_mb": 2.5,
            "exists": true,
            "result_count": 15
        },
        "logs": {
            "path": "/var/lib/node_agent/logs",
            "count": 10,
            "total_size_mb": 5.2
        },
        "working_dir_files": {
            "path": "/tmp/benchmark_work",
            "count": 3,
            "total_size_mb": 0.5
        },
        "total_size_mb": 8.2
    }
}
```

**清理存储请求**:
```json
{
    "clean_logs": true,
    "keep_logs_days": 7,
    "clean_working_dir": true,
    "clean_old_results": false,
    "keep_results_days": 30
}
```

**清理存储响应**:
```json
{
    "success": true,
    "data": {
        "logs_deleted": 5,
        "logs_size_freed_mb": 2.5,
        "working_files_deleted": 3,
        "working_size_freed_mb": 0.5,
        "results_deleted": 0
    },
    "message": "存储清理完成"
}
```

**执行压测请求**:
```json
{
    "test_name": "stream",
    "params": {
        "array_size": 100000000,
        "ntimes": 10,
        "nt": 4
    }
}
```

**同步任务响应（stream）**:
```json
{
    "success": true,
    "data": {
        "task_id": "a1b2c3d4-...",
        "test_name": "stream",
        "status": "completed",
        "duration_seconds": 45.2,
        "result": {
            "copy_rate_mbs": 45000.5,
            "scale_rate_mbs": 42000.3,
            "add_rate_mbs": 48000.2,
            "triad_rate_mbs": 47000.1,
            "avg_rate_mbs": 45500.3
        },
        "log_file": "/var/lib/node_agent/logs/2026-03-12_143052_stream_a1b2c3.log"
    }
}
```

**异步任务响应（unixbench）**:
```json
{
    "success": true,
    "data": {
        "task_id": "d4e5f6g7-...",
        "test_name": "unixbench",
        "status": "running",
        "message": "任务已开始执行，请通过 task_id 查询状态"
    }
}
```

**任务状态响应**:
```json
{
    "success": true,
    "data": {
        "task_id": "d4e5f6g7-...",
        "test_name": "unixbench",
        "status": "running",
        "start_time": "2026-03-12T14:30:00",
        "elapsed_seconds": 1800,
        "progress": {
            "current_test": "Dhrystone",
            "tests_completed": 3,
            "tests_total": 10
        }
    }
}
```

### 错误码定义

| 错误码 | HTTP状态码 | 说明 |
|--------|-----------|------|
| `TASK_RUNNING` | 409 | 已有任务在运行 |
| `TOOL_NOT_INSTALLED` | 400 | 工具未安装 |
| `TOOL_INSTALL_FAILED` | 500 | 工具安装失败 |
| `TASK_NOT_FOUND` | 404 | 任务不存在 |
| `INVALID_PARAMS` | 400 | 参数无效 |
| `INTERNAL_ERROR` | 500 | 内部错误 |

### APIServer 核心实现

```python
class APIServer:
    """HTTP API 服务器"""
    
    def __init__(self, agent: NodeAgent, host: str = "0.0.0.0", port: int = 8080):
        self.agent = agent
        self.host = host
        self.port = port
        self.app = Flask(__name__)
        self._register_routes()
    
    def _register_routes(self):
        """注册所有路由"""
        # 健康检查
        self.app.route('/health', methods=['GET'])(self.health_check)
        self.app.route('/api/status', methods=['GET'])(self.get_status)
        
        # 监控
        self.app.route('/api/monitor/start', methods=['POST'])(self.start_monitoring)
        self.app.route('/api/monitor/stop', methods=['POST'])(self.stop_monitoring)
        self.app.route('/api/monitor/status', methods=['GET'])(self.monitor_status)
        
        # 工具
        self.app.route('/api/tools', methods=['GET'])(self.list_tools)
        self.app.route('/api/tools/<tool_name>', methods=['GET'])(self.get_tool)
        self.app.route('/api/tools/<tool_name>/install', methods=['POST'])(self.install_tool)
        self.app.route('/api/tools/<tool_name>/uninstall', methods=['POST'])(self.uninstall_tool)
        
        # 压测
        self.app.route('/api/benchmark/run', methods=['POST'])(self.run_benchmark)
        self.app.route('/api/benchmark/cancel', methods=['POST'])(self.cancel_benchmark)
        self.app.route('/api/benchmark/pause', methods=['POST'])(self.pause_benchmark)
        self.app.route('/api/benchmark/resume', methods=['POST'])(self.resume_benchmark)
        self.app.route('/api/benchmark/current', methods=['GET'])(self.get_current_task)
        self.app.route('/api/benchmark/tasks', methods=['GET'])(self.list_tasks)
        self.app.route('/api/benchmark/tasks/<task_id>', methods=['GET'])(self.get_task_status)
        self.app.route('/api/benchmark/results/<task_id>', methods=['GET'])(self.get_result)
        self.app.route('/api/benchmark/results', methods=['GET'])(self.list_results)
        self.app.route('/api/benchmark/logs/<task_id>', methods=['GET'])(self.get_log)
    
    def start(self):
        """启动 API 服务器（非阻塞）"""
        self.app.run(host=self.host, port=self.port, threaded=True)
    
    def start_background(self):
        """在后台线程启动"""
        thread = threading.Thread(target=self.start, daemon=True)
        thread.start()
```

### 与 MCP Server 的通信

#### 方式一：HTTP 回调（推荐）

```python
# 任务状态变化时回调 MCP Server
def on_task_status_change(task_id: str, status: str):
    requests.post(
        f"{MCP_SERVER_URL}/api/agent/callback",
        json={
            "agent_id": self.agent_id,
            "event": "task_status_change",
            "task_id": task_id,
            "status": status
        }
    )
```

#### 方式二：WebSocket 推送（可选）

```python
# 实时日志推送
def on_task_log(task_id: str, log_line: str):
    if self.ws_client:
        self.ws_client.send(json.dumps({
            "type": "log",
            "task_id": task_id,
            "content": log_line
        }))
```

### 配置项

```python
API_CONFIG = {
    # HTTP 服务
    "host": "0.0.0.0",
    "port": 8080,
    
    # MCP Server 配置
    "mcp_server_url": "http://mcp-server:9000",
    "callback_enabled": True,
    "websocket_enabled": False,
    
    # 安全配置
    "auth_enabled": False,
    "api_key": None,
}
```

### 启动流程

```
NodeAgent.start()
    │
    ├─► 1. 初始化 ToolManager
    │
    ├─► 2. 启动 Prometheus metrics (port 8000)
    │
    ├─► 3. 启动 Monitor (后台线程)
    │
    ├─► 4. 初始化 BenchmarkExecutor
    │      └─► 注册 Runners
    │
    ├─► 5. 启动 APIServer (port 8080, 后台线程)
    │
    └─► 6. 主线程等待信号
```

### 端口规划

| 端口 | 服务 | 说明 |
|------|------|------|
| 8000 | Prometheus Metrics | 监控指标暴露 |
| 8080 | HTTP API | 与 MCP Server 通信 |

## monitor 的实现

在monitor文件夹下，实现cpu、内存、磁盘等系统资源的采集，当前阶段只需要打log
启动main.py, 就可以把monitor的功能注册进去

## tool 的实现

在tool文件夹下，实现压力测试工具的生命周期管理功能。

支持的工具：unixbench, superpi, stream, mlc, fio, hping3

详细设计见 `doc/tool-api-design.md`

## benchmark 的实现

### 设计原则

1. **串行执行**: 同一时刻只允许运行一个 benchmark 任务，确保测试结果准确
2. **异步执行**: 长时间运行的测试任务采用异步方式，避免阻塞 API
3. **现场清理**: 测试前后自动清理临时文件和进程，避免磁盘空间被填满
4. **结果采集**: 测试完成后自动收集和解析结果

### 核心类设计

```
benchmark/
├── __init__.py          # 模块导出
├── executor.py          # BenchmarkExecutor - 任务执行器
├── task.py              # BenchmarkTask - 任务定义
├── result.py            # ResultCollector - 结果采集器
├── cleaner.py           # Cleaner - 现场清理器
└── runners/             # 各工具的运行器
    ├── __init__.py
    ├── base.py          # BaseRunner - 运行器基类
    ├── unixbench.py     # UnixBench 运行器
    ├── superpi.py       # SuperPi 运行器
    ├── stream.py        # STREAM 运行器
    ├── mlc.py           # MLC 运行器
    ├── fio.py           # FIO 运行器
    └── hping3.py        # hping3 运行器
```

### 任务状态

```python
class TaskStatus(Enum):
    PENDING = "pending"        # 等待执行
    PREPARING = "preparing"    # 准备中（检查工具、清理现场）
    RUNNING = "running"        # 执行中
    PAUSED = "paused"          # 已暂停
    COLLECTING = "collecting"  # 采集结果中
    CLEANING = "cleaning"      # 清理现场中
    COMPLETED = "completed"    # 已完成
    FAILED = "failed"          # 失败
    CANCELLED = "cancelled"    # 已取消
```

### BenchmarkTask 任务类

```python
@dataclass
class BenchmarkTask:
    task_id: str                    # 任务ID (UUID)
    test_name: str                  # 测试名称 (unixbench/superpi/stream/mlc/fio/hping3)
    params: Dict[str, Any]          # 测试参数
    status: TaskStatus = TaskStatus.PENDING
    process: Optional[subprocess.Popen] = None  # 进程句柄
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    result: Optional[Dict] = None   # 测试结果
    error: Optional[str] = None     # 错误信息
    log_buffer: List[str] = field(default_factory=list)  # 日志缓冲
    
    # 运行属性
    working_dir: Optional[str] = None    # 工作目录
    output_file: Optional[str] = None    # 输出文件路径
```

### BaseRunner 运行器基类

```python
class BaseRunner(ABC):
    """压测工具运行器基类"""
    
    # 运行器属性
    name: str                       # 运行器名称
    typical_duration: int           # 典型运行时间（秒），用于判断是否异步
    requires_async: bool            # 是否需要异步执行
    
    @abstractmethod
    def prepare(self, task: BenchmarkTask, tool_manager: ToolManager) -> bool:
        """准备测试环境（检查工具、创建工作目录）"""
        pass
    
    @abstractmethod
    def build_command(self, task: BenchmarkTask) -> List[str]:
        """构建执行命令"""
        pass
    
    @abstractmethod
    def collect_result(self, task: BenchmarkTask) -> Dict:
        """收集和解析测试结果"""
        pass
    
    @abstractmethod
    def get_cleanup_patterns(self) -> List[str]:
        """获取需要清理的文件/目录模式"""
        pass
```

### 工具运行时间与异步策略

| 工具 | 典型运行时间 | 是否异步 | 说明 |
|------|-------------|---------|------|
| stream | 1-5分钟 | **否** | 短时间测试，同步返回结果 |
| superpi | 1-10分钟 | 是 | 中等时间，异步执行 |
| unixbench | 30-60分钟 | 是 | 长时间，必须异步 |
| mlc | 5-30分钟 | 是 | 中等时间，异步执行 |
| fio | 可配置 | 是 | 根据参数判断，默认异步 |
| hping3 | 可配置 | 是 | 根据参数判断，默认异步 |

### BenchmarkExecutor 核心功能

```python
class BenchmarkExecutor:
    """压测任务执行器"""
    
    def __init__(self, tool_manager: ToolManager, result_collector: ResultCollector):
        self.tool_manager = tool_manager
        self.result_collector = result_collector
        self.cleaner = Cleaner()
        
        # 任务管理
        self._current_task: Optional[BenchmarkTask] = None
        self._task_lock = threading.Lock()  # 确保同时只有一个任务
        self._tasks: Dict[str, BenchmarkTask] = {}  # 所有任务历史
        
        # 运行器注册
        self._runners: Dict[str, BaseRunner] = {}
        self._register_runners()
    
    def run_benchmark(self, test_name: str, params: Dict) -> Dict:
        """
        执行压测（阻塞或异步）
        
        Returns:
            同步任务: {"status": "completed", "result": {...}}
            异步任务: {"status": "running", "task_id": "xxx"}
        """
        pass
    
    def run_benchmark_async(self, test_name: str, params: Dict) -> str:
        """异步执行压测，返回 task_id"""
        pass
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务 (SIGTERM -> SIGKILL)"""
        pass
    
    def pause_task(self, task_id: str) -> bool:
        """暂停任务 (SIGSTOP)"""
        pass
    
    def resume_task(self, task_id: str) -> bool:
        """恢复任务 (SIGCONT)"""
        pass
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """查询任务状态"""
        pass
    
    def get_current_task(self) -> Optional[BenchmarkTask]:
        """获取当前运行的任务"""
        pass
    
    def is_busy(self) -> bool:
        """是否有任务在运行"""
        pass
```

### 执行流程

```
run_benchmark(test_name, params)
    │
    ├─► 1. 互斥检查 (is_busy?)
    │      └─► 忙碌: 返回错误 "已有任务在运行"
    │
    ├─► 2. 创建任务 (BenchmarkTask)
    │
    ├─► 3. 准备阶段 (status: PREPARING)
    │      ├─► 检查工具是否已安装 (tool_manager.check_tool)
    │      ├─► 创建工作目录
    │      └─► 清理旧现场 (cleaner.cleanup_before)
    │
    ├─► 4. 判断同步/异步
    │      ├─► 同步 (stream): 
    │      │      ├─► 执行测试 (status: RUNNING)
    │      │      ├─► 收集结果 (status: COLLECTING)
    │      │      ├─► 清理现场 (status: CLEANING)
    │      │      └─► 返回结果 (status: COMPLETED)
    │      │
    │      └─► 异步 (其他):
    │             ├─► 启动后台线程执行
    │             └─► 立即返回 task_id (status: RUNNING)
    │
    └─► 异步执行线程:
           ├─► 执行测试
           ├─► 收集结果
           ├─► 清理现场
           └─► 更新状态
```

### Cleaner 现场清理器

```python
class Cleaner:
    """现场清理器"""
    
    # 默认清理模式
    DEFAULT_PATTERNS = [
        "/tmp/benchmark_*",        # 通用临时文件
        "/tmp/*.tmp",              # 临时文件
        "*.log",                   # 日志文件（工作目录下）
        "*.out",                   # 输出文件
    ]
    
    def cleanup_before(self, task: BenchmarkTask, runner: BaseRunner) -> bool:
        """
        测试前清理
        
        - 清理上次遗留的临时文件
        - 检查磁盘空间
        - 杀死残留进程
        """
        pass
    
    def cleanup_after(self, task: BenchmarkTask, runner: BaseRunner) -> bool:
        """
        测试后清理
        
        - 清理工作目录
        - 清理输出文件
        - 确保进程已终止
        - 检查磁盘空间恢复
        """
        pass
    
    def kill_process_tree(self, pid: int) -> bool:
        """杀死进程树（包括子进程）"""
        pass
    
    def clean_patterns(self, patterns: List[str], base_dir: str) -> int:
        """按模式清理文件，返回清理数量"""
        pass
```

### 数据存储设计

#### 存储位置
```
/var/lib/node_agent/
├── benchmark_results.db              # SQLite 结果数据库
└── logs/
    ├── 2026-03-12_143052_stream_a1b2c3.log    # 每次压测一个日志
    ├── 2026-03-12_150231_unixbench_d4e5f6.log
    └── 2026-03-12_160815_fio_g7h8i9.log
```

#### 日志文件命名规则
```
{date}_{time}_{test_name}_{task_id_short}.log
示例: 2026-03-12_143052_stream_a1b2c3.log
```

#### 为什么用 SQLite 存储结果

| 方案 | 优点 | 缺点 | 适用性 |
|------|------|------|--------|
| **SQLite** ✅ | Python内置无依赖、单文件易管理、支持SQL查询 | 并发写入有限 | ✅ 我们串行执行，完美匹配 |
| JSON文件 | 简单直接 | 文件散乱、查询困难、历史管理混乱 | ❌ 不好管理 |
| MySQL/PostgreSQL | 功能强大 | 需要额外部署维护，太重 | ❌ 过度设计 |
| InfluxDB | 已部署 | 时序数据库，压测结果不是时序数据 | ❌ 数据模型不匹配 |

**SQLite 的优势**：
1. **零依赖**: Python 标准库 `sqlite3`，无需 `pip install`
2. **单机守护进程的最佳选择**: SQLite 设计初衷就是嵌入式场景
3. **串行写入无冲突**: 我们的任务是串行的，不存在并发问题
4. **易于运维**: 单文件，备份/迁移/清理都是复制或删除一个文件

### ResultCollector 结果采集器

```python
class ResultCollector:
    """测试结果采集器"""
    
    def __init__(self, data_dir: str = "/var/lib/node_agent"):
        self.data_dir = Path(data_dir)
        self.db_path = self.data_dir / "benchmark_results.db"
        self.log_dir = self.data_dir / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def create_log_file(self, task: BenchmarkTask) -> Path:
        """创建日志文件，返回文件路径"""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        log_filename = f"{timestamp}_{task.test_name}_{task.task_id[:6]}.log"
        return self.log_dir / log_filename
    
    def write_log(self, log_path: Path, content: str):
        """写入日志（追加模式）"""
        with open(log_path, "a") as f:
            f.write(content)
    
    def collect(self, task: BenchmarkTask, runner: BaseRunner, 
                log_path: Path, raw_output: str) -> Dict:
        """
        采集测试结果
        
        1. 调用 runner.collect_result() 解析结果
        2. 附加元数据（时间、参数、系统信息）
        3. 存储到 SQLite
        4. 返回结构化结果
        """
        pass
    
    def get_result(self, task_id: str) -> Optional[Dict]:
        """获取历史结果"""
        pass
    
    def get_log_path(self, task_id: str) -> Optional[Path]:
        """获取日志文件路径（用于失败排查）"""
        pass
    
    def list_results(self, test_name: str = None, limit: int = 100) -> List[Dict]:
        """列出历史结果"""
        pass
    
    def export_result(self, task_id: str, format: str = "json") -> str:
        """导出结果（json/csv）"""
        pass
    
    def cleanup_old_logs(self, keep_days: int = 30) -> int:
        """清理旧日志文件，返回删除数量"""
        pass
```

### SQLite 表结构

```sql
CREATE TABLE IF NOT EXISTS benchmark_results (
    task_id TEXT PRIMARY KEY,
    test_name TEXT NOT NULL,
    status TEXT NOT NULL,
    
    -- 时间信息
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    duration_seconds REAL,
    
    -- 参数
    params TEXT,  -- JSON 格式
    
    -- 结果（各工具不同）
    metrics TEXT,  -- JSON 格式
    
    -- 系统信息
    hostname TEXT,
    os_info TEXT,
    kernel_version TEXT,
    cpu_model TEXT,
    
    -- 文件路径
    log_file TEXT,  -- 日志文件路径，失败排查用
    raw_output_file TEXT,  -- 原始输出文件路径（可选保留）
    
    -- 错误信息
    error_message TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_test_name ON benchmark_results(test_name);
CREATE INDEX idx_start_time ON benchmark_results(start_time);
CREATE INDEX idx_status ON benchmark_results(status);
```

### 结果数据结构

```python
@dataclass
class BenchmarkResult:
    # 基本信息
    task_id: str
    test_name: str
    status: str
    
    # 时间信息
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    
    # 测试参数
    params: Dict[str, Any]
    
    # 测试结果（各工具不同）
    metrics: Dict[str, Any]
    # 示例:
    # stream: {"triad": 45000.5, "copy": 42000.3, ...}  # MB/s
    # unixbench: {"single_core": 1500.5, "multi_core": 8000.2, ...}
    # fio: {"read_iops": 50000, "write_iops": 30000, ...}
    
    # 系统信息
    system_info: Dict[str, str]  # hostname, os, kernel, cpu_model, ...
    
    # 原始输出
    raw_output_path: Optional[str]  # 原始输出文件路径
```

### 与 ToolManager 的集成

```python
# 执行流程中的工具检查
def run_benchmark(self, test_name: str, params: Dict) -> Dict:
    # 1. 检查工具是否已安装
    tool_status = self.tool_manager.check_tool(test_name)
    if tool_status.get("status") != ToolStatus.INSTALLED:
        return {
            "status": "error",
            "error": f"Tool {test_name} not installed",
            "tool_status": tool_status
        }
    
    # 2. 获取工具二进制路径
    tool = self.tool_manager.get_tool(test_name)
    binary_path = tool.binary_path
    
    # 3. 执行测试...
```

### API 接口设计

| 路由 | 方法 | 说明 | 返回 |
|------|------|------|------|
| `/api/run_benchmark` | POST | 执行压测 | 同步: 结果; 异步: task_id |
| `/api/cancel_task` | POST | 取消任务 | success/failure |
| `/api/pause_task` | POST | 暂停任务 | success/failure |
| `/api/resume_task` | POST | 恢复任务 | success/failure |
| `/api/task_status/<task_id>` | GET | 查询状态 | 状态信息 |
| `/api/current_task` | GET | 当前任务 | 任务信息或null |
| `/api/results/<task_id>` | GET | 获取结果 | 测试结果 |
| `/api/results` | GET | 结果列表 | 历史结果列表 |

### 错误处理

```python
class BenchmarkError(Exception):
    """压测错误基类"""
    pass

class ToolNotInstalledError(BenchmarkError):
    """工具未安装"""
    pass

class TaskRunningError(BenchmarkError):
    """已有任务在运行"""
    pass

class CleanupError(BenchmarkError):
    """清理失败"""
    pass

class ResultParseError(BenchmarkError):
    """结果解析失败"""
    pass
```

### 日志推送

测试过程中的日志实时推送到 MCP Server:

```python
# 在任务执行线程中
def _execute_task(self, task: BenchmarkTask, runner: BaseRunner):
    while task.process.poll() is None:
        line = task.process.stdout.readline()
        if line:
            task.log_buffer.append(line)
            # 推送到 MCP Server (通过 WebSocket)
            self._push_log(task.task_id, line)
```

### 配置项

```python
BENCHMARK_CONFIG = {
    # 任务超时（秒）
    "task_timeout": {
        "stream": 600,        # 10分钟
        "superpi": 1800,      # 30分钟
        "unixbench": 7200,    # 2小时
        "mlc": 3600,          # 1小时
        "fio": 3600,          # 1小时
        "hping3": 1800,       # 30分钟
    },
    
    # 工作目录
    "working_dir": "/tmp/benchmark_work",
    
    # 结果存储
    "result_db": "/var/lib/node_agent/benchmark_results.db",
    
    # 清理配置
    "cleanup": {
        "enabled": True,
        "keep_raw_output": False,  # 是否保留原始输出
        "min_disk_space_gb": 5,    # 最小磁盘空间要求
    }
}
```

