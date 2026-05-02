# 原始文档映射

这个文件用于回答两个问题：

1. 仓库里原来的文档都在哪
2. 哪些适合继续信，哪些只适合作为历史背景

## 文档分布

| 路径 | 类型 | 当前建议 |
|------|------|----------|
| `webui-v2/README.md` | 当前前端说明 | 高价值 |
| `test/node_agent_test.md` | 测试手册 | 高价值 |

## 当前判断原则

### 可以视为“当前有效入口”的文档

- `webui-v2/README.md`
- `test/node_agent_test.md`

### 可以视为“设计背景”的文档

- 已吸收进 `codeknowledge/` 的历史规格与进度信息

### 可以视为“需要弱化”的文档

- 已移除的旧入口和重复说明：
- `doc/README.md`
- `src/README.md`
- `webui/README.md`
- `PORTS.md`
- `doc/PROGRESS.md`
- `doc/UPGRADE_SPEC.md`

## 这次整理后的关系

本次新增的 `codeknowledge/` 不替代原始文档文件，它承担的是：

- 统一入口
- 消除文档散落
- 标记“当前实现”与“历史设计”的边界
- 提供更适合代码阅读和维护的组织方式

同时，本次已经删除以下容易误导的旧入口文档：

- `doc/README.md`
- `src/README.md`
- `webui/README.md`
- `PORTS.md`

在进一步吸收独有信息后，以下历史文档也已可删除：

- `src/langchain_agent/PHASE2_DESIGN.md`
- `doc/LangChain+MCP-项目设计与技术选型.md`
- `src/node_agent/design.md`
- `src/mcp_server/mcp_design.md`

当前仍保留的历史文档只有两份：

- 无

## 后续建议

如果你准备继续收敛文档，下一步最值得做的是：

1. 把仓库根目录 README 重写成总入口，并链接 `codeknowledge/`
2. 给 `node_agent`、`mcp_server`、`langchain_agent` 各补一个“接口清单”章节
3. 给 `ops/` 增加环境拓扑文档，明确本地与远程部署模式
