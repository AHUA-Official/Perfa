# MCP Server 设计文档

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置环境变量

```bash
export MCP_HOST="0.0.0.0"
export MCP_PORT="9000"
export MCP_API_KEY="your-api-key"
export MCP_DB_PATH="/var/lib/mcp/mcp.db"
```

或创建 `.env` 文件：

```bash
# .env
MCP_HOST=0.0.0.0
MCP_PORT=9000
MCP_API_KEY=your-secure-api-key-here
MCP_DB_PATH=/var/lib/mcp/mcp.db
MCP_AGENT_TIMEOUT=30
```

### 启动服务器

```bash
python main.py
```

### 测试连接

```bash
python test_mcp.py
```

---

## 部署架构

MCP Server 部署在远端服务器，通过 SSE (Server-Sent Events) 与 AI 客户端通信。

```
┌─────────────────────────────────────────────────┐
│              用户 + AI (客户端)                  │
└────────────────────┬────────────────────────────┘
                     │ SSE (长连接)
┌────────────────────┴────────────────────────────┐
│             MCP Server (管理端)                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐        │
│  │  Tools   │ │Resources │ │  SQLite  │        │
│  └─────┬────┘ └──────────┘ └─────┬────┘        │
└────────┼──────────────────────────┼─────────────┘
         │ HTTP/gRPC 控制指令        │
         ↓                          │
┌────────────────────────────────────────────────┐
│      Agent 守护进程（部署在被测服务器）          │
│  ┌──────────────────────────────────────┐     │
│  │ 任务执行器 (Benchmark/Tool)           │     │
│  └──────────────────────────────────────┘     │
│  ┌──────────────────────────────────────┐     │
│  │ 监控采集器 (直写 VM 时序数据库)        │     │
│  └──────────────────────────────────────┘     │
│  ┌──────────────────────────────────────┐     │
│  │ 本地 SQLite (测试结果)                │     │
│  └──────────────────────────────────────┘     │
└────────────────────────────────────────────────┘
```

---

## 客户端配置

### Cursor 配置

1. 打开 Cursor 设置：`Cmd+,` (Mac) 或 `Ctrl+,` (Windows/Linux)
2. 搜索 "MCP" 或 "Model Context Protocol"

**配置文件** (`~/.cursor/mcp_settings.json` 或 `%APPDATA%\Cursor\mcp_settings.json`)：

```json
{
  "mcpServers": {
    "perfa": {
      "url": "http://localhost:9000/sse",
      "apiKey": "your-api-key-here"
    }
  }
}
```

配置后需要重启 Cursor。

### VSCode 配置（使用 Continue 插件）

1. 安装 **Continue** 插件
2. 打开配置文件：`Cmd+Shift+P` → "Continue: Open Config File"

**配置文件** (`config.json`)：

```json
{
  "models": [
    {
      "title": "Claude",
      "provider": "anthropic",
      "model": "claude-3-5-sonnet-20241022",
      "apiKey": "your-anthropic-api-key"
    }
  ],
  "contextProviders": [
    {
      "name": "mcp",
      "params": {
        "servers": {
          "perfa": {
            "url": "http://localhost:9000/sse",
            "apiKey": "your-mcp-api-key"
          }
        }
      }
    }
  ]
}
```

### 命令行测试

```bash
# 测试 SSE 连接
curl -N http://localhost:9000/sse?api_key=your-api-key-here

# 列出工具
curl -X POST http://localhost:9000/message \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key-here" \
  -d '{"method": "tools/list", "params": {}}'

# 调用 list_servers
curl -X POST http://localhost:9000/message \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key-here" \
  -d '{"method": "tools/call", "params": {"name": "list_servers", "arguments": {}}}'
```

---

## 技术可行性：AI 如何准确调用 MCP？

### 核心机制

AI 客户端（如 Claude、GPT）通过 **Function Calling** 能力，自动理解用户意图并准确填充 MCP Tool 参数。

### 工作流程

```
用户: "帮我测试一下 192.168.1.100 这台服务器的 CPU 性能"
         ↓
AI 分析意图: 需要执行 CPU 压测
         ↓
AI 匹配工具: run_benchmark (server_id?, test_name="unixbench", params?)
         ↓
AI 填充参数:
  - server_id: 需要先查询或注册
  - test_name: "unixbench" (CPU 性能测试)
  - params: 默认参数
         ↓
AI 执行: 先调用 register_server 或 list_servers，再调用 run_benchmark
```

### 为什么能准确填充参数？

#### 1. MCP Tools 自描述

每个 Tool 都有完整的 JSON Schema 描述，包括：
- 工具名称和功能描述
- 每个参数的类型、是否必填、默认值
- 参数的说明文档

示例：
```json
{
  "name": "run_benchmark",
  "description": "执行压测任务",
  "inputSchema": {
    "type": "object",
    "properties": {
      "server_id": {
        "type": "string",
        "description": "服务器ID，可通过 list_servers 查询"
      },
      "test_name": {
        "type": "string",
        "enum": ["unixbench", "stream", "fio", ...],
        "description": "测试名称"
      },
      "params": {
        "type": "object",
        "description": "测试参数，不同工具有不同参数"
      }
    },
    "required": ["server_id", "test_name"]
  }
}
```

#### 2. AI 的推理能力

AI 可以：
- **理解自然语言**：将用户意图映射到具体工具
- **推导缺失参数**：如果用户没提供 server_id，AI 会先调用 `list_servers` 查询
- **选择合适参数**：根据测试类型（CPU/内存/磁盘）自动选择对应工具
- **处理依赖关系**：知道要先部署 Agent 才能运行压测

#### 3. 多轮对话上下文

AI 保持对话上下文，可以：
- 记住之前提到的服务器 ID
- 在后续操作中复用上下文信息
- 通过追问获取缺失的必填参数

### 实际场景示例

**场景 1：用户只说服务器 IP**
```
用户: "帮我测试 192.168.1.100 的内存性能"

AI 自动推理:
1. 192.168.1.100 是 IP，需要转换为 server_id
2. 调用 list_servers() 看是否已注册
3. 如未注册，调用 register_server("192.168.1.100", ...)
4. 调用 run_benchmark(server_id, "stream", ...)
```

**场景 2：用户指定测试参数**
```
用户: "用 fio 测试磁盘随机读写，bs=4k，size=10G"

AI 自动推理:
1. test_name = "fio"
2. params = {"bs": "4k", "size": "10G", "rw": "randrw"}
3. 调用 run_benchmark(server_id, "fio", params)
```

**场景 3：用户意图模糊**
```
用户: "看看这台服务器性能怎么样"

AI 自动追问:
"您想测试哪方面性能？CPU、内存还是磁盘？"
"服务器 IP 是多少？"
```

### 关键设计要点

为了确保 AI 能准确填充参数：

1. **清晰的工具描述**：每个工具的 description 要明确说明功能
2. **参数枚举值**：对于有限选项的参数，提供 enum 列表
3. **参数说明**：每个参数都要有 description，说明含义和取值
4. **默认值**：非必填参数提供合理默认值
5. **依赖提示**：在描述中说明参数的获取方式（如"可通过 xxx 查询"）

---

## 代码结构

```
src/mcp_server/
├── main.py                    # 入口文件
├── config.py                  # 配置管理
├── server.py                  # MCP Server 核心实现
│
├── tools/                     # MCP Tools 实现
│   ├── __init__.py           # 工具注册
│   ├── base.py               # Tool 基类和通用方法
│   ├── server_tools.py       # 服务器管理工具（5个）
│   ├── agent_tools.py        # Agent 管理工具（5个）
│   ├── tool_tools.py         # 工具管理工具（4个）
│   ├── benchmark_tools.py    # Benchmark 管理工具（5个）
│   └── report_tools.py       # 智能分析工具（1个）
│
├── agent_client/              # Agent HTTP 客户端
│   ├── __init__.py
│   ├── client.py             # 与 Agent 通信的客户端
│   └── models.py             # Agent 返回的数据模型
│
├── storage/                   # MCP Server 本地存储
│   ├── __init__.py
│   ├── database.py           # SQLite 数据库操作
│   └── models.py             # 数据模型（Server, Agent 等）
│
├── mcp_design.md              # 本设计文档
└── requirements.txt           # Python 依赖
```

### 依赖说明

```txt
# requirements.txt
mcp                          # MCP SDK
requests                     # HTTP 客户端
paramiko                     # SSH 连接
pydantic                     # 数据验证和模型
starlette                    # Web 框架
uvicorn                      # ASGI 服务器
```

---

## 安全性设计

### 单用户认证

使用 API Key 进行简单认证：

```
┌──────────────┐
│   AI 客户端   │
│  (带 API Key) │
└──────┬───────┘
       │ SSE + API Key in Header
       ↓
┌──────────────┐
│  MCP Server  │
│  (验证 Key)   │
└──────────────┘
```

### 认证流程

1. MCP Server 启动时加载 API Key (环境变量或配置文件)
2. AI 客户端连接时，在请求头携带: `Authorization: Bearer <api_key>`
3. MCP Server 验证 Key，无效则返回 401 Unauthorized
4. 验证通过后，正常处理请求

### SSH 凭证存储

- SSH 密码加密存储（使用 Python `cryptography` 库）
- 加密密钥从环境变量加载
- `list_servers` 不返回密码字段（脱敏）

---

## 回调机制设计

### 为什么需要回调？

`run_benchmark` 可能需要几分钟到几小时：
- UnixBench: 30-60 分钟
- FIO: 根据配置，几分钟到几十分钟
- Stream: 1-5 分钟

AI 客户端不能一直等待，需要回调机制。

### 回调流程

```
┌──────────────┐                          ┌──────────────┐
│   AI 客户端   │                          │  MCP Server  │
└──────┬───────┘                          └──────┬───────┘
       │ 1. run_benchmark(server_id, ...)       │
       │────────────────────────────────────────>│
       │                                         │
       │ 2. 返回 task_id (立即返回)               │
       │<────────────────────────────────────────│
       │                                         │
       │          (AI 可以继续其他对话)            │
       │                                         │
       │                                         │ 3. 转发请求给 Agent
       │                                         │──────────────>┌──────────┐
       │                                         │               │  Agent   │
       │                                         │               │ (执行测试)│
       │                                         │               └─────┬────┘
       │                                         │                     │
       │                                         │ 4. 任务完成，回调    │
       │                                         │<────────────────────│
       │                                         │                     │
       │ 5. 通知 AI (SSE 推送)                    │                     │
       │<────────────────────────────────────────│                     │
       │                                         │                     │
       │ 6. AI 调用 get_benchmark_result(task_id)│                     │
       │────────────────────────────────────────>│                     │
       │                                         │                     │
       │ 7. 返回完整结果                          │                     │
       │<────────────────────────────────────────│                     │
```

---

## 错误场景处理

### Agent 离线

```python
# get_server_info
if not agent_client.is_online(agent_id):
    return {
        "server": server_info,
        "hardware": None,
        "status": None,
        "error": "Agent offline",
        "agent_status": "offline"
    }
```

### 并发控制

Agent 同时只能运行一个压测任务：

```python
# run_benchmark
current_task = agent_client.get_current_task(agent_id)
if current_task and current_task["status"] == "running":
    return {
        "error": "Agent busy",
        "message": f"Agent is running {current_task['test_name']}"
    }
```

### 错误码定义

| 错误码 | 说明 | HTTP 状态码 |
|--------|------|------------|
| `UNAUTHORIZED` | API Key 无效 | 401 |
| `SERVER_NOT_FOUND` | 服务器不存在 | 404 |
| `AGENT_OFFLINE` | Agent 离线 | 503 |
| `AGENT_BUSY` | Agent 正在执行任务 | 409 |
| `TASK_NOT_FOUND` | 任务不存在 | 404 |
| `TOOL_NOT_INSTALLED` | 工具未安装 | 400 |

---

## MCP Tools 设计

### 1. 服务器生命周期管理

| 工具 | 功能 |
|------|------|
| `register_server` | 注册压测服务器，测试 SSH 连接 |
| `list_servers` | 列出已注册服务器，显示 Agent 状态 |
| `remove_server` | 移除服务器注册 |
| `get_server_info` | 获取服务器硬件信息和实时状态 |
| `update_server_info` | 更新服务器别名、标签、SSH 凭证 |

### 2. Agent 生命周期管理

| 工具 | 功能 | 实现方式 |
|------|------|----------|
| `deploy_agent` | 部署完整监控栈 | 检查环境 → rsync 传输 → 调用 `start-all.sh` |
| `check_agent_status` | 检查 Agent 运行状态 | 调用 Agent `/api/status` |
| `get_agent_logs` | 获取 Agent 日志 | 调用 Agent `/api/storage/logs` |
| `configure_agent` | 配置 Agent 参数 | 调用 Agent `/api/config` |
| `uninstall_agent` | 停止所有服务 | 调用 `stop-all.sh` |

**deploy_agent 部署流程：**
```
1. 检查运行时环境 (Python3, pip3, Docker, Docker Compose)
2. 创建安装目录
3. rsync 传输项目文件 (deploy/, src/node_agent/)
4. pip3 安装 Python 依赖
5. 调用 start-all.sh (启动 VM → Grafana → Agent)
6. 验证 Agent 健康状态
```

### 3. 压测工具管理

| 工具 | 功能 | Agent API |
|------|------|-----------|
| `install_tool` | 安装压测工具 | `POST /api/tools/<name>/install` |
| `uninstall_tool` | 卸载压测工具 | `POST /api/tools/<name>/uninstall` |
| `list_tools` | 列出工具状态 | `GET /api/tools` |
| `verify_tool` | 验证工具可用性 | `GET /api/tools/<name>` |

**支持的工具：**
| 工具 | 类别 | 说明 |
|------|------|------|
| unixbench | CPU | CPU 综合性能测试 |
| superpi | CPU | CPU 浮点性能测试 |
| stream | 内存 | 内存带宽测试 |
| mlc | 内存 | Intel 内存延迟测试 |
| fio | 磁盘 | 磁盘 I/O 性能测试 |
| hping3 | 网络 | 网络性能测试 |

### 4. Benchmark 管理

| 工具 | 功能 | Agent API |
|------|------|-----------|
| `run_benchmark` | 执行压测任务 | `POST /api/benchmark/run` |
| `get_benchmark_status` | 查询任务状态 | `GET /api/benchmark/tasks/<task_id>` |
| `cancel_benchmark` | 取消压测任务 | `POST /api/benchmark/cancel` |
| `get_benchmark_result` | 获取压测结果 | `GET /api/benchmark/results/<task_id>` |
| `list_benchmark_history` | 列出历史记录 | `GET /api/benchmark/results` |

**run_benchmark 参数说明：**
```json
{
  "server_id": "服务器 ID",
  "test_name": "unixbench/stream/fio/superpi/mlc/hping3",
  "params": {
    // UnixBench
    "single": true, "multi": true,
    // STREAM
    "array_size": 100000000, "ntimes": 10, "nt": 4,
    // FIO
    "rw": "randread", "bs": "4k", "size": "1G", "iodepth": 32, "numjobs": 1,
    // SuperPi
    "digits": 1048576,
    // hping3
    "target": "192.168.1.1", "count": 10, "interval": 1
  }
}
```

### 5. 智能分析

| 工具 | 功能 |
|------|------|
| `generate_report` | 生成压测分析报告 |

**报告类型：**
- `single`: 单次测试报告
- `comparison`: 多次测试对比
- `diagnosis`: 问题诊断和建议

**输出内容：**
- 测试摘要（关键指标）
- 性能分析（性能等级、瓶颈）
- 监控数据（从 VM 查询）
- 问题识别（CPU 饱和、内存压力等）
- 优化建议（基于测试类型和问题）

---

## 工具清单汇总 (20 个工具)

| 分类 | 工具数 | 工具列表 |
|------|--------|----------|
| 服务器管理 | 5 | `register_server`, `list_servers`, `remove_server`, `get_server_info`, `update_server_info` |
| Agent 管理 | 5 | `deploy_agent`, `check_agent_status`, `get_agent_logs`, `configure_agent`, `uninstall_agent` |
| 工具管理 | 4 | `install_tool`, `uninstall_tool`, `list_tools`, `verify_tool` |
| Benchmark 管理 | 5 | `run_benchmark`, `get_benchmark_status`, `cancel_benchmark`, `get_benchmark_result`, `list_benchmark_history` |
| 智能分析 | 1 | `generate_report` |

---

## 与 Agent API 的映射关系

| MCP Tool | Agent API |
|----------|-----------|
| check_agent_status | GET /health, GET /api/status |
| get_agent_logs | GET /api/storage/logs |
| configure_agent | POST /api/config |
| install_tool | POST /api/tools/<name>/install |
| uninstall_tool | POST /api/tools/<name>/uninstall |
| list_tools | GET /api/tools |
| verify_tool | GET /api/tools/<name> |
| run_benchmark | POST /api/benchmark/run |
| get_benchmark_status | GET /api/benchmark/tasks/<task_id> |
| cancel_benchmark | POST /api/benchmark/cancel |
| get_benchmark_result | GET /api/benchmark/results/<task_id> |
| list_benchmark_history | GET /api/benchmark/results |
| get_server_info | GET /api/system/info, GET /api/system/status |

---

## 常见问题

### Q1: Cursor 找不到 MCP 配置选项？

Cursor 的 MCP 功能在较新版本中才有，请确保：
- Cursor 版本 >= 0.40.0
- 检查是否有 "Experimental Features" 需要开启

### Q2: 连接失败 "Connection refused"？

检查：
1. MCP Server 是否正在运行
   ```bash
   ps aux | grep "python main.py"
   ```
2. 端口是否被占用
   ```bash
   lsof -i :9000
   ```
3. 防火墙是否允许连接

### Q3: API Key 无效？

确保：
1. 环境变量设置正确
   ```bash
   echo $MCP_API_KEY
   ```
2. 配置文件中的 API Key 与环境变量一致

### Q4: 工具调用失败？

查看 MCP Server 日志：
```bash
python main.py

# 或者后台运行
python main.py > mcp.log 2>&1 &
tail -f mcp.log
```

---

## 核心设计原则

| 原则 | 说明 |
|------|------|
| **单一职责** | 每个工具只做一件事 |
| **Agent 自治** | Agent 本地采集数据、直写数据库、管理本地工具 |
| **控制数据分离** | MCP 只传控制指令，不传高频监控数据 |
| **简洁至上** | 工具数量精简，避免过度设计 |
