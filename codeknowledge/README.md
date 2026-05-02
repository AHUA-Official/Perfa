# Perfa Code Knowledge

这个目录是 Perfa 仓库的本地知识库入口，目标是把分散在 `doc/`、`src/`、`webui*`、`test/` 中的说明整理成一套统一、可持续维护的文档结构。

## 建议阅读顺序

1. [00-map.md](./00-map.md) - 仓库地图与阅读入口
2. [01-architecture-overview.md](./01-architecture-overview.md) - 系统架构总览
3. `02-modules/` - 各核心模块分册
4. `03-operations/` - 运行、端口、部署
5. [04-testing-and-debugging.md](./04-testing-and-debugging.md) - 测试与排障
6. [05-doc-source-index.md](./05-doc-source-index.md) - 原始文档映射与状态判断
7. `06-deep-dives/` - 更细粒度的接口、调用链、关键文件索引
8. [07-history-and-operations-context.md](./07-history-and-operations-context.md) - 演进背景、当前环境、决策记录
9. [08-roadmap-and-spec.md](./08-roadmap-and-spec.md) - 升级目标、规格拆解、风险与路线图

## 目录结构

```text
codeknowledge/
├── README.md
├── 00-map.md
├── 01-architecture-overview.md
├── 02-modules/
│   ├── node-agent.md
│   ├── mcp-server.md
│   ├── langchain-agent.md
│   └── webui-v2.md
├── 03-operations/
│   ├── runtime-and-ports.md
│   └── deployment-and-startup.md
├── 04-testing-and-debugging.md
├── 05-doc-source-index.md
├── 07-history-and-operations-context.md
├── 08-roadmap-and-spec.md
└── 06-deep-dives/
    ├── README.md
    ├── node-agent-api-and-flow.md
    ├── mcp-tools-and-flow.md
    ├── langchain-api-and-workflow.md
    └── webui-v2-pages-and-dataflow.md
```

## 维护原则

- 以当前代码实现为主，旧设计文档仅作为背景。
- 每个主题优先给出“当前有效结论”，再附原始文档来源。
- 新增模块时，优先补充 `02-modules/`，并在 `00-map.md` 更新入口。
- 如果发现文档与代码不一致，以代码为准，并在 `05-doc-source-index.md` 标记差异。
