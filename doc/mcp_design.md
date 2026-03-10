# MCP (Model Context Protocol) 接口设计文档

> **版本**: v3.0  
> **设计者**: Perfa 架构团队  
> **最后更新**: 2026-03-10  
> **目标工具数**: 54  

---

## 一、设计原则与架构概览

### 1.1 核心设计原则

| 原则 | 说明 |
|------|------|
| **单一职责** | 每个工具只做一件事 |
| **Agent自治** | Agent本地采集数据，直写数据库 |
| **静默持久化** | 数据自动入库，AI无需关心存储 |
| **异步友好** | 长耗时任务返回task_id + Logging流 |
| **幂等性** | 唯一ID + 状态机，重复调用安全 |

### 1.2 架构分层

```
┌─────────────────────────────────────────────────┐
│              AI Agent (LLM)                      │
│          调用 Tools / 读取 Resources             │
└────────────────────┬────────────────────────────┘
                     │ MCP Protocol
┌────────────────────┴────────────────────────────┐
│             MCP Server (管理端)                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐        │
│  │  Tools   │ │Resources │ │ Logging  │        │
│  │  (54)    │ │  (5)     │ │  Stream  │        │
│  └─────┬────┘ └─────┬────┘ └─────┬────┘        │
└────────┼──────────────────────────┼─────────────┘
         │                          │
         │ HTTP/gRPC 控制指令        │ WebSocket 日志流
         ↓                          ↑
┌────────────────────────────────────────────────┐
│      Agent 守护进程（部署在被测服务器）          │
│  ┌──────────────────────────────────────┐     │
│  │ 任务执行器                            │     │
│  │  - 安装 PTS/Docker                   │     │
│  │  - 执行压测任务                       │     │
│  │  - 返回结果到MCP Server              │     │
│  └──────────────────────────────────────┘     │
│  ┌──────────────────────────────────────┐     │
│  │ 监控采集器（独立线程）                 │     │
│  │  - psutil 采集 CPU/内存              │     │
│  │  - nvidia-smi 采集 GPU               │     │
│  │  - sensors 采集温度                  │     │
│  │  - **直接写入 InfluxDB**             │     │
│  └──────────────────────────────────────┘     │
└────────────────────────────────────────────────┘
         │                    │
         │ 监控数据            │ 测试结果
         │ (高频，每秒)        │ (低频，测试结束)
         ↓                    ↓
┌────────────────┐    ┌───────────────┐
│   InfluxDB     │    │    SQLite     │
│ (时序数据库)    │    │  (元数据存储)  │
└────────┬───────┘    └───────┬───────┘
         │                    │
         └────────┬───────────┘
                  ↓
         MCP Server 查询数据返回给 AI
```

### 1.3 数据流说明

**控制流**（MCP Server → Agent）：
- AI 调用 MCP Tool（如 `run_benchmark`）
- MCP Server 发送指令给 Agent（HTTP/gRPC）
- Agent 执行任务（安装、压测、配置修改）
- Agent 返回结果给 MCP Server

**数据流**（Agent → 数据库）：
- Agent 监控线程**本地采集**数据（psutil、nvidia-smi）
- Agent **直写 InfluxDB**（高频监控数据）
- Agent **直写 SQLite**（低频测试结果）
- MCP Server 从数据库查询数据返回给 AI

**关键设计**：
- ❌ 监控数据**不经过** MCP（避免性能瓶颈）
- ✅ Agent 本地采集 + 直接入库
- ✅ MCP 只负责控制指令和结果查询

---

## 二、MCP Tools 接口设计 (54个工具)

### 2.1 Agent管理类 (Agent Management) - 7个工具

#### Tool 1: `deploy_agent`
**功能**: 在目标服务器部署Agent

**实现思路**:
- SSH连接目标服务器
- 安装Python运行时（如未安装）
- 下载Agent代码包
- 配置Agent连接参数（MCP Server地址、数据库地址）
- 启动Agent守护进程（systemd/supervisor）
- 返回agent_id

---

#### Tool 2: `check_agent_status`
**功能**: 检查Agent运行状态

**实现思路**:
- 通过HTTP调用Agent的健康检查接口
- 获取Agent版本、运行时长、资源使用
- 检查Agent日志中的错误
- 返回健康状态（healthy/degraded/unhealthy）

---

#### Tool 3: `upgrade_agent`
**功能**: 升级Agent版本

**实现思路**:
- 发送升级指令给Agent
- Agent下载新版本代码
- Agent重启服务
- 验证新版本运行正常
- 支持回滚到上一版本

---

#### Tool 4: `restart_agent`
**功能**: 重启Agent

**实现思路**:
- 通过systemd/supervisor重启Agent服务
- 等待Agent重新上线
- 检查重启后的健康状态
- 记录重启日志

---

#### Tool 5: `get_agent_logs`
**功能**: 获取Agent日志

**实现思路**:
- SSH连接服务器读取日志文件
- 或通过Agent的日志查询接口
- 支持时间范围过滤
- 支持日志级别过滤
- 返回日志内容

---

#### Tool 6: `uninstall_agent`
**功能**: 卸载Agent

**实现思路**:
- 停止Agent服务
- 删除Agent代码和配置
- 清理systemd/supervisor配置
- 保留已采集的数据
- 返回卸载结果

---

#### Tool 7: `configure_agent`
**功能**: 配置Agent参数

**实现思路**:
- 发送配置更新指令给Agent
- 支持动态调整：监控频率、上报间隔、日志级别
- Agent热更新配置（无需重启）
- 验证配置生效

---

### 2.2 服务器管理类 (Server Management) - 5个工具

#### Tool 8: `register_server`
**功能**: 注册压测服务器

**实现思路**:
- 接收服务器信息（IP、SSH端口、认证方式）
- 检测是否已部署Agent
- 如未部署，提示先调用`deploy_agent`
- 存储服务器配置到SQLite（加密存储凭证）
- 返回唯一server_id

---

#### Tool 9: `list_servers`
**功能**: 列出已注册服务器

**实现思路**:
- 从SQLite读取所有服务器配置
- 联动`check_agent_status`获取Agent状态
- 返回服务器列表（脱敏，不显示密码）
- 包含Agent状态（在线/离线/版本）

---

#### Tool 10: `remove_server`
**功能**: 移除服务器注册

**实现思路**:
- 检查该服务器是否有正在运行的任务
- 检查Agent是否已卸载
- 从SQLite删除配置和凭证
- 提示是否需要卸载Agent

---

#### Tool 11: `get_server_hardware_info`
**功能**: 获取服务器硬件信息

**实现思路**:
- 通过Agent获取硬件清单
- Agent本地执行：lscpu、nvidia-smi、lsblk
- 返回CPU、GPU、内存、磁盘信息
- 数据缓存在SQLite

---

#### Tool 12: `update_server_info`
**功能**: 更新服务器信息

**实现思路**:
- 更新服务器别名、标签、分组
- 更新SSH认证凭证（如密码变更）
- 更新SQLite配置表

---

### 2.3 环境管理类 (Environment Management) - 5个工具

#### Tool 13: `setup_bench_env`
**功能**: 一键初始化压测环境

**实现思路**:
- 通过Agent执行环境初始化脚本
- Agent检测操作系统类型
- Agent安装依赖（build-essential、python、docker）
- Agent下载并安装 Phoronix Test Suite
- 配置环境变量和权限
- 返回安装结果和版本信息

---

#### Tool 14: `check_hardware_inventory`
**功能**: 扫描服务器硬件拓扑

**实现思路**:
- 通过Agent执行硬件扫描
- Agent本地调用：lscpu、nvidia-smi、lsblk、lsmem
- 结果存储到SQLite，返回结构化硬件清单
- 同时更新Agent本地缓存

---

#### Tool 15: `install_test_suite`
**功能**: 安装特定测试套件

**实现思路**:
- 发送指令给Agent：安装测试套件
- Agent调用PTS命令：`phoronix-test-suite install <suite>`
- Agent检查依赖并自动安装
- 返回已安装测试列表

---

#### Tool 16: `verify_environment`
**功能**: 验证压测环境完整性

**实现思路**:
- 通过Agent执行环境检查脚本
- Agent检查：PTS版本、Docker状态、编译工具、传感器
- 返回各项检查结果和建议

---

#### Tool 17: `cleanup_environment`
**功能**: 清理测试环境

**实现思路**:
- 发送指令给Agent：清理环境
- Agent清理：PTS缓存、临时文件、Docker未使用镜像
- 支持dry_run模式预览
- 返回清理结果

---

### 2.4 压测执行类 (Benchmark Execution) - 6个工具

#### Tool 18: `run_benchmark`
**功能**: 执行硬件压测（核心接口）

**实现思路**:
- 发送任务指令给Agent
- Agent启动压测进程
- Agent同时启动本地监控线程
- Agent实时推送日志到MCP Server（WebSocket）
- 测试完成，Agent将结果写入SQLite和InfluxDB
- 返回task_id

**Agent内部流程**:
```python
# Agent端执行
task_id = generate_task_id()
process = start_benchmark(test_name)
monitor_thread = start_local_monitoring(task_id)

# 监控线程直接写入InfluxDB
while task_running:
    metrics = collect_metrics()  # psutil, nvidia-smi
    influxdb.write(metrics)      # 直写，不走MCP
    
# 任务完成
result = wait_for_completion(task_id)
sqlite.save(result)              # 写入SQLite
```

---

#### Tool 19: `cancel_benchmark`
**功能**: 取消正在运行的测试

**实现思路**:
- 发送取消指令给Agent
- Agent终止压测进程
- Agent停止监控线程
- 保存已完成的部分结果
- 返回取消状态

---

#### Tool 20: `get_benchmark_status`
**功能**: 查询压测任务状态

**实现思路**:
- 查询Agent的任务状态（或从SQLite读取）
- 获取进度百分比、当前迭代
- 获取最近日志片段（Agent推送）
- 返回完整状态信息

---

#### Tool 21: `list_available_benchmarks`
**功能**: 列出所有可用的测试项目

**实现思路**:
- 通过Agent查询PTS测试列表
- Agent执行：`phoronix-test-suite list-available-tests`
- 过滤已安装和未安装的测试
- 按类别分组返回

---

#### Tool 22: `create_benchmark_profile`
**功能**: 创建测试配置模板

**实现思路**:
- 将测试配置保存到SQLite
- 包含测试列表、参数、标签
- 返回profile_id供批量执行

---

#### Tool 23: `pause_benchmark`
**功能**: 暂停正在运行的测试

**实现思路**:
- 发送暂停指令给Agent
- Agent发送SIGSTOP暂停进程
- Agent保持监控线程运行
- 更新任务状态为paused

---

### 2.5 监控数据查询类 (Monitoring Query) - 4个工具

> **注意**: 监控数据由Agent本地采集并**直接写入InfluxDB**，MCP Server只负责查询

#### Tool 24: `start_monitoring`
**功能**: 启动后台监控

**实现思路**:
- 发送指令给Agent：启动监控
- Agent启动独立监控线程
- Agent按指定间隔采集数据（psutil、nvidia-smi、sensors）
- Agent**直接写入InfluxDB**（不经过MCP）
- 返回monitor_id

**Agent内部实现**:
```python
# Agent端
def monitoring_loop():
    while active:
        metrics = {
            'cpu_percent': psutil.cpu_percent(),
            'memory_used': psutil.virtual_memory().used,
            'cpu_temp': get_cpu_temp(),
            'gpu_temp': get_gpu_temp()
        }
        # 直接写入InfluxDB，不走MCP
        influxdb_client.write(metrics, tags={'agent_id': agent_id})
        sleep(interval)
```

---

#### Tool 25: `stop_monitoring`
**功能**: 停止监控

**实现思路**:
- 发送停止指令给Agent
- Agent终止监控线程
- 刷新缓冲区数据到InfluxDB
- 返回监控统计信息

---

#### Tool 26: `get_realtime_metrics`
**功能**: 获取实时指标

**实现思路**:
- 从InfluxDB查询最近的数据点
- 查询语句：`SELECT * FROM metrics WHERE agent_id=X ORDER BY time DESC LIMIT 1`
- 返回当前时刻的系统指标
- **不是实时采集，而是查询最近采集的数据**

---

#### Tool 27: `query_monitoring_data`
**功能**: 查询历史监控数据

**实现思路**:
- 从InfluxDB查询指定时间范围的数据
- 支持降采样聚合（1min/5min/1hour）
- 支持多指标查询
- 返回时序数据点列表

---

### 2.6 数据存储与查询类 (Data & Resources) - 5个工具

> **说明**: 这些工具操作的是数据库（SQLite、InfluxDB），数据已由Agent提前写入

#### Tool 28: `save_benchmark_result`
**功能**: 手动保存测试结果（通常自动触发）

**实现思路**:
- 此工具通常不手动调用
- Agent完成任务后自动调用（内部接口）
- 解析测试输出，提取分数
- 写入SQLite + InfluxDB

---

#### Tool 29: `query_history`
**功能**: 查询历史测试记录

**实现思路**:
- 从SQLite读取benchmark_results表
- 支持多条件过滤（测试名称、日期范围、标签）
- 分页返回结果
- 包含硬件快照信息

---

#### Tool 30: `compare_results`
**功能**: 对比多次测试结果

**实现思路**:
- 从SQLite读取多个测试结果
- 计算分数变化百分比
- 对比硬件配置差异
- 生成对比分析报告
- 识别性能提升/下降原因

---

#### Tool 31: `export_result`
**功能**: 导出测试结果

**实现思路**:
- 从数据库读取测试结果
- 转换为目标格式（JSON/CSV/HTML/PDF）
- 可选包含时序监控数据
- 保存到导出目录

---

#### Tool 32: `delete_result`
**功能**: 删除测试结果

**实现思路**:
- 从SQLite删除元数据记录
- 从InfluxDB删除时序数据
- 删除关联的日志文件
- 计算释放的存储空间

---

### 2.7 时序数据分析类 (Timeseries Analysis) - 4个工具

> **说明**: 分析Agent采集并写入InfluxDB的监控数据

#### Tool 33: `retrieve_timeseries_data`
**功能**: 获取时序监控数据

**实现思路**:
- 从InfluxDB查询指定测试的时序数据
- 支持时间范围过滤
- 支持降采样聚合（1min/5min/1hour）
- 计算基础统计信息（min/max/avg）
- 返回时序数据点列表

---

#### Tool 34: `analyze_trend`
**功能**: 分析趋势

**实现思路**:
- 提取时序数据的时间序列
- 使用线性回归计算趋势斜率
- 检测异常数据点（Z-score或Isolation Forest）
- 识别关键事件（如降频时刻）
- 返回趋势分析和异常列表

---

#### Tool 35: `detect_anomaly`
**功能**: 检测异常数据点

**实现思路**:
- 对时序数据进行预处理
- 应用异常检测算法（Z-score/Isolation Forest/DBSCAN）
- 标记异常点和异常类型
- 计算异常严重程度
- 返回异常点列表和可能原因

---

#### Tool 36: `detect_bottleneck`
**功能**: 检测性能瓶颈

**实现思路**:
- 综合分析时序数据
- 识别温度墙、功耗墙、内存瓶颈
- 对比基准性能数据
- 计算瓶颈影响程度
- 返回瓶颈类型、证据和优化建议

---

### 2.8 智能分析与优化类 (Intelligence & Optimization) - 4个工具

#### Tool 37: `generate_expert_report`
**功能**: 生成专家级诊断报告（核心RAG接口）

**实现思路**:
- 提取测试结果和时序数据
- 调用`detect_anomaly`识别异常
- **RAG检索**：在向量数据库中搜索相关文档
- 使用LLM生成结构化报告
- 返回完整报告

---

#### Tool 38: `query_knowledge_base`
**功能**: 检索硬件手册和优化文档

**实现思路**:
- 接收自然语言查询
- 使用Embedding模型转换为向量
- 在向量数据库中检索相似文档
- 返回文档片段和来源信息

---

#### Tool 39: `suggest_optimization`
**功能**: 智能优化建议

**实现思路**:
- 分析当前测试结果
- 识别性能瓶颈
- 基于优化目标排序建议
- 从知识库检索最佳实践
- 返回分级优化方案

---

#### Tool 40: `diagnose_failure`
**功能**: 故障诊断

**实现思路**:
- 解析错误日志
- 提取错误类型和错误码
- 匹配已知故障模式库
- RAG检索相关故障处理文档
- 返回根因分析和修复步骤

---

### 2.9 任务管理类 (Task Management) - 4个工具

#### Tool 41: `list_running_tasks`
**功能**: 列出正在运行的任务

**实现思路**:
- 查询SQLite任务状态表
- 联动Agent查询实时状态
- 过滤status为running的任务
- 返回任务列表和资源使用情况

---

#### Tool 42: `wait_for_task`
**功能**: 等待任务完成（阻塞式）

**实现思路**:
- 启动轮询循环
- 定期查询任务状态
- 超时则返回超时错误
- 任务完成返回最终结果
- **注意**：此工具会阻塞AI，谨慎使用

---

#### Tool 43: `resume_benchmark`
**功能**: 恢复暂停的测试

**实现思路**:
- 发送恢复指令给Agent
- Agent发送SIGCONT信号恢复进程
- Agent恢复监控线程
- 更新任务状态为running

---

#### Tool 44: `check_task_dependencies`
**功能**: 检查任务依赖

**实现思路**:
- 通过Agent查询系统资源
- 检查CPU/内存/磁盘资源
- 检查依赖工具是否已安装
- 检查是否有冲突任务
- 返回依赖检查结果

---

### 2.10 批量操作类 (Batch Operations) - 2个工具

#### Tool 45: `run_benchmark_suite`
**功能**: 批量执行测试套件

**实现思路**:
- 加载预定义的测试模板
- 发送批量任务指令给Agent
- Agent执行测试（串行/并行）
- 创建suite_task_id管理进度
- 返回所有子任务ID列表

---

#### Tool 46: `get_suite_status`
**功能**: 查询测试套件整体状态

**实现思路**:
- 查询所有子任务状态
- 统计完成/运行中/待执行数量
- 计算整体进度百分比
- 返回详细状态报告

---

### 2.11 数据管理类 (Data Management) - 3个工具

#### Tool 47: `compact_data`
**功能**: 压缩历史数据

**实现思路**:
- 从InfluxDB查询原始时序数据
- 按指定粒度降采样
- 删除原始数据，保留聚合数据
- 返回压缩比和释放空间

---

#### Tool 48: `archive_old_results`
**功能**: 归档旧测试结果

**实现思路**:
- 查询指定日期之前的结果
- 导出为JSON文件
- 压缩为tar.gz格式
- 从数据库删除记录
- 返回归档文件路径

---

#### Tool 49: `check_storage_usage`
**功能**: 检查存储使用情况

**实现思路**:
- 检查SQLite数据库文件大小
- 查询InfluxDB数据库大小
- 统计日志文件目录大小
- 返回存储详情和清理建议

---

### 2.12 系统配置类 (System Configuration) - 3个工具

#### Tool 50: `set_kernel_param`
**功能**: 设置内核参数

**实现思路**:
- 发送配置指令给Agent
- Agent使用sysctl修改参数
- Agent验证参数是否生效
- 记录修改历史到SQLite

---

#### Tool 51: `restore_config`
**功能**: 恢复默认配置

**实现思路**:
- 从SQLite备份表读取配置
- 发送恢复指令给Agent
- Agent恢复sysctl配置
- 返回恢复的配置项列表

---

#### Tool 52: `backup_config`
**功能**: 备份当前配置

**实现思路**:
- 通过Agent读取当前sysctl配置
- 备份环境变量
- 备份PTS配置文件
- 存储到SQLite备份表
- 返回备份ID

---

### 2.13 系统健康类 (System Health) - 2个工具

#### Tool 53: `health_check`
**功能**: 系统健康检查

**实现思路**:
- 检查MCP Server自身健康
- 联动Agent健康检查
- 聚合所有组件健康状态
- 返回各项检查结果

---

#### Tool 54: `get_system_info`
**功能**: 获取系统运行信息

**实现思路**:
- 读取Perfa版本信息
- 计算MCP Server运行时长
- 统计历史任务数量
- 聚合所有Agent状态
- 返回系统概览信息

---

## 三、MCP Resources 设计 (5个资源)

### Resource 1: `mcp://agents/list`
**描述**: 已部署Agent列表及状态

---

### Resource 2: `mcp://hardware/inventory/{agent_id}`
**描述**: 指定Agent所在服务器的硬件清单

---

### Resource 3: `mcp://benchmark/history`
**描述**: 历史测试汇总表

---

### Resource 4: `mcp://knowledge/{doc_id}`
**描述**: 知识库文档

---

### Resource 5: `mcp://logs/{task_id}`
**描述**: 任务日志流（Agent推送）

---

## 四、典型工作流示例

### 4.1 完整压测流程

```
1. deploy_agent(host="192.168.1.100", credentials)
   ↓ 在目标服务器部署Agent，返回 agent_id

2. check_agent_status(agent_id)
   ↓ 验证Agent运行正常

3. setup_bench_env(agent_id, provider="pts")
   ↓ Agent安装压测环境

4. check_hardware_inventory(agent_id)
   ↓ Agent扫描硬件，返回清单

5. run_benchmark(agent_id, "unixbench")
   ↓ Agent执行压测，返回 task_id
   ↓ Agent同时启动监控，数据直写InfluxDB

6. get_benchmark_status(task_id)  # 轮询
   ↓ 查询任务进度

7. query_monitoring_data(task_id)
   ↓ 从InfluxDB读取监控数据

8. generate_expert_report(task_id)
   ↓ 生成RAG报告
```

---

## 五、Agent架构设计

### 5.1 Agent职责

| 模块 | 职责 | 数据流 |
|------|------|--------|
| 任务执行器 | 执行压测、环境管理 | 接收MCP指令 → 本地执行 → 返回结果 |
| 监控采集器 | 采集CPU/GPU/温度/功耗 | 本地采集 → **直写InfluxDB** |
| 日志推送器 | 实时推送日志 | 本地日志 → 推送到MCP Server |
| 配置管理器 | 管理系统配置 | 接收指令 → 修改配置 → 返回结果 |

### 5.2 Agent监控采集示例

```python
# Agent端监控线程
def monitoring_loop(agent_id, task_id, interval):
    while monitoring_active:
        # 本地采集
        metrics = {
            'cpu_percent': psutil.cpu_percent(),
            'memory_used_gb': psutil.virtual_memory().used / 1e9,
            'cpu_temp_c': get_cpu_temp(),
            'gpu_temp_c': get_gpu_temp(),
            'cpu_freq_mhz': psutil.cpu_freq().current,
            'power_w': get_power_consumption()
        }
        
        # 直接写入InfluxDB，不走MCP
        influxdb_client.write(
            measurement='system_metrics',
            tags={
                'agent_id': agent_id,
                'task_id': task_id
            },
            fields=metrics
        )
        
        time.sleep(interval)
```

### 5.3 为什么监控数据不走MCP？

1. **性能问题**: 监控数据是高频采集（每秒多次），通过MCP传输会成为瓶颈
2. **MCP设计初衷**: MCP是AI调用协议，用于控制指令，不适合高频数据传输
3. **解耦设计**: Agent直写数据库，MCP Server只负责查询，职责清晰

---

## 六、工具清单汇总 (54个工具)

| 序号 | 工具名称 | 分类 |
|------|----------|------|
| 1-7 | Agent管理类 | deploy_agent, check_agent_status, upgrade_agent, restart_agent, get_agent_logs, uninstall_agent, configure_agent |
| 8-12 | 服务器管理类 | register_server, list_servers, remove_server, get_server_hardware_info, update_server_info |
| 13-17 | 环境管理类 | setup_bench_env, check_hardware_inventory, install_test_suite, verify_environment, cleanup_environment |
| 18-23 | 压测执行类 | run_benchmark, cancel_benchmark, get_benchmark_status, list_available_benchmarks, create_benchmark_profile, pause_benchmark |
| 24-27 | 监控查询类 | start_monitoring, stop_monitoring, get_realtime_metrics, query_monitoring_data |
| 28-32 | 数据存储类 | save_benchmark_result, query_history, compare_results, export_result, delete_result |
| 33-36 | 时序分析类 | retrieve_timeseries_data, analyze_trend, detect_anomaly, detect_bottleneck |
| 37-40 | 智能分析类 | generate_expert_report, query_knowledge_base, suggest_optimization, diagnose_failure |
| 41-44 | 任务管理类 | list_running_tasks, wait_for_task, resume_benchmark, check_task_dependencies |
| 45-46 | 批量操作类 | run_benchmark_suite, get_suite_status |
| 47-49 | 数据管理类 | compact_data, archive_old_results, check_storage_usage |
| 50-52 | 系统配置类 | set_kernel_param, restore_config, backup_config |
| 53-54 | 系统健康类 | health_check, get_system_info |

---

## 七、架构评审总结

### 7.1 核心设计亮点

| 亮点 | 说明 |
|------|------|
| **Agent自治** | Agent本地采集监控数据，直写InfluxDB |
| **控制数据分离** | MCP只传控制指令，不传高频数据 |
| **静默持久化** | AI无需关心数据存储 |
| **RAG内聚** | 报告生成内置智能检索 |
| **分层清晰** | 13个分类，职责明确 |

### 7.2 关键区别

| 维度 | 错误设计（v1.0） | 正确设计（v3.0） |
|------|-----------------|-----------------|
| Agent角色 | 不存在 | 独立守护进程 |
| 监控采集 | MCP远程采集 | Agent本地采集 |
| 数据传输 | 监控数据走MCP | 监控数据直写DB |
| 性能瓶颈 | MCP是瓶颈 | 无瓶颈 |

---

**设计者**: Perfa 架构团队  
**版本**: v3.0  
**状态**: 设计完成  
**最后更新**: 2026-03-10
