# Perfa

Perfa 是一个面向服务器性能测试的多组件系统，当前主线由四部分组成：

- `src/node_agent/` - 被测节点执行端
- `src/mcp_server/` - MCP Tool 服务层
- `src/langchain_agent/` - 对话与编排层
- `webui-v2/` - 当前主用前端

## 文档入口

统一知识库在 [codeknowledge/README.md](./codeknowledge/README.md)。

建议从这里开始阅读：

1. [codeknowledge/00-map.md](./codeknowledge/00-map.md) - 仓库地图
2. [codeknowledge/01-architecture-overview.md](./codeknowledge/01-architecture-overview.md) - 架构总览
3. [codeknowledge/02-modules/](./codeknowledge/02-modules/) - 核心模块分册
4. [codeknowledge/06-deep-dives/](./codeknowledge/06-deep-dives/) - 接口、调用链、关键文件索引

## 快速定位

- 运行与端口: [codeknowledge/03-operations/runtime-and-ports.md](./codeknowledge/03-operations/runtime-and-ports.md)
- 部署与启动: [codeknowledge/03-operations/deployment-and-startup.md](./codeknowledge/03-operations/deployment-and-startup.md)
- 测试与排障: [codeknowledge/04-testing-and-debugging.md](./codeknowledge/04-testing-and-debugging.md)
- 原始文档映射: [codeknowledge/05-doc-source-index.md](./codeknowledge/05-doc-source-index.md)

## 说明

仓库中仍保留一部分历史文档和旧方案目录。后续维护请优先更新 `codeknowledge/`，把它作为统一知识入口。
