# 论文图表绘制提示词

## 图 3-1 系统总体架构图

绘制一个学术论文级别的系统架构图，展示“基于大语言模型与 MCP 的服务器性能测试平台总体架构”。采用从上到下布局，白色背景，简约学术风格，450 DPI。图中包含用户浏览器、WebUI V2、LangChain Agent、MCP Server、Node Agent、Benchmark Tools、VictoriaMetrics、Grafana、ReportStore。WebUI V2 到 LangChain Agent 使用 HTTP/SSE 箭头，LangChain Agent 到 MCP Server 使用 MCPToolAdapter 箭头，MCP Server 到 Node Agent 使用 HTTP AgentClient 箭头，Node Agent 到 VictoriaMetrics 使用 metrics 箭头，VictoriaMetrics 到 Grafana 使用查询/展示箭头，ReportStore 回到 WebUI V2 展示报告。交互层用蓝色，编排层用橙色，能力封装层用绿色，执行层用灰蓝色，监控和报告存储用浅灰色。

## 图 3-2 自然语言测试请求处理流程图

绘制一个学术论文级别的流程图，展示“自然语言测试请求处理流程”。从左到右布局，步骤包括用户输入测试需求、WebUI V2 发送流式请求、LangChain Agent 场景路由、判断是否性能测试场景、WorkflowEngine 选择场景图、MCPToolAdapter 调用 MCP Tool、MCP Server 执行 Tool、Node Agent 运行 Benchmark、返回任务状态和结果、生成报告并持久化、WebUI 展示回答和报告。判断节点使用菱形，普通步骤使用圆角矩形，流程箭头清晰。

## 图 3-3 报告生成与证据回溯流程图

绘制一个学术论文级别的流程图，展示“报告生成与证据回溯流程”。输入包括 Benchmark 结果、错误记录、工具调用记录，进入 generate_report 节点，然后判断 MCP 报告工具是否可用。可用时进入 GenerateReportTool，不可用时进入 LLM 辅助生成，两者汇入 AgentOrchestrator，随后保存到 ReportStore，前端 ReportsPage 展示 AI 结论、raw_results、任务 ID、错误记录和 tool_calls。重点突出报告不是单纯文本，而是包含原始证据。

## 图 3-4 本地完整部署拓扑图

绘制一个学术论文级别的部署拓扑图，展示 Perfa 本地完整开发链路。包含 Browser、WebUI V2:3002、LangChain Backend:10000、MCP Server:9000、Node Agent API:8080、Node Agent Metrics:8000、VictoriaMetrics:8428、Grafana:3000、OTel Collector:4317/4318、Jaeger UI:16686。主业务链路从 Browser 到 Node Agent API，监控链路从 Node Agent Metrics 到 VictoriaMetrics 到 Grafana，可观测链路从各服务到 OTel Collector 到 Jaeger。

## 图 4-1 报告生成与知识增强设计边界图

绘制一个学术论文级别的双区域结构图，展示“报告生成与知识增强设计边界”。左侧区域为“已实现链路”，包含 Benchmark 结果、错误记录与工具调用、FurinaBench Markdown 知识库、search_benchmark_knowledge、本地知识片段、generate_report Tool / LLM 报告节点、ReportStore、ReportsPage，ReportsPage 展示 AI 结论、知识依据和原始证据。右侧区域为“扩展预留链路”，包含历史报告、FurinaBench 文档、codeknowledge 文档、Embedding、Vector Store、相似报告/知识片段检索、RAG 增强报告生成。用虚线箭头从已实现 ReportsPage 指向扩展检索模块，表示后续向向量化 RAG 演进，不表示当前已完整实现向量数据库 RAG。
