# 摘  要

服务器性能测试是系统上线验收、硬件资源评估和容量规划中的重要环节。传统测试流程通常依赖多种命令行工具，存在工具安装分散、参数配置复杂、测试过程难以追踪和报告整理依赖人工等问题。针对上述问题，本文设计并实现了一套名为 Perfa 的服务器性能测试平台，将大语言模型的自然语言交互能力与模型上下文协议（Model Context Protocol，MCP）的工具调用机制结合，用于降低单服务器性能测试的操作门槛。

系统采用交互层、智能编排层、能力封装层和节点执行层四层架构。交互层提供对话、服务器管理、报告和运行监控页面；智能编排层负责自然语言理解、场景路由和测试工作流执行；能力封装层基于 MCP 将服务器管理、测试工具管理、Benchmark 任务和报告生成封装为标准工具；节点执行层运行在被测服务器上，完成指标采集、测试工具管理、Benchmark 执行和结果保存。

项目重点实现了节点执行端、MCP 能力封装、智能工作流、流式交互和报告归档模块。报告模块在生成自然语言分析的同时保留原始 Benchmark 结果、任务标识和工具调用记录，使测试结论能够回溯到执行证据。本文通过模块测试、接口检查和运行状态验证对系统进行评估。测试结果表明，Perfa 能够完成服务器注册、工具管理、Benchmark 执行、报告归档和页面交互等主要流程，验证了自然语言驱动的服务器性能测试平台在毕业设计场景下的可用性，并为后续扩展多节点调度和报告分析能力提供了工程基础。

关键词：服务器性能测试；大语言模型；MCP；智能运维；运行监控

# ABSTRACT

Server performance testing is an important task in system acceptance, hardware resource evaluation, and capacity planning. Traditional testing workflows usually rely on multiple command-line tools, which leads to scattered tool installation, complex parameter configuration, weak process traceability, and labor-intensive report preparation. To address these problems, this thesis designs and implements Perfa, a server performance testing platform that combines the natural language interaction capability of large language models with the tool invocation mechanism of the Model Context Protocol (MCP). The platform is intended to reduce the operational complexity of single-server performance testing.

The system adopts a four-layer architecture consisting of an interaction layer, an intelligent orchestration layer, a capability encapsulation layer, and a node execution layer. The interaction layer provides conversation, server management, report, and runtime monitoring pages. The intelligent orchestration layer handles natural language understanding, scenario routing, and testing workflow execution. The capability encapsulation layer uses MCP to expose server management, testing tool management, benchmark tasks, and report generation as standard tools. The node execution layer runs on the target server and performs metric collection, testing tool management, benchmark execution, and result persistence.

The project implements the node execution module, MCP-based capability encapsulation, intelligent workflow, streaming interaction, and report archiving. While generating natural language analysis, the report module preserves raw benchmark results, task identifiers, and tool invocation records, so that conclusions can be traced back to execution evidence. Module tests, interface checks, and runtime status verification are conducted to evaluate the system. The results show that Perfa can complete the main workflows of server registration, tool management, benchmark execution, report archiving, and page interaction, which verifies the usability of a natural-language-driven server performance testing platform in the graduation design scenario and provides an engineering basis for future multi-node scheduling and report analysis.

Keywords: server performance testing; large language model; MCP; intelligent operations; runtime monitoring
