# Task Packet

- Scope: 为第四章准备“报告生成与知识增强设计”材料，强调工作量同时保持源码可追溯。
- Files to read: `src/mcp_server/tools/report_tools.py`, `src/langchain_agent/workflows/nodes.py`, `src/langchain_agent/core/orchestrator.py`, `src/langchain_agent/backend/report_store.py`, `src/langchain_agent/core/config.py`, `webui-v2/src/components/reports/ReportsPage.tsx`, `codeknowledge/06-deep-dives/README.md`
- Files allowed to edit: `thesis_workspace/chapters/04_detailed_design_and_implementation.md`, `thesis_workspace/plan/progress.md`, `thesis_workspace/figures/data-manifest.md`
- Required skills: writing-chapters, writing-core
- Evidence/data inputs: report tool source, workflow report node, report persistence source, WebUI report display source, ChromaDB reserved config, codeknowledge deep dive docs
- Required artifacts: 第四章报告模块小节、报告生成流程图说明、报告数据字段表
- Rejection checks: 不得写成完整 RAG 已上线；不得写成 Word/PDF 导出已实现；必须区分已实现能力和扩展设计
- Validation commands: `rg -n "ChromaConfig|generate_report|ReportStore|ReportsPage" src webui-v2 codeknowledge`
