# MCP Server

MCP (Model Context Protocol) Server for Perfa - 性能测试平台管理端

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

### 启动服务器

```bash
python main.py
```

### 测试连接

```bash
python test_mcp.py
```

### 配置客户端（Cursor 或 VSCode）

详见 [MCP_CLIENT_SETUP.md](./MCP_CLIENT_SETUP.md)

## 架构

```
┌──────────────────┐
│   用户 + AI      │
│   (客户端)        │
└────────┬─────────┘
         │ SSE (长连接)
         ↓
┌──────────────────┐
│   MCP Server     │
│   (远端服务器)    │
└────────┬─────────┘
         │ HTTP
         ↓
┌──────────────────┐
│   Agent 集群      │
└──────────────────┘
```

## 已实现的功能

### 服务器管理（5个工具）
- `register_server` - 注册服务器
- `list_servers` - 列出服务器
- `remove_server` - 移除服务器
- `get_server_info` - 获取服务器信息
- `update_server_info` - 更新服务器信息

### 待实现
- Agent 管理工具
- 压测工具管理
- Benchmark 管理
- 智能分析

## 开发

详见 `mcp_design.md`
