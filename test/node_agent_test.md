# Node Agent 测试文档

本文档描述 Node Agent 各模块的功能测试方法。

---

## 一、环境准备

### 1.1 启动服务

```bash
bash /home/ubuntu/Perfa/ops/scripts/start-point.sh
```

确认以下服务正常运行：
- Victoria Metrics (端口 8428)
- Grafana (端口 3000)
- Node Agent (端口 8080)
- Prometheus Metrics (端口 8000)

### 1.2 验证服务状态

```bash
# 健康检查
curl http://localhost:8080/health

# 查看服务状态
curl http://localhost:8080/api/status
```

### 1.3 运行 API 测试脚本

测试脚本位于 `test/node_agent/` 目录下，按模块分为四个独立脚本：

```
test/
├── node_agent/
│   ├── run_all.py        # 运行所有模块测试
│   ├── test_monitor.py   # 监控模块测试
│   ├── test_tool.py      # 工具管理模块测试
│   ├── test_benchmark.py # 压测执行模块测试
│   └── test_storage.py   # 存储管理模块测试
├── apitest.py            # 综合测试脚本
├── api_test.sh           # Shell 测试脚本
└── node_agent_test.md    # 本文档
```

#### 运行所有测试

```bash
cd /home/ubuntu/Perfa/test/node_agent

# 运行所有模块测试
python3 run_all.py

# 快速测试（跳过长时间测试）
python3 run_all.py --quick

# 指定服务地址
python3 run_all.py --host 192.168.1.100 --port 8080
```

#### 运行单个模块测试

```bash
# 监控模块测试（健康检查、系统信息、监控启停）
python3 test_monitor.py

# 工具管理模块测试（工具列表、安装/卸载）
python3 test_tool.py

# 压测执行模块测试（任务执行、控制、结果查询）
python3 test_benchmark.py            # 完整测试
python3 test_benchmark.py --quick    # 快速测试

# 存储管理模块测试（存储查询、日志管理、配置）
python3 test_storage.py
```

#### 测试输出说明

测试脚本提供详细的日志输出，包括：

- **[INFO]** 测试步骤说明
- **[DATA]** 实际数据展示
- **[PASS]** 测试通过
- **[FAIL]** 测试失败（包含失败原因）
- **[WARN]** 警告信息

每个测试会验证：
1. HTTP 状态码是否正确
2. 响应数据格式是否正确
3. 业务逻辑是否正确（如工具安装后状态是否变为 `installed`）

---

## 二、Monitor 模块测试

### 2.1 系统信息采集

**测试目标**：验证系统能正确采集静态信息（hostname、CPU 型号、内存大小等）

**测试步骤**：
1. 访问 `/api/system/info`
2. 检查返回的字段是否完整

**预期结果**：
- 返回 `hostname`、`os`、`arch`、`cpu_model`、`cpu_cores`、`memory_total_gb`、`kernel`、`machine_id`
- 各字段值非空且合理

**测试命令**：
```bash
curl http://localhost:8080/api/system/info | jq
```

### 2.2 系统实时状态

**测试目标**：验证能采集实时系统状态

**测试步骤**：
1. 访问 `/api/system/status`
2. 运行一些负载（如 `stress` 命令）
3. 再次访问观察 CPU、内存变化

**预期结果**：
- 返回 CPU 使用率、内存使用率、磁盘使用率、网络统计
- 数值随系统负载变化

**测试命令**：
```bash
curl http://localhost:8080/api/system/status | jq
```

### 2.3 监控启停

**测试目标**：验证监控服务的启动和停止功能

**测试步骤**：
1. 启动监控：POST `/api/monitor/start`
2. 查询状态：GET `/api/monitor/status`
3. 停止监控：POST `/api/monitor/stop`
4. 再次查询状态

**预期结果**：
- 启动后状态为 `running: true`
- 停止后状态为 `running: false`

**测试命令**：
```bash
# 启动监控
curl -X POST http://localhost:8080/api/monitor/start \
  -H "Content-Type: application/json" \
  -d '{"interval": 5}'

# 查询状态
curl http://localhost:8080/api/monitor/status | jq

# 停止监控
curl -X POST http://localhost:8080/api/monitor/stop

# 再次查询
curl http://localhost:8080/api/monitor/status | jq
```

### 2.4 Prometheus 指标暴露

**测试目标**：验证 Prometheus 指标正确暴露

**测试步骤**：
1. 访问 `http://localhost:8000/metrics`
2. 检查指标格式和内容

**预期结果**：
- 返回 Prometheus 格式的指标
- 包含 `node_cpu_percent`、`node_memory_percent` 等指标

**测试命令**：
```bash
curl http://localhost:8000/metrics | grep node_
```

### 2.5 Grafana 可视化

**测试目标**：验证 Grafana 能正确展示监控数据

**测试步骤**：
1. 打开 Grafana：http://localhost:3000
2. 登录（admin/admin123）
3. 查看 Node Agent Dashboard

**预期结果**：
- Dashboard 正确显示 CPU、内存、磁盘、网络图表
- 数据实时更新

---

## 三、Tool 模块测试

### 3.1 查看工具列表

**测试目标**：验证能列出所有支持的测试工具

**测试步骤**：
1. 访问 `/api/tools`

**预期结果**：
- 返回 6 个工具：stream、unixbench、superpi、mlc、fio、hping3
- 每个工具包含 name、category、status 字段

**测试命令**：
```bash
curl http://localhost:8080/api/tools | jq
```

### 3.2 查询工具状态

**测试目标**：验证能查询单个工具的状态

**测试步骤**：
1. 查询 stream 工具：`/api/tools/stream`
2. 查询不存在的工具：`/api/tools/notexist`

**预期结果**：
- stream 工具返回正确的状态信息
- 不存在的工具返回错误

**测试命令**：
```bash
curl http://localhost:8080/api/tools/stream | jq
curl http://localhost:8080/api/tools/notexist | jq
```

### 3.3 工具安装

**测试目标**：验证工具安装功能

**测试步骤**：
1. 选择一个未安装的工具（如 fio）
2. 发送安装请求：POST `/api/tools/fio/install`
3. 查询工具状态确认安装成功

**预期结果**：
- 安装请求返回成功
- 工具状态变为 `installed`

**测试命令**：
```bash
# 安装 fio
curl -X POST http://localhost:8080/api/tools/fio/install | jq

# 查询状态
curl http://localhost:8080/api/tools/fio | jq
```

### 3.4 工具卸载

**测试目标**：验证工具卸载功能

**测试步骤**：
1. 卸载已安装的工具：POST `/api/tools/fio/uninstall`
2. 查询工具状态确认卸载成功

**预期结果**：
- 卸载请求返回成功
- 工具状态变为 `not_installed`

**测试命令**：
```bash
curl -X POST http://localhost:8080/api/tools/fio/uninstall | jq
curl http://localhost:8080/api/tools/fio | jq
```

---

## 四、Benchmark 模块测试

### 4.1 同步执行测试（STREAM）

**测试目标**：验证短时间测试能同步返回结果

**测试步骤**：
1. 确保 stream 工具已安装
2. 执行 STREAM 测试
3. 等待结果返回

**预期结果**：
- 返回 `status: "completed"`
- 包含测试结果（copy_rate、scale_rate、add_rate、triad_rate）

**测试命令**：
```bash
# 先安装 stream
curl -X POST http://localhost:8080/api/tools/stream/install

# 执行测试
curl -X POST http://localhost:8080/api/benchmark/run \
  -H "Content-Type: application/json" \
  -d '{"test_name": "stream", "params": {"array_size": 10000000}}' | jq
```

### 4.2 异步执行测试（UnixBench）

**测试目标**：验证长时间测试能异步执行

**测试步骤**：
1. 确保 unixbench 工具已安装
2. 执行 UnixBench 测试
3. 立即返回 task_id，状态为 running
4. 轮询查询任务状态直到完成

**预期结果**：
- 立即返回 `status: "running"` 和 `task_id`
- 通过 task_id 可查询进度
- 最终状态变为 completed

**测试命令**：
```bash
# 安装 unixbench
curl -X POST http://localhost:8080/api/tools/unixbench/install

# 执行测试
curl -X POST http://localhost:8080/api/benchmark/run \
  -H "Content-Type: application/json" \
  -d '{"test_name": "unixbench"}' | jq

# 记录返回的 task_id，轮询查询状态
TASK_ID="返回的task_id"
curl http://localhost:8080/api/benchmark/tasks/$TASK_ID | jq
```

### 4.3 任务取消

**测试目标**：验证能取消正在运行的任务

**测试步骤**：
1. 启动一个长时间测试（如 unixbench）
2. 在运行中发送取消请求
3. 查询任务状态

**预期结果**：
- 取消成功
- 任务状态变为 `cancelled`

**测试命令**：
```bash
# 取消任务
curl -X POST http://localhost:8080/api/benchmark/cancel \
  -H "Content-Type: application/json" \
  -d '{"task_id": "your_task_id"}' | jq
```

### 4.4 任务暂停与恢复

**测试目标**：验证任务的暂停和恢复功能

**测试步骤**：
1. 启动一个长时间测试
2. 发送暂停请求
3. 查询状态确认已暂停
4. 发送恢复请求
5. 查询状态确认已恢复运行

**预期结果**：
- 暂停后状态为 `paused`
- 恢复后状态为 `running`

**测试命令**：
```bash
# 暂停
curl -X POST http://localhost:8080/api/benchmark/pause \
  -H "Content-Type: application/json" \
  -d '{"task_id": "your_task_id"}' | jq

# 恢复
curl -X POST http://localhost:8080/api/benchmark/resume \
  -H "Content-Type: application/json" \
  -d '{"task_id": "your_task_id"}' | jq
```

### 4.5 查询历史结果

**测试目标**：验证历史结果存储和查询功能

**测试步骤**：
1. 执行几次测试
2. 查询结果列表
3. 查询单个结果详情

**预期结果**：
- 结果列表包含所有历史测试
- 单个结果包含完整信息

**测试命令**：
```bash
# 列出结果
curl http://localhost:8080/api/benchmark/results | jq

# 查询单个结果
curl http://localhost:8080/api/benchmark/results/your_task_id | jq
```

### 4.6 并发限制测试

**测试目标**：验证同一时刻只能运行一个任务

**测试步骤**：
1. 启动一个长时间测试（task1）
2. 在 task1 运行期间尝试启动另一个测试（task2）

**预期结果**：
- 第二个请求返回错误，错误码为 `TASK_RUNNING`
- 提示已有任务在运行

**测试命令**：
```bash
# 启动第一个测试
curl -X POST http://localhost:8080/api/benchmark/run \
  -H "Content-Type: application/json" \
  -d '{"test_name": "unixbench"}'

# 立即尝试启动第二个测试
curl -X POST http://localhost:8080/api/benchmark/run \
  -H "Content-Type: application/json" \
  -d '{"test_name": "stream"}' | jq
```

---

## 五、API 模块测试

### 5.1 错误响应格式

**测试目标**：验证错误响应格式一致

**测试步骤**：
1. 发送无效请求
2. 检查响应格式

**预期结果**：
- 返回格式为 `{"success": false, "error": {"code": "...", "message": "..."}}`

**测试命令**：
```bash
# 不存在的工具
curl http://localhost:8080/api/tools/notexist | jq

# 无效参数
curl -X POST http://localhost:8080/api/benchmark/run \
  -H "Content-Type: application/json" \
  -d '{}' | jq
```

### 5.2 存储管理

**测试目标**：验证存储使用情况查询和清理功能

**测试步骤**：
1. 查询存储使用情况
2. 清理存储
3. 再次查询确认清理成功

**测试命令**：
```bash
# 查询存储使用情况
curl http://localhost:8080/api/storage/usage | jq

# 列出日志文件
curl http://localhost:8080/api/storage/logs | jq

# 清理存储
curl -X POST http://localhost:8080/api/storage/cleanup \
  -H "Content-Type: application/json" \
  -d '{"clean_logs": true, "keep_logs_days": 7}' | jq
```

---

## 六、各工具专项测试

### 6.1 STREAM 测试参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| array_size | 100000000 | 数组大小 |
| ntimes | 10 | 重复次数 |
| nt | 1 | 线程数 |

### 6.2 SuperPi 测试参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| digits | 1000000 | 计算位数 |

### 6.3 FIO 测试参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| size | 1G | 测试数据大小 |
| bs | 4k | 块大小 |
| rw | randread | 读写模式 |
| runtime | 60 | 运行时间（秒） |

### 6.4 UnixBench 测试参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| copies | 自动 | 并行拷贝数 |
| tests | 全部 | 指定测试项 |

---

## 七、API 接口参考

### 7.1 健康检查

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查，返回 `status: "healthy"` 和运行时间 |
| GET | `/api/status` | 获取 Agent 状态，包括 agent_id、monitor_running、current_task |

### 7.2 监控 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/monitor/status` | 获取监控状态 |
| POST | `/api/monitor/start` | 启动监控，参数：`interval`、`enabled_metrics` |
| POST | `/api/monitor/stop` | 停止监控 |
| GET | `/api/system/info` | 获取系统静态信息（hostname、CPU、内存等） |
| GET | `/api/system/status` | 获取系统实时状态（CPU、内存、磁盘、网络） |

### 7.3 工具管理 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/tools` | 列出所有工具，可选参数：`category` |
| GET | `/api/tools/<tool_name>` | 查询工具状态 |
| POST | `/api/tools/<tool_name>/install` | 安装工具 |
| POST | `/api/tools/<tool_name>/uninstall` | 卸载工具 |

### 7.4 Benchmark API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/benchmark/run` | 执行压测，参数：`test_name`、`params` |
| POST | `/api/benchmark/cancel` | 取消任务，参数：`task_id` |
| POST | `/api/benchmark/pause` | 暂停任务，参数：`task_id` |
| POST | `/api/benchmark/resume` | 恢复任务，参数：`task_id` |
| GET | `/api/benchmark/current` | 获取当前运行任务 |
| GET | `/api/benchmark/tasks` | 获取任务列表，可选参数：`limit` |
| GET | `/api/benchmark/tasks/<task_id>` | 查询任务状态 |
| GET | `/api/benchmark/results` | 获取结果列表，可选参数：`test_name`、`limit` |
| GET | `/api/benchmark/results/<task_id>` | 获取单个测试结果 |
| GET | `/api/benchmark/logs/<task_id>` | 获取任务日志路径 |

### 7.5 存储管理 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/storage/usage` | 获取存储使用情况 |
| GET | `/api/storage/logs` | 列出日志文件，可选参数：`limit` |
| GET | `/api/storage/logs/<log_name>` | 读取日志内容，可选参数：`lines` |
| POST | `/api/storage/cleanup` | 清理存储，参数：`clean_logs`、`keep_logs_days`、`clean_working_dir`、`clean_old_results`、`keep_results_days` |

### 7.6 配置管理 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/config` | 获取当前配置 |
| POST | `/api/config` | 更新配置，参数：`collect_interval_sec`、`max_concurrent_tasks`、`enabled_metrics` |

---

## 八、错误码参考

| 错误码 | 说明 | HTTP 状态码 |
|--------|------|-------------|
| `INTERNAL_ERROR` | 内部服务器错误 | 500 |
| `INVALID_PARAMS` | 无效参数 | 400 |
| `NOT_FOUND` | 资源不存在 | 404 |
| `TASK_RUNNING` | 已有任务在运行 | 409 |
| `TASK_NOT_FOUND` | 任务不存在 | 404 |
| `TASK_NOT_RUNNING` | 任务未运行 | 400 |
| `TASK_CANNOT_CANCEL` | 无法取消任务 | 400 |
| `TOOL_NOT_INSTALLED` | 工具未安装 | 400 |
| `TOOL_INSTALL_FAILED` | 工具安装失败 | 500 |
| `TOOL_NOT_FOUND` | 工具不存在 | 404 |
| `MONITOR_ALREADY_RUNNING` | 监控已在运行 | 409 |
| `MONITOR_NOT_RUNNING` | 监控未运行 | 400 |

---

## 九、响应格式

### 成功响应

```json
{
  "success": true,
  "message": "操作成功",
  "data": { ... }
}
```

### 错误响应

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "错误描述",
    "details": { ... }
  }
}
```

---

## 十、清理测试环境

```bash
bash /home/ubuntu/Perfa/ops/scripts/stop-point.sh
```
