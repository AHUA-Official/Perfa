# Perfa 完整架构设计

## 📁 项目结构总览

```
Perfa/
├── doc/
│   └── mcp_design.md              # MCP接口设计文档
│
├── mvps/
│   ├── mcp_server_project/        # MCP Server项目
│   │   ├── server.py              # 主入口
│   │   ├── tools/                 # 工具模块（54个工具）
│   │   │   ├── agent.py          # Agent管理工具
│   │   │   ├── benchmark.py      # 压测执行工具
│   │   │   └── monitoring.py     # 监控查询工具
│   │   ├── services/             # 业务服务
│   │   └── README.md
│   │
│   ├── daemonset_agent/           # Agent项目
│   │   ├── main.py               # 主入口
│   │   ├── core/                 # 核心模块
│   │   │   ├── agent.py         # Agent主类
│   │   │   ├── monitor.py       # 监控采集器
│   │   │   └── task_executor.py # 任务执行器
│   │   ├── api/                  # API服务
│   │   │   └── server.py        # HTTP API
│   │   ├── collectors/           # 采集器
│   │   ├── storage/              # 存储模块
│   │   └── README.md
│   │
│   ├── examples/                  # 示例代码
│   │   └── complete_workflow.py  # 完整流程示例
│   │
│   └── README.md                  # 总结文档
│
└── README.md                      # 项目说明
```

---

## 🏗️ 架构设计

### 整体架构

```
┌─────────────────────────────────────────────────────┐
│                  AI Agent (LLM)                      │
│              调用 MCP Tools / 读取 Resources          │
└────────────────────┬────────────────────────────────┘
                     │ MCP Protocol
                     ↓
┌─────────────────────────────────────────────────────┐
│            MCP Server Project                        │
│          (运行在管理服务器)                            │
│                                                      │
│  server.py                                           │
│  ├── Tools (54个)                                    │
│  │   ├── deploy_agent()                            │
│  │   ├── run_benchmark()                           │
│  │   └── query_monitoring_data()                   │
│  │                                                  │
│  ├── Resources                                      │
│  │   └── mcp://benchmark/history                   │
│  │                                                  │
│  └── Services                                       │
│      ├── Database Service (SQLite/InfluxDB)       │
│      └── RAG Service (Vector DB)                   │
└───────────┬─────────────────────┬───────────────────┘
            │                     │
            │ HTTP指令            │ 数据库查询
            ↓                     ↓
┌───────────────────────┐  ┌──────────────────────┐
│  DaemonSet Agent      │  │   InfluxDB          │
│ (被测服务器A)          │  │   (时序数据库)       │
│                       │  └──────────────────────┘
│  main.py              │           ↑
│  ├── HTTP API (9000) │           │ 直写监控数据
│  ├── Monitor         │───────────┘
│  └── Task Executor   │
└───────────────────────┘
            ↓
┌───────────────────────┐
│   SQLite              │
│  (本地数据库)          │
└───────────────────────┘
```

---

## 🔑 关键设计

### 1. 两个独立项目

| 项目 | 部署位置 | 职责 |
|------|----------|------|
| **mcp_server_project** | 管理服务器 | 提供MCP接口、管理Agent、查询数据 |
| **daemonset_agent** | 被测服务器 | 执行压测、采集监控、直写数据库 |

### 2. 数据流设计

#### ❌ 错误设计（v1.0）
```
监控数据: Agent → MCP Server → InfluxDB
                ↑ 性能瓶颈
```

#### ✅ 正确设计（v3.0）
```
监控数据: Agent → InfluxDB (直写，不走MCP)
控制指令: MCP Server → Agent (HTTP)
日志流: Agent → MCP Server (WebSocket)
```

### 3. 模块化组织

#### MCP Server（54个工具）

```
server.py (200行)
├── Agent管理类 (7个)
│   ├── deploy_agent
│   ├── check_agent_status
│   └── ...
│
├── 压测执行类 (6个)
│   ├── run_benchmark
│   ├── get_benchmark_status
│   └── ...
│
├── 监控查询类 (4个)
│   ├── start_monitoring
│   ├── query_monitoring_data
│   └── ...
│
└── 其他工具 (37个)
```

#### Agent（多线程）

```
main.py (50行)
└── Agent
    ├── Main Thread
    │   └── HTTP API Server
    │
    ├── Monitoring Thread
    │   ├── CPU Collector
    │   ├── GPU Collector
    │   └── InfluxDB Writer (直写)
    │
    ├── Task Execution Thread
    │   ├── PTS Runner
    │   └── SQLite Writer (直写)
    │
    └── Log Pusher Thread
        └── WebSocket Client
```

---

## 🚀 部署流程

### 步骤1: 部署数据库

```bash
# InfluxDB
docker run -d -p 8086:8086 influxdb:2.0

# SQLite (自动创建)
# Agent会在本地创建SQLite数据库
```

### 步骤2: 部署MCP Server

```bash
cd mvps/mcp_server_project/

# 安装依赖
pip install -r requirements.txt

# 配置
vim config.yaml

# 启动
python server.py
```

### 步骤3: 部署Agent（通过MCP工具）

```python
# AI调用
deploy_agent(
    host="192.168.1.100",
    ssh_port=22,
    credentials={"username": "root", "password": "xxx"}
)

# MCP Server会自动：
# 1. SSH连接目标服务器
# 2. 上传Agent代码
# 3. 安装依赖
# 4. 启动Agent服务
```

### 步骤4: 验证部署

```bash
# 检查Agent状态
curl http://192.168.1.100:9000/health

# AI调用
check_agent_status(agent_id="agent_192_168_1_100")
```

---

## 📖 使用示例

### 完整压测流程

```python
# 1. 部署Agent
deploy_agent(host="192.168.1.100", ...)

# 2. 安装压测环境
setup_bench_env(agent_id="agent_xxx", provider="pts")

# 3. 执行压测
run_benchmark(
    agent_id="agent_xxx",
    test_name="unixbench",
    params={"iterations": 3}
)
# 返回: {"task_id": "bench_xxx", "status": "running"}

# 4. 查询进度
get_benchmark_status(task_id="bench_xxx")

# 5. 查询监控数据
query_monitoring_data(task_id="bench_xxx", ...)

# 6. 生成报告
generate_expert_report(result_id="result_xxx")
```

---

## 🔧 关键代码位置

### MCP Server

| 功能 | 文件 | 行数 |
|------|------|------|
| 主入口 | server.py | ~200 |
| Agent工具 | tools/agent.py | ~300 |
| 压测工具 | tools/benchmark.py | ~250 |
| 监控工具 | tools/monitoring.py | ~200 |

**总计**: ~5000行（分散在多个文件）

### Agent

| 功能 | 文件 | 行数 |
|------|------|------|
| 主入口 | main.py | ~50 |
| Agent主类 | core/agent.py | ~200 |
| 监控采集 | core/monitor.py | ~300 |
| 任务执行 | core/task_executor.py | ~400 |
| API服务 | api/server.py | ~200 |

**总计**: ~1500-2000行（分散在多个文件）

---

## 📊 工具清单

### MCP Server (54个工具)

| 分类 | 工具数 | 核心工具 |
|------|--------|----------|
| Agent管理 | 7 | deploy_agent, check_agent_status |
| 服务器管理 | 5 | register_server, list_servers |
| 环境管理 | 5 | setup_bench_env, verify_environment |
| 压测执行 | 6 | run_benchmark, get_benchmark_status |
| 监控查询 | 4 | query_monitoring_data |
| 数据存储 | 5 | query_history, compare_results |
| 时序分析 | 4 | detect_anomaly, analyze_trend |
| 智能分析 | 4 | generate_expert_report |
| 任务管理 | 4 | list_running_tasks |
| 批量操作 | 2 | run_benchmark_suite |
| 数据管理 | 3 | compact_data, archive_old_results |
| 系统配置 | 3 | set_kernel_param |
| 系统健康 | 2 | health_check |

---

## 🎯 开发步骤建议

### Phase 1: 核心功能（4周）

**MCP Server**:
- ✅ server.py基础框架
- ✅ deploy_agent工具
- ✅ run_benchmark工具
- ✅ query_monitoring_data工具

**Agent**:
- ✅ main.py启动框架
- ✅ HTTP API服务器
- ✅ 监控采集器（CPU/GPU）
- ✅ InfluxDB写入器

### Phase 2: 完整功能（4周）

**MCP Server**:
- ✅ 所有54个工具
- ✅ RAG服务集成
- ✅ 数据库服务完善

**Agent**:
- ✅ 任务执行器（PTS支持）
- ✅ 日志推送器
- ✅ 健康检查器

### Phase 3: 优化和测试（4周）

- ✅ 单元测试
- ✅ 集成测试
- ✅ 性能优化
- ✅ 文档完善

---

## 📝 文档清单

| 文档 | 路径 | 说明 |
|------|------|------|
| MCP接口设计 | doc/mcp_design.md | 54个工具详细设计 |
| MCP Server结构 | mvps/mcp_server_project/README.md | 项目组织方式 |
| Agent结构 | mvps/daemonset_agent/README.md | Agent架构设计 |
| 完整示例 | mvps/examples/complete_workflow.py | 交互流程示例 |
| 总结文档 | mvps/README.md | MCP开发组织方式 |

---

## 💡 关键要点

### 1. 项目分离

- **MCP Server**: 管理端，一个实例
- **Agent**: 被测端，多实例部署

### 2. 数据流分离

- **控制流**: MCP Server → Agent (HTTP)
- **监控数据**: Agent → InfluxDB (直写)
- **测试结果**: Agent → SQLite (直写)

### 3. 代码组织

- **MCP Server**: 模块化，按功能分类
- **Agent**: 多线程，职责清晰

### 4. 通信协议

| 方向 | 协议 | 用途 |
|------|------|------|
| MCP Server → Agent | HTTP | 发送指令 |
| Agent → MCP Server | WebSocket | 推送日志 |
| Agent → InfluxDB | HTTP | 写入监控数据 |

---

## 🎓 学习路径

1. **阅读文档**: doc/mcp_design.md
2. **查看示例**: mvps/examples/complete_workflow.py
3. **实现核心**: server.py + agent.py
4. **逐步扩展**: 添加其他工具和模块
5. **测试验证**: 单元测试 + 集成测试

---

**总结**: 两个独立项目，模块化组织，数据流分离，职责清晰。
