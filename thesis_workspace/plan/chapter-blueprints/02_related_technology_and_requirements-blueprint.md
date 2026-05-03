# 第二章相关技术与需求分析蓝图

## 章节目标

第二章负责承接绪论中的问题背景，将 Perfa 用到的技术基础和系统需求讲清楚。写作重点不是教科书式介绍所有技术，而是说明这些技术为什么被用于 Perfa，以及它们分别支撑了哪些功能需求。

## 小节安排

### 2.1 服务器性能测试技术基础

- Role: technology basis
- Main claim: 服务器性能测试需要覆盖 CPU、内存、磁盘和网络等资源维度，不同工具输出不同指标，需要统一生命周期管理。
- Evidence/source: `src/node_agent/tool/manager.py`, `src/node_agent/benchmark/executor.py`
- Transition: 由底层测试工具过渡到测试过程监控。
- Forbidden content: 不写成工具说明书，不堆砌命令参数。

### 2.2 监控与可观测性技术

- Role: technology basis
- Main claim: 测试任务需要结合运行时指标和日志才能解释结果。
- Evidence/source: `src/node_agent/main.py`, Prometheus/OpenTelemetry refs, `codeknowledge/03-operations/runtime-and-ports.md`
- Transition: 由指标采集过渡到工具能力封装。
- Forbidden content: 不声称完整分布式追踪已覆盖所有链路。

### 2.3 MCP 工具协议与能力封装

- Role: protocol basis
- Main claim: MCP 用于将服务器管理、工具管理、压测和报告生成封装为上层可调用工具。
- Evidence/source: `src/mcp_server/server.py`, `src/langchain_agent/tools/mcp_adapter.py`
- Transition: 引出 LangChain Agent 编排。
- Forbidden content: 不把 MCP 写成压测执行引擎。

### 2.4 大语言模型 Agent 与工作流编排

- Role: orchestration basis
- Main claim: Agent 层负责意图识别、场景路由、工具调用和报告总结。
- Evidence/source: `src/langchain_agent/backend/main.py`, `src/langchain_agent/workflows/router.py`, `src/langchain_agent/workflows/nodes.py`
- Transition: 引出前端交互。
- Forbidden content: 不声称模型自动保证结果正确。

### 2.5 Web 前端与交互技术

- Role: interface basis
- Main claim: WebUI V2 用于承载对话、服务器、报告和监控页面，降低系统使用门槛。
- Evidence/source: `webui-v2/package.json`, `webui-v2/src/app/page.tsx`, `webui-v2/src/lib/api.ts`
- Transition: 转向需求分析。
- Forbidden content: 不写过多前端框架宣传语。

### 2.6 系统功能需求分析

- Role: requirements
- Main claim: Perfa 至少需要支持服务器管理、Agent 部署、工具管理、压测任务、报告生成、监控展示和会话管理。
- Evidence/source: code modules and web pages
- Transition: 非功能需求。
- Forbidden content: 不写尚未实现的功能为已完成。

### 2.7 系统非功能需求分析

- Role: requirements
- Main claim: 系统需要满足可扩展性、可维护性、可观测性、安全边界和可用性要求。
- Evidence/source: project architecture and implementation
- Transition: 本章小结。
- Forbidden content: 不夸大安全性。

### 2.8 本章小结

- Role: summary
- Main claim: 本章为第三章总体设计提供需求与技术依据。
