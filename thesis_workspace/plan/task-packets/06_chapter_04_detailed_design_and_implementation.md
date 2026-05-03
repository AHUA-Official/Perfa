# Task Packet

- Scope: 写作第四章系统详细设计与实现，覆盖 Node Agent、MCP Server、LangChain Agent、WebUI V2、报告生成与知识增强。
- Files to read: `src/node_agent/main.py`, `src/node_agent/api/routes/*.py`, `src/node_agent/monitor/*.py`, `src/node_agent/tool/manager.py`, `src/node_agent/benchmark/*.py`, `src/mcp_server/server.py`, `src/mcp_server/tools/*.py`, `src/mcp_server/agent_client/client.py`, `src/langchain_agent/backend/*.py`, `src/langchain_agent/core/orchestrator.py`, `src/langchain_agent/tools/mcp_adapter.py`, `src/langchain_agent/workflows/*.py`, `webui-v2/src/app/page.tsx`, `webui-v2/src/components/chat/*.tsx`, `webui-v2/src/components/reports/*.tsx`, `webui-v2/src/lib/*.ts`
- Files allowed to edit: `thesis_workspace/chapters/04_detailed_design_and_implementation.md`, `thesis_workspace/plan/progress.md`
- Required skills: writing-chapters, writing-core
- Evidence/data inputs: Perfa source code, previous architecture chapters
- Required artifacts: 第四章初稿，关键模块表，报告生成流程说明
- Rejection checks: 不写成源码注释翻译；不写未实现 RAG 为已实现；不夸大安全能力；每个模块必须说明输入、处理、输出和设计理由
- Validation commands: `wc -m thesis_workspace/chapters/04_detailed_design_and_implementation.md`; `rg '首先|其次|最后|此外|另外|接下来|总之|值得注意的是|需要指出的是|显而易见|我认为|我觉得' thesis_workspace/chapters/04_detailed_design_and_implementation.md`
