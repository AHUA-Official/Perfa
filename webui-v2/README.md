# Perfa Web UI V2

自研 Next.js 前端，替换 ChatGPT-Next-Web。

## 技术栈

- Next.js 14 (App Router) + TypeScript
- Ant Design 5 (暗色主题)
- Tailwind CSS
- ECharts (图表)
- Zustand (状态管理)
- react-markdown + react-syntax-highlighter (消息渲染)

## 开发

```bash
cd /home/ubuntu/Perfa/webui-v2
npm install
npm run dev
```

访问: http://localhost:3002

## 生产构建

```bash
npm run build
npm run start
```

## 与旧版对比

| 特性 | webui/ (ChatGPT-Next-Web) | webui-v2/ (自研) |
|------|--------------------------|-------------------|
| 部署方式 | Docker | npm / Docker |
| 工作流进度 | ❌ | ✅ 实时进度条 |
| 结果卡片 | ❌ | ✅ 结构化展示 |
| 服务器管理 | ❌ | ✅ |
| 报告页面 | ❌ | ✅ ECharts 图表 |
| 自定义主题 | ❌ | ✅ Dark Tech 风格 |
| 端口 | 3001 | 3002 |

## 与后端 API 交互

- `/v1/chat/completions` — SSE 流式对话
- `/v1/servers` — 服务器列表
- `/v1/reports` — 报告列表

Next.js rewrites 自动代理 `/api/*` → `http://localhost:10000/*`
