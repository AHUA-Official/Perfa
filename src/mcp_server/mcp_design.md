# MCP Server 设计文档

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

### MCP Protocol 的优势

MCP (Model Context Protocol) 是为 AI 设计的协议：
- 标准化的工具描述格式
- 支持 JSON Schema 参数验证
- 支持 Resources（只读数据）和 Tools（可执行操作）
- 支持 Prompts（预定义提示模板）

---

## 代码结构设计

### 目录结构

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
└── README.md                  # 使用说明
```

### 依赖说明

使用现成的库，不重复造轮子：

```txt
# requirements.txt
mcp                          # MCP SDK
requests                     # HTTP 客户端
paramiko                     # SSH 连接
pydantic                     # 数据验证和模型
```

Python 标准库：
- `sqlite3` - 数据库
- `logging` - 日志
- `dataclasses` - 配置和数据类
- `typing` - 类型注解

### 设计准则

#### 1. 单一职责原则
每个模块只负责一件事：
- `tools/` - 只负责实现 MCP Tools 的业务逻辑
- `agent_client/` - 只负责与 Agent 通信
- `storage/` - 只负责本地数据存储
- `utils/` - 只提供通用工具函数

#### 2. 依赖注入
不硬编码依赖，通过参数或配置注入：

```python
# ❌ 不好的做法
class ServerTools:
    def __init__(self):
        self.db = Database("/var/lib/mcp/mcp.db")  # 硬编码路径
        self.agent_client = AgentClient()          # 硬编码依赖

# ✅ 好的做法
class ServerTools:
    def __init__(self, db: Database, agent_client: AgentClient):
        self.db = db
        self.agent_client = agent_client
```

#### 3. 接口抽象
定义清晰的接口，便于测试和替换：

```python
# agent_client/client.py
class AgentClient(ABC):
    @abstractmethod
    def get_status(self, agent_id: str) -> AgentStatus:
        pass
    
    @abstractmethod
    def run_benchmark(self, agent_id: str, test_name: str, params: dict) -> str:
        pass

# 实现
class HTTPAgentClient(AgentClient):
    def __init__(self, base_url: str):
        self.base_url = base_url
    
    def get_status(self, agent_id: str) -> AgentStatus:
        response = requests.get(f"{self.base_url}/api/status")
        return AgentStatus.from_dict(response.json())
```

#### 4. 错误处理统一
统一的错误处理和响应格式：

```python
# utils/exceptions.py
class MCPError(Exception):
    """MCP 错误基类"""
    def __init__(self, code: str, message: str, details: dict = None):
        self.code = code
        self.message = message
        self.details = details or {}

class ServerNotFoundError(MCPError):
    def __init__(self, server_id: str):
        super().__init__(
            code="SERVER_NOT_FOUND",
            message=f"Server {server_id} not found",
            details={"server_id": server_id}
        )

class AgentOfflineError(MCPError):
    def __init__(self, agent_id: str):
        super().__init__(
            code="AGENT_OFFLINE",
            message=f"Agent {agent_id} is offline",
            details={"agent_id": agent_id}
        )
```

#### 5. 配置管理
使用配置文件，不硬编码：

```python
# config.py
from dataclasses import dataclass

@dataclass
class Config:
    # MCP Server
    host: str = "0.0.0.0"
    port: int = 9000
    
    # 数据库
    db_path: str = "/var/lib/mcp/mcp.db"
    
    # Agent
    agent_timeout: int = 30
    
    @classmethod
    def from_env(cls) -> "Config":
        """从环境变量加载配置"""
        import os
        return cls(
            host=os.getenv("MCP_HOST", "0.0.0.0"),
            port=int(os.getenv("MCP_PORT", "9000")),
            db_path=os.getenv("MCP_DB_PATH", "/var/lib/mcp/mcp.db"),
            agent_timeout=int(os.getenv("MCP_AGENT_TIMEOUT", "30")),
        )
```

#### 6. 日志规范
使用 Python 标准库 `logging`，配置结构化日志：

```python
# config.py
import logging

logging.basicConfig(
    level=logging.INFO,
    format='{"time": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"}'
)
```

#### 7. 数据验证
使用 `pydantic` 进行数据验证：

```python
# storage/models.py
from pydantic import BaseModel
from datetime import datetime

class Server(BaseModel):
    server_id: str
    ip: str
    port: int = 22
    alias: str = ""
    agent_id: str | None = None
    created_at: datetime
    
class AgentStatus(BaseModel):
    agent_id: str
    status: str  # online/offline/degraded
    version: str
    uptime_seconds: int
```

### 核心类设计

#### Tool 基类

```python
# tools/base.py
from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseTool(ABC):
    """MCP Tool 基类"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """工具名称"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """工具描述"""
        pass
    
    @property
    @abstractmethod
    def input_schema(self) -> Dict[str, Any]:
        """参数 Schema"""
        pass
    
    @abstractmethod
    def execute(self, **kwargs) -> Dict[str, Any]:
        """执行工具"""
        pass
    
    def to_mcp_tool(self) -> Dict[str, Any]:
        """转换为 MCP Tool 定义"""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema
        }
```

#### 工具实现示例

```python
# tools/server_tools.py
from .base import BaseTool
from storage.database import Database
from agent_client import AgentClient

class GetServerInfoTool(BaseTool):
    name = "get_server_info"
    description = "获取服务器信息和实时状态"
    
    input_schema = {
        "type": "object",
        "properties": {
            "server_id": {
                "type": "string",
                "description": "服务器ID"
            }
        },
        "required": ["server_id"]
    }
    
    def __init__(self, db: Database, agent_client: AgentClient):
        self.db = db
        self.agent_client = agent_client
    
    def execute(self, server_id: str) -> Dict[str, Any]:
        # 1. 从数据库获取服务器信息
        server = self.db.get_server(server_id)
        if not server:
            raise ServerNotFoundError(server_id)
        
        # 2. 从 Agent 获取实时状态
        try:
            status = self.agent_client.get_system_status(server.agent_id)
            hardware = self.agent_client.get_system_info(server.agent_id)
        except Exception as e:
            logger.error("Failed to get agent status", error=e, server_id=server_id)
            status = None
            hardware = None
        
        # 3. 返回合并结果
        return {
            "server": server.to_dict(),
            "hardware": hardware,
            "status": status
        }
```

---

## MCP Resources（可选）

MCP Resources 提供只读数据访问，但**不是必需的**。所有数据都可以通过 Tools 获取。

如果需要实现，可用于：
- 提供静态文档或配置
- 缓存频繁访问的数据

当前设计中，暂不实现 Resources，所有数据通过 Tools 获取即可。

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

### 配置

```python
# config.py
@dataclass
class Config:
    # MCP Server
    host: str = "0.0.0.0"
    port: int = 9000
    
    # 认证
    api_key: str = ""  # 从环境变量加载
    
    # 数据库
    db_path: str = "/var/lib/mcp/mcp.db"
    
    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            api_key=os.getenv("MCP_API_KEY", ""),
            # ...
        )
```

### 认证流程

```
1. MCP Server 启动时加载 API Key (环境变量或配置文件)
2. AI 客户端连接时，在请求头携带: Authorization: Bearer <api_key>
3. MCP Server 验证 Key，无效则返回 401 Unauthorized
4. 验证通过后，正常处理请求
```

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

### Agent 回调接口

Agent 任务完成后，回调 MCP Server：

```python
# Agent 完成任务后调用
POST http://<mcp_server>:9000/api/callback/benchmark

{
    "agent_id": "agent-001",
    "task_id": "task-xxx",
    "status": "completed",  # 或 "failed"
    "timestamp": "2026-03-13T10:30:00Z"
}
```

### MCP Server 处理回调

```python
# server.py
@app.post("/api/callback/benchmark")
async def benchmark_callback(request: Request):
    data = await request.json()
    task_id = data["task_id"]
    status = data["status"]
    
    # 1. 更新任务状态
    db.update_task_status(task_id, status)
    
    # 2. 通过 SSE 通知 AI 客户端
    await sse_notify(task_id, status)
    
    return {"success": True}
```

### SSE 通知

MCP Server 通过 SSE 推送任务完成通知：

```python
# AI 客户端订阅
GET /sse?api_key=<key>

# 推送消息
event: benchmark_complete
data: {"task_id": "xxx", "status": "completed"}
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

# run_benchmark
if not agent_client.is_online(agent_id):
    raise AgentOfflineError(agent_id)
```

### 并发控制

参考 node_agent 设计，Agent 同时只能运行一个压测任务：

```python
# run_benchmark
# 1. 检查 Agent 当前任务
current_task = agent_client.get_current_task(agent_id)
if current_task and current_task["status"] == "running":
    return {
        "error": "Agent busy",
        "message": f"Agent is running {current_task['test_name']} (task_id: {current_task['task_id']})",
        "current_task": current_task
    }

# 2. 发起新任务
task_id = agent_client.run_benchmark(agent_id, test_name, params)
return {"task_id": task_id, "status": "started"}
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

## 核心设计原则

| 原则 | 说明 |
|------|------|
| **单一职责** | 每个工具只做一件事 |
| **Agent 自治** | Agent 本地采集数据、直写数据库、管理本地工具 |
| **控制数据分离** | MCP 只传控制指令，不传高频监控数据 |
| **简洁至上** | 工具数量精简，避免过度设计 |

## 数据流说明

**控制流**（MCP Server → Agent）：
- AI 调用 MCP Tool（如 `run_benchmark`）
- MCP Server 发送指令给 Agent（HTTP/gRPC）
- Agent 执行任务并返回结果

**数据流**（Agent → 数据库）：
- Agent 监控线程本地采集数据（psutil、nvidia-smi）
- Agent 直写 VM 时序数据库（高频监控数据）
- Agent 直写本地 SQLite（测试结果和日志）
- MCP 需要时向 Agent 查询数据，不独立存储测试数据

---

## MCP Tools 设计

### 1. 服务器生命周期管理

#### `register_server`
**功能**: 注册压测服务器
- 接收服务器信息（IP、SSH 端口、认证方式）
- 测试 SSH 连接是否可达
- 存入 SQLite，返回唯一 `server_id`

#### `list_servers`
**功能**: 列出已注册服务器
- 返回服务器列表（ID、IP、端口等）
- 联动 Agent 状态（已部署/未部署/在线/离线）

#### `remove_server`
**功能**: 移除服务器注册
- 检查是否有正在运行的任务
- 检查 Agent 是否已卸载
- 从 SQLite 删除配置

#### `get_server_info`
**功能**: 获取服务器信息和实时状态
- 通过 Agent API 查询硬件信息（CPU 型号、内存大小、磁盘容量等）
- 同时返回实时状态（当前 CPU 使用率、内存占用、磁盘使用等）
- 调用 Agent `/api/system/info` 和 `/api/system/status`

#### `update_server_info`
**功能**: 更新服务器信息
- 更新别名、标签、SSH 凭证等
- 需验证 SSH 连接可用

---

### 2. Agent 生命周期管理

#### `deploy_agent`
**功能**: 在目标服务器部署 Agent
- SSH 连接目标服务器
- 安装依赖和 Agent 代码
- 配置并启动 Agent 守护进程

#### `check_agent_status`
**功能**: 检查 Agent 运行状态
- 调用 Agent `/health` 接口
- 返回版本、运行时长、当前任务等

#### `get_agent_logs`
**功能**: 获取 Agent 日志
- 调用 Agent API 获取日志
- 支持时间范围和级别过滤

#### `configure_agent`
**功能**: 配置 Agent 参数
- 更新监控频率、日志级别等配置
- Agent 热更新，无需重启

#### `uninstall_agent`
**功能**: 卸载 Agent
- 停止服务、删除代码和配置
- 保留已采集的数据

---

### 3. 压测工具管理

> 说明：这些工具是对 Agent `/api/tools` 相关接口的封装

#### `install_tool`
**功能**: 在 Agent 上安装压测工具
- 调用 Agent `/api/tools/<tool_name>/install`
- 支持：unixbench、stream、superpi、mlc、fio、hping3

#### `uninstall_tool`
**功能**: 卸载压测工具

#### `list_tools`
**功能**: 列出工具状态
- 调用 Agent `/api/tools`
- 返回已安装/未安装状态

#### `verify_tool`
**功能**: 验证工具可用性
- 调用 Agent `/api/tools/<tool_name>`

---

### 4. Benchmark 管理

#### `run_benchmark`
**功能**: 执行压测任务
- 调用 Agent `/api/benchmark/run`
- Agent 执行测试并直写本地 SQLite
- 返回 `task_id`（异步任务）

#### `get_benchmark_status`
**功能**: 查询压测任务状态
- 调用 Agent `/api/benchmark/tasks/<task_id>`
- 返回进度、状态等

#### `cancel_benchmark`
**功能**: 取消压测任务
- 调用 Agent `/api/benchmark/cancel`

#### `get_benchmark_result`
**功能**: 获取压测结果
- 调用 Agent `/api/benchmark/results/<task_id>`
- 返回测试指标、日志路径，包括对应的日志的log

#### `list_benchmark_history`
**功能**: 列出历史测试记录
- 调用 Agent `/api/benchmark/results`

---

### 5. 智能分析

#### `generate_report`
**功能**: 生成压测分析报告
- 从 Agent 获取测试结果
- 从 VM 时序数据库查询监控数据
- 使用 RAG 检索相关知识库
- 生成结构化分析报告

---

## 工具清单汇总 (约 16 个工具)

| 分类 | 工具数 | 工具列表 |
|------|--------|----------|
| 服务器管理 | 5 | register_server, list_servers, remove_server, get_server_info, update_server_info |
| Agent 管理 | 5 | deploy_agent, check_agent_status, get_agent_logs, configure_agent, uninstall_agent |
| 工具管理 | 4 | install_tool, uninstall_tool, list_tools, verify_tool |
| Benchmark 管理 | 5 | run_benchmark, get_benchmark_status, cancel_benchmark, get_benchmark_result, list_benchmark_history |
| 智能分析 | 1 | generate_report |

---

## 为什么这样设计？

### 1. 为什么把实时状态集成到服务器信息查询中？

- 查询服务器时，用户通常既想看硬件配置，也想看当前状态
- 不需要单独的监控工具，Agent 会在压测时自动采集并写入 VM 时序数据库
- AI 需要了解服务器状态时，直接调用 `get_server_info` 即可

### 2. 为什么去掉时序分析、趋势预测等工具？

这些是数据分析功能，不应该放在 MCP 层：
- 如果 AI 需要分析数据，可以调用 `generate_report` 生成报告
- 复杂的数据分析应该由 Agent 或独立的分析服务完成
- MCP 保持简洁，只做控制协调

### 3. 为什么去掉批量操作、任务管理类工具？

- `wait_for_task` - AI 可以轮询 `get_benchmark_status`
- `run_benchmark_suite` - AI 可以循环调用 `run_benchmark`
- `list_running_tasks` - AI 可以调用 `check_agent_status` 获取当前任务
- MCP 不应该过度封装 Agent 的能力

### 4. 为什么只保留一个智能分析工具？

- `generate_report` 是核心价值接口，整合了结果数据 + 监控数据 + RAG 知识库
- `query_knowledge_base`、`suggest_optimization` 等功能可以整合在报告生成中
- AI 可以根据报告内容继续追问，不需要独立的查询工具

---

## 与 Agent API 的映射关系

| MCP Tool | Agent API |
|----------|-----------|
| check_agent_status | GET /health, GET /api/status |
| get_agent_logs | GET /api/storage/logs |
| configure_agent | POST /api/config (待实现) |
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
