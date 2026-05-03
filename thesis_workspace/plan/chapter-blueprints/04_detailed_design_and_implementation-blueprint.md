# 第四章详细设计与实现蓝图

## 章节目标

第四章是全文工作量核心，需要结合源码说明 Perfa 的关键模块如何实现。写作方式按“输入对象 -> 处理流程 -> 输出结果 -> 设计理由”展开，避免文件清单式罗列。

## 小节安排

### 4.1 Node Agent 执行端设计与实现

- 说明启动流程、监控采集、工具管理、BenchmarkExecutor、结果和日志保存。
- 源码依据：`src/node_agent/main.py`, `api/routes/*`, `monitor/*`, `tool/manager.py`, `benchmark/*`

### 4.2 MCP Server 能力封装层设计与实现

- 说明工具注册、API Key、SSE、SQLite、AgentClient、Benchmark Tool 和 Agent 生命周期 Tool。
- 源码依据：`src/mcp_server/server.py`, `tools/*.py`, `agent_client/client.py`, `storage/database.py`

### 4.3 LangChain Agent 智能编排层设计与实现

- 说明 FastAPI、OpenAI 兼容接口、MCPToolAdapter、场景路由、WorkflowEngine、ReportStore。
- 源码依据：`src/langchain_agent/backend/*`, `core/orchestrator.py`, `tools/mcp_adapter.py`, `workflows/*`

### 4.4 WebUI V2 交互层设计与实现

- 说明页面结构、流式对话、服务器选择、报告页面、前端 API 封装。
- 源码依据：`webui-v2/src/app/page.tsx`, `components/chat/*`, `components/reports/*`, `lib/api.ts`, `lib/sse.ts`

### 4.5 报告生成与知识增强设计

- 说明已实现的结构化报告、LLM 降级报告、报告持久化和前端证据回溯。
- 明确 ChromaDB/RAG 属于预留扩展，不写成已完整实现。

### 4.6 本章小结

- 承接第五章测试。
