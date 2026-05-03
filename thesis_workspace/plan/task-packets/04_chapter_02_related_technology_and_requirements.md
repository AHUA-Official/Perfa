# Task Packet

- Scope: 写作第二章相关技术与需求分析，覆盖技术基础、功能需求和非功能需求。
- Files to read: `thesis_workspace/plan/outline.md`, `thesis_workspace/plan/chapter-blueprints/02_related_technology_and_requirements-blueprint.md`, `src/node_agent/main.py`, `src/node_agent/tool/manager.py`, `src/node_agent/benchmark/executor.py`, `src/mcp_server/server.py`, `src/langchain_agent/backend/main.py`, `src/langchain_agent/workflows/router.py`, `src/langchain_agent/tools/mcp_adapter.py`, `webui-v2/package.json`, `webui-v2/src/app/page.tsx`
- Files allowed to edit: `thesis_workspace/chapters/02_related_technology_and_requirements.md`, `thesis_workspace/plan/progress.md`, `thesis_workspace/refs/references.md`
- Required skills: writing-chapters, writing-core, evidence-driven-writing
- Evidence/data inputs: Perfa source code, project architecture docs, references E03-E12
- Required artifacts: 第二章初稿、需求表内容
- Rejection checks: 不泛泛讲框架；技术介绍必须落到 Perfa 功能；不声称未实现功能已经完成；正文避免列表化
- Validation commands: `wc -m thesis_workspace/chapters/02_related_technology_and_requirements.md`; `rg '首先|其次|最后|此外|另外|接下来|总之|值得注意的是|需要指出的是|显而易见|我认为|我觉得' thesis_workspace/chapters/02_related_technology_and_requirements.md`
