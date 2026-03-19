# Perfa Web UI

ChatGPT 风格的对话界面，连接 Perfa Agent 后端。

## 快速启动

### 1. 启动后端

```bash
cd /home/ubuntu/Perfa/src/langchain_agent
./start_backend.sh
```

后端将在 `http://localhost:10000` 启动。

### 2. 启动前端

```bash
cd /home/ubuntu/Perfa/webui
./start.sh
```

前端将在 `http://localhost:3001` 启动。

## 访问

打开浏览器访问：`http://localhost:3001`

## 测试

### 使用 curl 测试后端

```bash
# 测试对话接口（同步）
curl -X POST http://localhost:10000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"perfa-agent","messages":[{"role":"user","content":"有哪些服务器？"}]}'

# 测试流式输出
curl -X POST http://localhost:10000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"perfa-agent","messages":[{"role":"user","content":"测试"}],"stream":true}'
```

## 配置说明

### 前端环境变量（docker-compose.yml）

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `OPENAI_API_KEY` | API Key（任意值） | `any-key` |
| `BASE_URL` | 后端 API 地址 | `http://host.docker.internal:10000/v1` |

### 修改后端地址

编辑 `webui/docker-compose.yml`，修改 `BASE_URL`：

```yaml
environment:
  - BASE_URL=http://your-backend-host:10000/v1
```

## 常见问题

### 1. 前端无法连接后端

确保：
- 后端已启动（访问 http://localhost:10000/health 检查）
- `BASE_URL` 配置正确
- Docker 网络配置正确（Linux 需要 `extra_hosts`）

### 2. MCP Server 连接失败

确保 MCP Server 已启动：

```bash
# 启动 MCP Server
cd /home/ubuntu/Perfa
python3 -m src.mcp_server.main
```

## 停止服务

```bash
# 停止前端
cd /home/ubuntu/Perfa/webui
docker-compose down

# 停止后端（Ctrl+C）
```
