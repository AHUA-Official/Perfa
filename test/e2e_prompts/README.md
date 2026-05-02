# Prompt-First E2E

这套目录不是断言式单元测试，而是“场景 prompt 驱动”的端到端验证工具。

## 目标

1. 先定义功能/场景级 prompt
2. 每个 prompt 对应一个独立脚本
3. 脚本打印：
   - prompt
   - SSE metadata 事件
   - workflow 信息
   - 最终回答
   - session detail
   - trace_id / jaeger_url
4. 第二阶段调用评审 AI 做初审
5. 生成给人类看的精简摘要页
6. 最终是否通过，不由脚本硬编码断言，而是由 AI + 人类阅读上下文后确认

## 文件

- `cases.json`
  - 场景清单
- `runner.py`
  - 共享执行器
- `ai_judge.py`
  - 第二阶段 AI 初审
- `run_*.py`
  - 单场景入口
- `run_all.py`
  - 批量跑所有场景
- `reports/*.md`
  - 生成人类摘要页

## 运行

单个场景：

```bash
python3 test/e2e_prompts/run_cpu_focus_basic.py
python3 test/e2e_prompts/run_storage_focus_basic.py
python3 test/e2e_prompts/run_network_focus_basic.py
python3 test/e2e_prompts/run_full_assessment_server.py
python3 test/e2e_prompts/run_multi_turn_followup.py
```

批量运行：

```bash
python3 test/e2e_prompts/run_all.py
```

指定后端：

```bash
python3 test/e2e_prompts/runner.py --host 127.0.0.1 --port 10000 --case-id cpu_focus_basic
```

## 判定方式

输出末尾会明确打印：

- `MANUAL_RESULT: REVIEW_REQUIRED`
- `MANUAL_GUIDE: ...`

也就是：

1. 看最终回答是否符合场景
2. 看 workflow / metadata events 是否符合预期
3. 看 session detail 是否保留了正确上下文
4. 如有 trace_id / jaeger_url，可继续去看 Jaeger

这套工具的目的不是替代人工判断，而是把“足够判断”的上下文一次性打全。

## AI 初审

执行成功时，runner 会：

1. 收集 execution context
2. 调用 `ai_judge.py`
3. `ai_judge.py` 读取 `src/langchain_agent/.env` 中的：
   - `ZHIPU_API_KEY`
   - `ZHIPU_MODEL`
   - `ZHIPU_BASE_URL`
4. 输出 `PASS / FAIL / UNSURE`

如果你已经把 key 配在 `src/langchain_agent/.env`，这层会直接复用，不需要再单独加一套测试配置。
