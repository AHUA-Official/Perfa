# Deep Dives

这一层是更像 deepwiki 的细粒度知识页，重点回答三类问题：

- 这个模块暴露了哪些接口或能力
- 请求在代码里是怎么流转的
- 改某类问题时应该先看哪些文件

## 目录

- [node-agent-api-and-flow.md](./node-agent-api-and-flow.md)
- [mcp-tools-and-flow.md](./mcp-tools-and-flow.md)
- [langchain-api-and-workflow.md](./langchain-api-and-workflow.md)
- [webui-v2-pages-and-dataflow.md](./webui-v2-pages-and-dataflow.md)

## 使用方式

如果你要排查一条完整链路，推荐顺序是：

1. Web UI
2. LangChain Agent API
3. MCP Tool
4. Node Agent API
