# MCP 客户端配置指南

本文档说明如何配置 Cursor 和 VSCode 连接到 MCP Server。

## 前置条件

1. MCP Server 已启动（运行 `python main.py`）
2. 已设置 API Key（环境变量 `MCP_API_KEY`）

## 1. Cursor 配置

### 步骤 1：打开设置

1. 打开 Cursor
2. 按 `Cmd+,` (Mac) 或 `Ctrl+,` (Windows/Linux) 打开设置
3. 搜索 "MCP" 或 "Model Context Protocol"

### 步骤 2：配置 MCP Server

在 Cursor 设置中找到 MCP 配置部分，添加以下内容：

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

或者直接编辑配置文件：

**Mac/Linux**: `~/.cursor/mcp_settings.json`  
**Windows**: `%APPDATA%\Cursor\mcp_settings.json`

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

### 步骤 3：重启 Cursor

配置后需要重启 Cursor 才能生效。

### 步骤 4：测试连接

在 Cursor 的聊天框中，输入：

```
列出所有服务器
```

如果配置成功，Cursor 会调用 `list_servers` 工具并返回结果。

---

## 2. VSCode 配置（使用 Continue 插件）

VSCode 需要安装 **Continue** 插件来支持 MCP。

### 步骤 1：安装 Continue 插件

1. 打开 VSCode
2. 按 `Cmd+Shift+X` 打开扩展商店
3. 搜索 "Continue"
4. 安装 "Continue - Open Source AI Code Assistant"

### 步骤 2：配置 Continue

1. 按 `Cmd+Shift+P` 打开命令面板
2. 输入 "Continue: Open Config File"
3. 选择 `config.json` 打开

在 `config.json` 中添加 MCP 配置：

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

### 步骤 3：测试连接

在 Continue 的聊天框中，输入：

```
@perfa 列出所有服务器
```

如果配置成功，Continue 会调用 `list_servers` 工具。

---

## 3. 快速测试（命令行）

如果想先测试 MCP Server 是否正常运行，可以使用 `curl`：

### 测试健康检查

```bash
# 测试 SSE 连接
curl -N http://localhost:9000/sse?api_key=your-api-key-here
```

### 测试工具调用

```bash
# 列出工具
curl -X POST http://localhost:9000/message \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key-here" \
  -d '{
    "method": "tools/list",
    "params": {}
  }'

# 调用 list_servers
curl -X POST http://localhost:9000/message \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key-here" \
  -d '{
    "method": "tools/call",
    "params": {
      "name": "list_servers",
      "arguments": {}
    }
  }'
```

---

## 4. 完整示例：注册服务器

配置成功后，你可以在 Cursor 或 VSCode 中这样使用：

**用户**:
```
帮我注册一台服务器，IP 是 192.168.1.100，SSH 用户是 root，密码是 password123
```

**AI 会自动**:
1. 调用 `register_server` 工具
2. 填充参数：
   ```json
   {
     "ip": "192.168.1.100",
     "ssh_user": "root",
     "ssh_password": "password123",
     "port": 22
   }
   ```
3. 返回结果

---

## 5. 常见问题

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
# 查看 stdout
python main.py

# 或者后台运行并查看日志
python main.py > mcp.log 2>&1 &
tail -f mcp.log
```

---

## 6. 环境变量配置示例

创建 `.env` 文件（不要提交到 Git）：

```bash
# .env
MCP_HOST=0.0.0.0
MCP_PORT=9000
MCP_API_KEY=your-secure-api-key-here
MCP_DB_PATH=/var/lib/mcp/mcp.db
MCP_AGENT_TIMEOUT=30
```

启动时加载：
```bash
export $(cat .env | xargs)
python main.py
```

---

## 7. 下一步

配置成功后，你可以：
1. 注册服务器
2. 部署 Agent（需要实现 agent_tools）
3. 运行压测（需要实现 benchmark_tools）

详见 `mcp_design.md`
