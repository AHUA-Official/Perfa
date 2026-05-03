# 写作备注

- 用户要求：指导老师要求较高，需要多使用论文写作技能，按章节逐步写。
- 交付策略：优先产出高质量 Markdown 正文，后续再转换为 Word。
- 语言风格：中文工科毕业论文，避免 AI 痕迹，避免正文列表化。
- 证据边界：不能编造文献、不能编造实验数据。
- 时间压力：学校要求 2026-05-06 前完成初稿，需优先形成完整可审稿版本。

## 源码阅读后的写作边界

- 报告生成可以写成“结构化报告生成 + LLM 辅助总结 + 工作流报告持久化 + 原始证据回溯”的组合能力。源码依据包括 `src/mcp_server/tools/report_tools.py`、`src/langchain_agent/workflows/nodes.py`、`src/langchain_agent/core/orchestrator.py`、`src/langchain_agent/backend/report_store.py` 和 `webui-v2/src/components/reports/ReportsPage.tsx`。
- 不应写成“已经完整实现 RAG 报告生成”。当前代码中 `ChromaConfig` 明确标注为未来功能预留，适合写成“预留向量检索与历史测试相似查询扩展接口”。
- 可以把 `codeknowledge/06-deep-dives/` 写成类似 DeepWiki 的项目知识库，用于支撑开发维护、链路追踪和论文材料整理；不应写成运行时自动检索知识库，除非后续补实现。
- 可以把报告导出设计写强一些：系统当前已保存工作流综合报告，包含 AI 结论、原始结果、任务 ID、错误记录、工具调用和 Trace ID；论文中可扩展描述为“为后续 Word/PDF 导出提供结构化数据基础”。
- 第四章应专设“报告生成与知识增强设计”小节，把当前实现、LLM 降级生成、报告持久化、前端报告页、RAG 扩展边界讲清楚，以提高工作量呈现但避免答辩风险。
