# Task Packet

- Scope: 写作第五章系统测试与结果分析，必须基于真实测试输出或明确标记未运行项。
- Files to read: `thesis_workspace/plan/experiment-protocol.md`, `test/node_agent_test.md`, `test/e2e_prompts/README.md`, `test/**/*.py`, `ops/scripts/status-all.sh`
- Files allowed to edit: `thesis_workspace/chapters/05_testing_and_results.md`, `thesis_workspace/plan/progress.md`, `thesis_workspace/plan/review/method-experiment-traceability.md`
- Required skills: experiment-results-planning, writing-chapters, writing-core
- Evidence/data inputs: test command outputs, status scripts, test docs
- Required artifacts: 第五章初稿、测试结果表、限制说明
- Rejection checks: 不得编造通过结果；不得使用 mock 数据；未运行项必须说明原因；不得把测试计划写成测试结果
- Validation commands: `wc -m thesis_workspace/chapters/05_testing_and_results.md`; `rg '待真实实验替换|PLANNING DATA|首先|其次|最后|此外|另外|总之|值得注意的是|需要指出的是|显而易见|我认为|我觉得' thesis_workspace/chapters/05_testing_and_results.md`
