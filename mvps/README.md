# MCP开发组织方式总结

## 您的问题

> 这些接口都是给一个mcp的吗？然后写在一个mcp_server.py文件里面？

## 答案

**是的，所有54个接口都属于同一个MCP Server，但不建议写在一个文件里。**

---

## 推荐的项目结构

### 方案对比

| 方案 | 优点 | 缺点 | 适用场景 |
|------|------|------|----------|
| **单文件** | 简单快速 | 难以维护、代码冗长 | 原型、演示 |
| **模块化** | 清晰、易维护、团队协作 | 需要额外组织 | **生产环境** ✅ |

---

## 实际项目结构（推荐）

```
mcp_server_project/
├── server.py              # 主MCP Server入口（约200行）
│   - 创建MCP Server实例
│   - 注册所有54个工具
│   - 启动服务
│
├── tools/                 # 工具模块（按功能分类）
│   ├── agent.py          # Agent管理工具（7个）
│   ├── benchmark.py      # 压测执行工具（6个）
│   ├── monitoring.py     # 监控查询工具（4个）
│   ├── intelligence.py   # 智能分析工具（4个）
│   └── ...               # 其他模块
│
├── services/             # 业务逻辑服务
│   ├── agent_service.py  # Agent通信服务
│   ├── db_service.py     # 数据库服务
│   └── rag_service.py    # RAG检索服务
│
└── models/               # 数据模型
    └── ...
```

---

## 核心概念

### 1. 一个MCP Server = 所有工具的注册中心

```python
# server.py
from mcp import Server

server = Server("perfa")  # 创建一个MCP Server实例

# 注册工具1
@server.tool("deploy_agent")
async def deploy_agent(...):
    ...

# 注册工具2
@server.tool("run_benchmark")
async def run_benchmark(...):
    ...

# ... 注册所有54个工具

server.run()  # 启动服务
```

### 2. 工具实现按模块组织

```python
# tools/agent.py - Agent管理工具
async def deploy_agent(...):
    # 实现逻辑
    pass

async def check_agent_status(...):
    # 实现逻辑
    pass

# tools/benchmark.py - 压测执行工具
async def run_benchmark(...):
    # 实现逻辑
    pass
```

### 3. server.py负责注册和转发

```python
# server.py
from tools import agent, benchmark

@server.tool("deploy_agent")
async def deploy_agent(host, ssh_port, credentials):
    # 转发到具体实现
    return await agent.deploy_agent(host, ssh_port, credentials)

@server.tool("run_benchmark")
async def run_benchmark(agent_id, test_name, params):
    # 转发到具体实现
    return await benchmark.run_benchmark(agent_id, test_name, params)
```

---

## 工作流程示例

### AI调用工具的完整流程

```
1. AI调用 MCP Tool
   ↓
2. MCP Server (server.py) 接收请求
   ↓
3. 转发到对应模块 (tools/agent.py 或 tools/benchmark.py)
   ↓
4. 模块执行业务逻辑
   - 调用Agent API
   - 查询数据库
   - 调用RAG服务
   ↓
5. 返回结果给 AI
```

### 具体示例

```python
# AI要执行压测

# 步骤1: AI调用
result = mcp_client.call_tool("run_benchmark", {
    "agent_id": "agent_001",
    "test_name": "unixbench"
})

# 步骤2: MCP Server接收
# server.py中的 run_benchmark 函数被调用

# 步骤3: 转发到 tools/benchmark.py
# tools/benchmark.py中的 run_benchmark 函数执行

# 步骤4: 业务逻辑
# - 发送HTTP请求给Agent
# - Agent启动压测
# - Agent直写InfluxDB

# 步骤5: 返回结果
return {
    "task_id": "bench_001",
    "status": "running"
}
```

---

## 为什么不建议单文件？

### 单文件的问题

```python
# ❌ 不推荐：mcp_server.py（单文件，3000+行）

from mcp import Server

server = Server("perfa")

@server.tool("deploy_agent")
async def deploy_agent(...):
    # 100行实现
    pass

@server.tool("check_agent_status")
async def check_agent_status(...):
    # 50行实现
    pass

# ... 继续52个工具
# 文件变得非常长，难以维护
```

### 模块化的优势

```python
# ✅ 推荐：server.py（200行）
# 只负责注册工具，不包含实现

@server.tool("deploy_agent")
async def deploy_agent(...):
    return await agent.deploy_agent(...)

# tools/agent.py（500行）
# 包含7个Agent工具的具体实现

async def deploy_agent(...):
    # 具体实现
    pass
```

**优势**：
- ✅ server.py简洁，只负责注册
- ✅ 每个模块职责清晰
- ✅ 易于团队协作（不同成员负责不同模块）
- ✅ 易于测试和维护

---

## 开发步骤建议

### 第一步：创建基础结构

```bash
mkdir -p mcp_server_project/tools
touch mcp_server_project/server.py
touch mcp_server_project/tools/__init__.py
touch mcp_server_project/tools/agent.py
touch mcp_server_project/tools/benchmark.py
```

### 第二步：实现核心工具

1. 先实现 `tools/agent.py`（deploy_agent, check_agent_status）
2. 再实现 `tools/benchmark.py`（run_benchmark, get_benchmark_status）
3. 最后实现其他模块

### 第三步：在server.py注册

```python
# server.py
from tools import agent, benchmark

server = Server("perfa")

@server.tool("deploy_agent")
async def deploy_agent(...):
    return await agent.deploy_agent(...)

@server.tool("run_benchmark")
async def run_benchmark(...):
    return await benchmark.run_benchmark(...)

# ... 继续注册其他工具

server.run()
```

### 第四步：启动和测试

```bash
# 启动MCP Server
python server.py

# 或使用MCP客户端连接
mcp-client connect http://localhost:8000
```

---

## 总结

### 关键要点

1. **所有54个工具都属于同一个MCP Server**
2. **不建议写在一个文件**，应该模块化组织
3. **server.py只负责注册**，不包含实现
4. **每个模块实现一类工具**（如agent.py实现7个Agent工具）
5. **Agent是独立进程**，不包含在MCP Server代码中

### 文件数量

- **1个主文件**: server.py
- **13个工具模块**: tools/*.py
- **总共约20个文件**: 包含models、services等

### 代码行数

- **server.py**: ~200行（只注册工具）
- **每个工具模块**: ~300-500行
- **总计**: ~5000-7000行（分散在多个文件）

---

## 参考资料

已创建的示例文件：

1. **`mvp_simple_server.py`**: 单文件示例（不推荐）
2. **`mcp_server_project/`**: 模块化示例（推荐）
   - `server.py`: 主入口
   - `tools/agent.py`: Agent工具实现
   - `tools/benchmark.py`: 压测工具实现
   - `tools/monitoring.py`: 监控工具实现
   - `examples.py`: 使用示例

---

**建议**：从 `mcp_server_project/` 示例开始，逐步实现各个模块。
