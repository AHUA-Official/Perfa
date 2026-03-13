# MCP 客户端配置示例

本目录包含 VSCode 和 Cursor 的 MCP 配置示例文件。

## 文件说明

- `vscode_mcp_config.json` - VSCode MCP 配置示例
- `cursor_mcp_config.json` - Cursor MCP 配置示例

## 配置步骤

### 1. 修改配置文件

将配置文件中的参数修改为你的实际值：

- `<SERVER_IP>` - MCP Server 的 IP 地址（本地为 `localhost`，远程为实际 IP）
- `<API_KEY>` - 你的 API Key（与服务器端 `MCP_API_KEY` 环境变量一致）
- `<PORT>` - MCP Server 端口（默认 `9000`）

### 2. 导入配置

#### VSCode

1. 打开 VSCode 设置：`Ctrl + ,`（Mac: `Cmd + ,`）
2. 搜索 "MCP"
3. 点击 "Edit in settings.json"
4. 将 `vscode_mcp_config.json` 的内容复制进去

#### Cursor

1. 打开 Cursor 设置：`Ctrl + Shift + J`（Mac: `Cmd + Shift + J`）
2. 搜索 "MCP"
3. 找到 MCP Servers 配置项
4. 点击 "Edit"
5. 将 `cursor_mcp_config.json` 的内容复制进去

或者直接编辑配置文件：

- macOS/Linux: `~/.cursor/mcp.json`
- Windows: `%USERPROFILE%\.cursor\mcp.json`

## 安全提示

⚠️ **请勿将包含真实 API Key 的配置文件提交到 Git 仓库！**

建议：
1. 使用环境变量存储敏感信息
2. 在 `.gitignore` 中添加配置文件
3. 使用不同的 API Key 进行生产和测试

## 可用工具

连接成功后，你可以使用以下工具：

1. **register_server** - 注册性能测试服务器
2. **list_servers** - 列出所有已注册服务器
3. **remove_server** - 移除服务器
4. **get_server_info** - 获取服务器详细信息
5. **update_server_info** - 更新服务器信息

## 使用示例

在 Cursor 或 VSCode 的 AI 对话中，直接说：

```
帮我注册一个性能测试服务器，IP 是 192.168.1.100，SSH 用户是 root
```

AI 会自动调用 `register_server` 工具完成注册。
