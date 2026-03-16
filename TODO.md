# Perfa 开发 TODO

## 已完成 ✅

### Node Agent (5,567 行)
- [x] HTTP API 服务器
- [x] Benchmark 执行器 (fio, superpi, unixbench, stream, mlc, hping3)
- [x] 监控采集器 (CPU/内存/磁盘/网络)
- [x] 工具管理 (安装/卸载/验证)
- [x] 结果存储 (SQLite)

### MCP Server (2,722 行)
- [x] SSE 传输协议
- [x] 服务器管理工具 (5个)
- [x] Agent 管理工具 (5个)
- [x] 工具管理工具 (4个)
- [x] Benchmark 工具 (5个)
- [x] 智能分析工具 (generate_report)

---

## 待开发 🚧

### LangChain Agent (~2,500 行) - 核心

#### Phase 1: 基础框架 (~800 行)
- [ ] Agent 核心类 (ReAct / Plan-and-Execute 模式)
- [ ] MCP Tools → LangChain Tools 封装 (20个工具)
- [ ] Prompt 工程设计
- [ ] 对话记忆管理
- [ ] CLI 交互入口

#### Phase 2: 智能决策 (~700 行)
- [ ] 意图识别与工具选择
- [ ] 智能 Planning (任务拆解)
- [ ] 工具链编排 (自动选择最优组合)
- [ ] 错误处理与重试机制

#### Phase 3: 高级能力 (~600 行)
- [ ] 多 Agent 协作 (调度Agent + 分析Agent + 报告Agent)
- [ ] 自动诊断推理 (性能瓶颈分析)
- [ ] 自然语言报告生成
- [ ] 结果解析与结构化输出

#### Phase 4: 集成优化 (~400 行)
- [ ] Web 界面 (可选)
- [ ] 性能优化
- [ ] 文档完善

---

## 可选扩展功能

### 监控告警
- [ ] `set_alert_rule` - 设置告警规则
- [ ] `list_alerts` - 告警历史
- [ ] 告警推送 (微信/钉钉)

### 压测调度
- [ ] `schedule_benchmark` - 定时压测
- [ ] `batch_benchmark` - 批量压测
- [ ] `compare_results` - 跨服务器对比

### 报告增强
- [ ] `export_report_pdf` - PDF 导出
- [ ] `baseline_management` - 性能基线
- [ ] `trend_analysis` - 趋势分析

---

## 目标架构

```
用户自然语言输入
       ↓
┌─────────────────────────────┐
│     LangChain Agent         │  ← 核心决策层
│  ┌─────────────────────┐   │
│  │ 意图识别 + Planning  │   │
│  │ 工具编排 + 推理分析  │   │
│  └─────────────────────┘   │
└──────────┬──────────────────┘
           ↓
┌─────────────────────────────┐
│       MCP Server            │  ← 协议适配层
│    (20+ Tools)              │
└──────────┬──────────────────┘
           ↓
┌─────────────────────────────┐
│      Node Agent             │  ← 执行层
│  Benchmark + Monitor        │
└─────────────────────────────┘
```

---

## 行数目标

| 模块 | 当前 | 目标 | 占比 |
|------|------|------|------|
| Node Agent | 5,567 | 5,567 | 45% |
| MCP Server | 2,722 | 2,722 | 22% |
| **LangChain Agent** | **0** | **~2,500** | **20%** |
| 其他 | - | ~1,500 | 13% |
| **总计** | **8,289** | **~12,300** | |

---

## 明日计划

1. 设计 LangChain Agent 目录结构
2. 实现 MCP Tools → LangChain Tools 封装
3. 完成 Agent 核心类 (ReAct 模式)
4. 实现 CLI 交互入口
5. 基础对话测试

---

*最后更新: 2026-03-16*
