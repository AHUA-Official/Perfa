# Web UI V2

## 定位

`webui-v2/` 是当前主用前端。它替代了旧的 `webui/`，承担用户主要交互入口。

## 技术栈

从 `webui-v2/README.md` 和目录可确认：

- Next.js 14 App Router
- TypeScript
- Ant Design 5
- Tailwind CSS
- Zustand
- ECharts

## 页面结构

主页面壳位于 `webui-v2/src/app/page.tsx`，当前导航包括：

- `chat`
- `servers`
- `reports`
- `monitor`

对应组件目录：

- `src/components/chat/`
- `src/components/servers/`
- `src/components/reports/`
- `src/components/monitor/`

## 关键前端能力

### 对话页

- `ChatPage.tsx`
- `ChatInput.tsx`
- `ChatMessage.tsx`
- `WorkflowProgress.tsx`
- `ResultCard.tsx`

这说明前端不只是简单聊天框，还包含工作流进度和结构化结果展示。

### 状态管理

- `src/store/useChatStore.ts`

### API 封装

- `src/lib/api.ts`
- `src/lib/sse.ts`

### 代理层

- `src/app/api/v1/chat/completions/route.ts`

结合 README，可知前端通过 Next.js 代理后端 API，而不是浏览器直接打后端服务。

## 当前运行方式

README 给出的开发地址是 `http://localhost:3002`，这也和旧文档中的“V2 使用 3002”一致。

## 与旧版前端的关系

- `webui/` 是旧方案，基于 ChatGPT-Next-Web
- `webui-v2/` 是当前主线，应作为后续文档、联调和演示入口

## 目录视图

```text
webui-v2/
├── src/app/
├── src/components/
│   ├── chat/
│   ├── servers/
│   ├── reports/
│   └── monitor/
├── src/lib/
├── src/store/
├── package.json
└── README.md
```
