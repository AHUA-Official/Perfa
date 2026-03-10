# DaemonSet Agent 项目结构

> Agent是部署在被测服务器上的独立守护进程，负责执行压测、采集监控数据、上报状态

---

## 项目结构

```
daemonset_agent/
├── __init__.py
├── main.py                    # Agent主入口
├── config.yaml                # 配置文件
│
├── core/                      # 核心模块
│   ├── __init__.py
│   ├── agent.py              # Agent主类
│   ├── task_executor.py      # 任务执行器
│   ├── monitor.py            # 监控采集器
│   ├── logger.py             # 日志推送器
│   └── health.py             # 健康检查
│
├── collectors/                # 监控采集器（各种指标）
│   ├── __init__.py
│   ├── cpu_collector.py      # CPU指标采集
│   ├── memory_collector.py   # 内存指标采集
│   ├── gpu_collector.py      # GPU指标采集
│   ├── thermal_collector.py  # 温度采集
│   └── power_collector.py    # 功耗采集
│
├── benchmark/                 # 压测执行模块
│   ├── __init__.py
│   ├── pts_runner.py         # PTS测试执行器
│   ├── docker_runner.py      # Docker测试执行器
│   └── native_runner.py      # 原生测试执行器
│
├── api/                       # API服务（MCP Server调用）
│   ├── __init__.py
│   ├── server.py             # HTTP API服务器
│   └── routes.py             # API路由
│
├── communication/             # 通信模块
│   ├── __init__.py
│   ├── http_client.py        # HTTP客户端（与MCP Server通信）
│   └── websocket_client.py   # WebSocket客户端（推送日志）
│
├── storage/                   # 存储模块
│   ├── __init__.py
│   ├── influxdb_writer.py    # InfluxDB写入器
│   └── sqlite_writer.py      # SQLite写入器
│
├── utils/                     # 工具模块
│   ├── __init__.py
│   ├── system.py             # 系统工具
│   └── hardware.py           # 硬件信息工具
│
├── systemd/                   # 系统服务配置
│   └── perfa-agent.service   # systemd服务文件
│
└── tests/                     # 测试
    ├── test_collector.py
    └── test_executor.py
```

---

## 核心模块职责

| 模块 | 职责 | 关键功能 |
|------|------|----------|
| **core/agent.py** | Agent主类 | 启动所有模块、管理生命周期 |
| **core/task_executor.py** | 任务执行器 | 执行压测任务、管理进程 |
| **core/monitor.py** | 监控采集器 | 本地采集指标、直写InfluxDB |
| **collectors/** | 具体采集器 | psutil、nvidia-smi等 |
| **benchmark/** | 压测执行器 | PTS、Docker、原生测试 |
| **api/server.py** | HTTP API | 接收MCP Server指令 |
| **storage/** | 数据写入 | 直写InfluxDB/SQLite |

---

## 关键设计要点

### 1. 多线程架构

```python
# Agent内部架构
Agent
├── Main Thread              # 主线程
│   └── HTTP API Server     # 接收指令
│
├── Monitoring Thread        # 监控线程（独立运行）
│   ├── CPU Collector
│   ├── GPU Collector
│   ├── Thermal Collector
│   └── InfluxDB Writer     # 直写InfluxDB
│
├── Task Execution Thread    # 任务执行线程
│   ├── PTS Runner
│   └── Result Writer       # 写入SQLite
│
└── Log Pusher Thread        # 日志推送线程
    └── WebSocket Client     # 推送到MCP Server
```

### 2. 数据流向

```
采集器 → InfluxDB (直写，不走MCP)
任务结果 → SQLite (直写)
日志 → MCP Server (WebSocket推送)
状态 → MCP Server (HTTP上报)
```

### 3. 通信协议

| 方向 | 协议 | 用途 |
|------|------|------|
| MCP Server → Agent | HTTP | 发送任务指令 |
| Agent → MCP Server | WebSocket | 推送日志流 |
| Agent → MCP Server | HTTP | 上报健康状态 |
| Agent → InfluxDB | HTTP | 写入监控数据 |

---

## 配置示例

```yaml
# config.yaml
agent:
  id: "agent_001"
  name: "test-server-01"
  
mcp_server:
  url: "http://192.168.1.10:8000"
  websocket_url: "ws://192.168.1.10:8000/logs"
  
influxdb:
  url: "http://192.168.1.20:8086"
  token: "my-token"
  org: "perfa"
  bucket: "metrics"
  
sqlite:
  path: "/opt/perfa/agent/data.db"
  
monitoring:
  enabled: true
  interval: 5  # 秒
  metrics:
    - cpu_percent
    - memory_used
    - cpu_temp
    - gpu_temp
    - power
    
api:
  host: "0.0.0.0"
  port: 9000
  
logging:
  level: "INFO"
  path: "/var/log/perfa-agent.log"
```

---

## 启动方式

### 方式1: 直接运行

```bash
python main.py --config config.yaml
```

### 方式2: systemd服务

```bash
# 安装服务
sudo cp systemd/perfa-agent.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable perfa-agent
sudo systemctl start perfa-agent

# 查看状态
sudo systemctl status perfa-agent

# 查看日志
sudo journalctl -u perfa-agent -f
```

---

## 开发步骤建议

### 第一步：实现核心框架

1. `main.py` - 启动入口
2. `core/agent.py` - Agent主类
3. `api/server.py` - HTTP API

### 第二步：实现监控采集

1. `core/monitor.py` - 监控管理器
2. `collectors/cpu_collector.py` - CPU采集
3. `storage/influxdb_writer.py` - 写入InfluxDB

### 第三步：实现任务执行

1. `core/task_executor.py` - 任务执行器
2. `benchmark/pts_runner.py` - PTS执行
3. `storage/sqlite_writer.py` - 写入SQLite

### 第四步：实现通信

1. `communication/websocket_client.py` - 日志推送
2. `communication/http_client.py` - 状态上报

---

## 测试方式

```bash
# 单元测试
pytest tests/

# 集成测试
python -m pytest tests/integration/

# 手动测试API
curl http://localhost:9000/health
curl -X POST http://localhost:9000/api/run_benchmark \
  -H "Content-Type: application/json" \
  -d '{"test_name": "unixbench", "params": {}}'
```

---

## 关键文件说明

| 文件 | 行数 | 说明 |
|------|------|------|
| main.py | ~50 | 启动入口 |
| core/agent.py | ~200 | Agent主类 |
| core/monitor.py | ~150 | 监控管理器 |
| core/task_executor.py | ~200 | 任务执行器 |
| collectors/cpu_collector.py | ~100 | CPU采集器 |
| api/server.py | ~100 | API服务器 |
| storage/influxdb_writer.py | ~100 | InfluxDB写入 |

**总计**: ~1500-2000行代码（分散在多个文件）

---

## 与MCP Server的关系

```
┌──────────────────────────────────────┐
│         MCP Server Project           │
│  (运行在管理服务器上)                  │
│                                      │
│  server.py                           │
│  ├── deploy_agent() → SSH部署Agent   │
│  ├── run_benchmark() → HTTP调用Agent │
│  └── query_monitoring_data() →      │
│       从InfluxDB查询                 │
└──────────────────────────────────────┘

         ↓ SSH部署
         ↓ HTTP指令
         ↑ WebSocket日志
         
┌──────────────────────────────────────┐
│      DaemonSet Agent Project         │
│    (运行在被测服务器上)                │
│                                      │
│  main.py → Agent                     │
│  ├── HTTP API (接收指令)             │
│  ├── Monitor (直写InfluxDB)         │
│  └── Task Executor (写入SQLite)     │
└──────────────────────────────────────┘

         ↓ 直写监控数据
         ↓ 直写测试结果
         
┌──────────────────────────────────────┐
│          InfluxDB / SQLite           │
│        (数据库服务器)                  │
└──────────────────────────────────────┘
```

---

## 部署流程

```bash
# 1. 在MCP Server上打包Agent代码
cd mcp_server_project/
python scripts/pack_agent.py  # 打包为 agent.tar.gz

# 2. SCP到目标服务器
scp agent.tar.gz user@192.168.1.100:/tmp/

# 3. SSH到目标服务器
ssh user@192.168.1.100

# 4. 解压安装
mkdir -p /opt/perfa/agent
tar -xzf /tmp/agent.tar.gz -C /opt/perfa/agent
cd /opt/perfa/agent

# 5. 安装依赖
pip install -r requirements.txt

# 6. 配置
vim config.yaml

# 7. 启动
python main.py --config config.yaml

# 或安装为系统服务
sudo cp systemd/perfa-agent.service /etc/systemd/system/
sudo systemctl start perfa-agent
```

---

## 总结

### Agent是独立项目

- **独立代码库**: daemonset_agent/
- **独立部署**: 部署在被测服务器
- **独立进程**: systemd守护进程
- **独立配置**: config.yaml

### 与MCP Server的关系

- **MCP Server**: 部署Agent、发送指令
- **Agent**: 接收指令、执行任务、上报数据
- **数据库**: 共享（InfluxDB、SQLite）

### 关键设计

- **多线程**: 监控、任务、日志独立运行
- **直写数据库**: 监控数据不走MCP
- **HTTP API**: 接收MCP Server指令
- **WebSocket**: 推送日志到MCP Server
