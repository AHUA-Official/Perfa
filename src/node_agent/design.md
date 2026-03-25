# Node Agent 设计文档

## 概述

Node Agent 是运行在被测节点上的守护进程，负责监控系统资源、管理压力测试工具、执行压测任务并提供 API 接口。

## 核心模块

| 模块 | 职责 |
|------|------|
| `monitor` | 采集 CPU、内存、磁盘、网络等系统资源指标 |
| `tool` | 管理压力测试工具的生命周期（安装、检查、卸载） |
| `benchmark` | 执行压测任务、收集结果、清理现场 |
| `api` | 提供 HTTP API 接口 |

---

## 架构设计

```
┌─────────────────────────────────────────────────────────┐
│                      Node Agent                          │
├─────────────────────────────────────────────────────────┤
│  Main Thread                                             │
│  ├── HTTP API Server (Flask, port 8080)                 │
│  └── ToolManager (工具生命周期管理)                      │
├─────────────────────────────────────────────────────────┤
│  Monitor Thread                                          │
│  └── 定时采集系统指标 → Prometheus Metrics              │
├─────────────────────────────────────────────────────────┤
│  Task Thread (按需创建)                                  │
│  └── 执行压测任务 → SQLite 存储                         │
└─────────────────────────────────────────────────────────┘
```

## 数据流

```
监控指标 → Prometheus Metrics → Victoria Metrics → Grafana
任务结果 → SQLite 数据库
日志文件 → /tmp/agent.log
```

---

## Monitor 模块

### 功能

定时采集系统资源指标，通过 Prometheus 格式暴露。

### 采集指标

| 类别 | 指标 |
|------|------|
| CPU | 使用率、核心数、频率 |
| 内存 | 总量、已用、可用、Swap |
| 磁盘 | 总量、已用、IO 统计 |
| 网络 | 发送/接收字节、连接数 |

---

## Tool 模块

### 功能

管理压力测试工具的完整生命周期：检查、安装、卸载。

### 支持的工具

| 工具 | 类别 | 安装方式 |
|------|------|----------|
| UnixBench | CPU | 源码编译 |
| SuperPi | CPU | 源码编译 |
| STREAM | 内存 | 源码编译 |
| MLC | 内存 | 预编译二进制 |
| FIO | 磁盘 | 系统包管理器 |
| hping3 | 网络 | 系统包管理器 |

### 工具状态

| 状态 | 说明 |
|------|------|
| `not_installed` | 未安装 |
| `installed` | 已安装 |
| `available` | 系统可用 |
| `error` | 错误 |

### 目录结构

```
tool/
├── sources/           # 源码和压缩包
│   ├── cpu/          # CPU 测试工具
│   ├── disk/         # 磁盘测试工具
│   ├── mem/          # 内存测试工具
│   └── net/          # 网络测试工具
├── binaries/          # 编译后的二进制文件
├── base.py           # 工具基类
├── manager.py        # 工具管理器
└── *_tools.py       # 各类工具实现
```

---

## Benchmark 模块

### 设计原则

1. **串行执行**: 同一时刻只运行一个压测任务
2. **异步支持**: 长时间任务异步执行
3. **自动清理**: 测试前后清理临时文件和进程
4. **结果持久化**: 结果存储到 SQLite

### 任务状态

| 状态 | 说明 |
|------|------|
| `pending` | 等待执行 |
| `preparing` | 准备中 |
| `running` | 执行中 |
| `paused` | 已暂停 |
| `collecting` | 采集结果 |
| `cleaning` | 清理现场 |
| `completed` | 已完成 |
| `failed` | 失败 |
| `cancelled` | 已取消 |

### 执行策略

| 工具 | 典型耗时 | 执行方式 |
|------|----------|----------|
| STREAM | 1-5 分钟 | 同步 |
| SuperPi | 1-10 分钟 | 异步 |
| UnixBench | 30-60 分钟 | 异步 |
| MLC | 5-30 分钟 | 异步 |
| FIO | 可配置 | 异步 |
| hping3 | 可配置 | 异步 |

### Runner 设计

每个工具对应一个 Runner，负责：
- 准备测试环境
- 构建执行命令
- 解析测试结果
- 定义清理规则

### 数据存储

```
/var/lib/node_agent/
├── benchmark_results.db      # SQLite 结果数据库
└── logs/
    └── {date}_{time}_{test}_{task_id}.log
```

---

## API 模块

### 健康检查

| 路由 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/api/status` | GET | Agent 状态 |

### 监控

| 路由 | 方法 | 说明 |
|------|------|------|
| `/api/monitor/start` | POST | 启动监控 |
| `/api/monitor/stop` | POST | 停止监控 |
| `/api/monitor/status` | GET | 监控状态 |
| `/api/system/info` | GET | 系统静态信息 |
| `/api/system/status` | GET | 系统实时状态 |

### 工具管理

| 路由 | 方法 | 说明 |
|------|------|------|
| `/api/tools` | GET | 列出所有工具 |
| `/api/tools/<name>` | GET | 查询工具状态 |
| `/api/tools/<name>/install` | POST | 安装工具 |
| `/api/tools/<name>/uninstall` | POST | 卸载工具 |

### 压测任务

| 路由 | 方法 | 说明 |
|------|------|------|
| `/api/benchmark/run` | POST | 执行压测 |
| `/api/benchmark/cancel` | POST | 取消任务 |
| `/api/benchmark/pause` | POST | 暂停任务 |
| `/api/benchmark/resume` | POST | 恢复任务 |
| `/api/benchmark/current` | GET | 当前任务 |
| `/api/benchmark/tasks` | GET | 任务列表 |
| `/api/benchmark/tasks/<id>` | GET | 任务状态 |
| `/api/benchmark/results` | GET | 结果列表 |
| `/api/benchmark/results/<id>` | GET | 测试结果 |
| `/api/benchmark/logs/<id>` | GET | 日志路径 |

### 存储

| 路由 | 方法 | 说明 |
|------|------|------|
| `/api/storage/usage` | GET | 存储使用情况 |
| `/api/storage/logs` | GET | 日志文件列表 |
| `/api/storage/logs/<name>` | GET | 读取日志内容 |
| `/api/storage/cleanup` | POST | 清理存储 |

### 配置

| 路由 | 方法 | 说明 |
|------|------|------|
| `/api/config` | GET | 获取配置 |
| `/api/config` | POST | 更新配置 |

### 错误码

| 错误码 | 说明 |
|--------|------|
| `INTERNAL_ERROR` | 内部错误 |
| `INVALID_PARAMS` | 参数无效 |
| `NOT_FOUND` | 资源不存在 |
| `TASK_RUNNING` | 任务已在运行 |
| `TASK_NOT_FOUND` | 任务不存在 |
| `TASK_NOT_RUNNING` | 任务未运行 |
| `TASK_CANNOT_CANCEL` | 无法取消 |
| `TOOL_NOT_INSTALLED` | 工具未安装 |
| `TOOL_INSTALL_FAILED` | 安装失败 |
| `TOOL_NOT_FOUND` | 工具不存在 |
| `MONITOR_ALREADY_RUNNING` | 监控已在运行 |
| `MONITOR_NOT_RUNNING` | 监控未运行 |
