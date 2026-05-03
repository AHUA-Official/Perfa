# 第一章绪论段落蓝图

## Paragraph 1

- Role: context
- Main claim: 服务器性能测试是保障服务稳定性、容量规划和故障定位的基础环节。
- Evidence IDs: E01
- Contrast or transition: 从性能测试的重要性过渡到传统流程的操作成本。
- Forbidden content: 不写具体实验结果。

## Paragraph 2

- Role: problem condition
- Main claim: 现代系统由多组件、多机器和多语言服务构成，单点测试结果难以解释完整性能问题。
- Evidence IDs: E02
- Contrast or transition: 引出监控和可观测性。
- Forbidden content: 不夸大 Perfa 已具备所有分布式追踪能力。

## Paragraph 3

- Role: technology landscape
- Main claim: Prometheus 和 OpenTelemetry 等技术使性能数据采集、时间序列存储和链路观测成为工程实践的重要支撑。
- Evidence IDs: E03, E04, E12
- Contrast or transition: 说明仅有监控仍不足以降低测试操作复杂度。
- Forbidden content: 不把官方文档写成论文创新。

## Paragraph 4

- Role: method landscape
- Main claim: 大语言模型为自然语言交互和任务分解提供了新的可能，但模型自身不能替代真实系统操作。
- Evidence IDs: E05, E06
- Contrast or transition: 引出工具调用和 Agent 路线。
- Forbidden content: 不写“大模型完全理解系统”之类绝对化表述。

## Paragraph 5

- Role: method gap
- Main claim: ReAct 和 Toolformer 等研究说明模型可以通过推理与动作交替、外部 API 调用等方式扩展能力边界。
- Evidence IDs: E07, E08
- Contrast or transition: 引出 MCP 标准化工具协议。
- Forbidden content: 不声称 Perfa 实现了 Toolformer 训练方法。

## Paragraph 6

- Role: protocol route
- Main claim: MCP 提供了连接 AI 应用与外部工具、数据源的标准化机制，适合作为性能测试能力封装层。
- Evidence IDs: E09, E10
- Contrast or transition: 过渡到 Perfa 的总体设计。
- Forbidden content: 不写 MCP 已解决所有安全问题。

## Paragraph 7

- Role: project position
- Main claim: Perfa 将 Web 交互、LLM 编排、MCP 工具封装和节点执行结合，形成自然语言驱动的服务器性能测试平台。
- Evidence IDs: Project codeknowledge
- Contrast or transition: 展开本文研究内容。
- Forbidden content: 不写未经验证的商业价值。

## Paragraph 8

- Role: contribution
- Main claim: 本文主要工作包括架构设计、核心模块实现、工具调用链路和测试验证。
- Evidence IDs: Project codeknowledge
- Contrast or transition: 引出论文结构。
- Forbidden content: 不列过多贡献点，不写算法创新。

## Paragraph 9

- Role: organization
- Main claim: 概述各章安排。
- Evidence IDs: outline
- Contrast or transition: 结束第一章。
- Forbidden content: 不写冗长章节说明。
