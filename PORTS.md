# Perfa 端口配置

本文档统一管理 Perfa 项目的所有端口，避免冲突。

## 端口分配表

| 服务 | 端口 | 说明 | 状态 |
|------|------|------|------|
| **Node Agent** | | | |
| Agent API | 8080 | HTTP API 服务 | 已占用 |
| Agent Metrics | 8000 | Prometheus 指标 | 已占用 |
| **MCP Server** | | | |
| MCP Server | 9000 | MCP 工具服务 | 已占用 |
| **LangChain Agent** | | | |
| Agent API | 10000 | OpenAI 兼容 API | ✅ 新分配 |
| **数据库** | | | |
| ChromaDB | 8001 | 向量数据库 | 已占用 |
| SQLite | - | 本地数据库 | 内嵌 |
| **可视化** | | | |
| Grafana | 3000 | 监控面板 | 已占用 |
| VictoriaMetrics | 8428 | 时序数据库 | 已占用 |
| **Web UI** | | | |
| ChatGPT-Next-Web | 3001 | 对话界面 | ✅ 新分配 |

## 端口段划分

```
3000-3999  : 可视化服务（Grafana 3000, Web UI 3001）
5000-5999  : 备用
8000-8999  : Agent 和数据库服务
9000-9999  : MCP 和内部服务
10000-10999: LangChain Agent 扩展服务
```

## 使用说明

### 1. 环境变量配置

在 `.env` 文件中：

```bash
# Node Agent
NODE_AGENT_API_PORT=8080
NODE_AGENT_METRICS_PORT=8000

# MCP Server
MCP_PORT=9000

# LangChain Agent
LANGCHAIN_API_PORT=10000

# Database
CHROMADB_PORT=8001

# Web UI
WEBUI_PORT=3001
```

### 2. 启动服务

确保按以下顺序启动，避免端口冲突：

```bash
# 1. Node Agent（端口 8080, 8000）
cd /home/ubuntu/Perfa/deploy
./start-all.sh

# 2. MCP Server（端口 9000）
cd /home/ubuntu/Perfa
python3 -m src.mcp_server.main

# 3. LangChain Agent API（端口 10000）
cd /home/ubuntu/Perfa/src/langchain_agent
./start_backend.sh

# 4. Web UI（端口 3001）
cd /home/ubuntu/Perfa/webui
./start.sh
```

### 3. 检查端口占用

```bash
# 查看所有 Perfa 相关端口
netstat -tuln | grep -E ':(3000|3001|8000|8001|8080|8428|9000|10000)'

# 或使用 ss
ss -tuln | grep -E ':(3000|3001|8000|8001|8080|8428|9000|10000)'
```
