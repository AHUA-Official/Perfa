# Web UI V2: 页面与数据流

## 页面入口

- `webui-v2/src/app/page.tsx`

当前主导航页面：

- `chat`
- `servers`
- `reports`
- `monitor`

## 组件清单

### Chat

- `src/components/chat/ChatPage.tsx`
- `src/components/chat/ChatInput.tsx`
- `src/components/chat/ChatMessage.tsx`
- `src/components/chat/WorkflowProgress.tsx`
- `src/components/chat/ResultCard.tsx`

### Servers

- `src/components/servers/ServersPage.tsx`

### Reports

- `src/components/reports/ReportsPage.tsx`

### Monitor

- `src/components/monitor/MonitorPage.tsx`

## 前端数据层

### API 包装

- `webui-v2/src/lib/api.ts`

当前可见的主要前端请求函数：

- `chatCompletion`
- `chatCompletionStream`
- `listServers`
- `deployServerAgent`
- `uninstallServerAgent`
- `getServerAgentStatus`
- `listReports`
- `getReport`
- `listSessions`
- `getSession`
- `deleteSession`

### SSE 解析

- `webui-v2/src/lib/sse.ts`

当前前端明确支持两类流：

- 正文 `content`
- 过程事件 `event`

过程事件类型包括：

- `thinking_start`
- `thinking_result`
- `tool_result`
- `workflow_progress`
- `answer_start`
- `answer_done`
- `summary`

## 前后端调用链

### 对话链路

```text
ChatPage
  -> api.ts: chatCompletionStream()
  -> /api/v1/chat/completions
  -> langchain_agent /v1/chat/completions
  -> sse.ts 解析流
  -> 消息区 / 工作流进度区更新
```

### 服务器列表链路

```text
ServersPage
  -> api.ts: listServers()
  -> /api/v1/servers
  -> langchain_agent 扩展 API
```

### 报告链路

```text
ReportsPage
  -> api.ts: listReports()
  -> /api/v1/reports
```

## 关键文件索引

| 文件 | 作用 |
|------|------|
| `webui-v2/src/app/page.tsx` | 主界面壳与菜单 |
| `webui-v2/src/lib/api.ts` | API 请求封装 |
| `webui-v2/src/lib/sse.ts` | SSE 解析器 |
| `webui-v2/src/store/useChatStore.ts` | 聊天会话状态 |
| `webui-v2/src/components/chat/` | 对话与进度展示 |
| `webui-v2/src/components/servers/ServersPage.tsx` | 服务器管理 |
| `webui-v2/src/components/reports/ReportsPage.tsx` | 报告展示 |
| `webui-v2/src/components/monitor/MonitorPage.tsx` | 监控页面 |

## 改动建议

如果你要改：

- 对话体验，先看 `chat/` + `sse.ts`
- 页面 API 接口，先看 `lib/api.ts`
- 导航结构，先看 `src/app/page.tsx`
