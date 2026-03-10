# Perfa 3周MVP冲刺计划

> **目标**: 3周内完成可演示的最小可行产品（MVP）  
> **策略**: 聚焦核心功能，简化非必要功能，快速迭代

---

## 📅 时间规划（21天）

### 第1周（7天）：基础框架 + 核心通信

**目标**: 跑通基本流程

| 天数 | 任务 | 交付物 |
|------|------|--------|
| Day 1-2 | MCP Server基础框架 | server.py可启动 |
| Day 3-4 | Agent基础框架 + HTTP API | Agent可接收指令 |
| Day 5-6 | 数据库集成（InfluxDB） | Agent可写入数据 |
| Day 7 | 部署脚本 + 测试 | 可部署到测试服务器 |

**关键产出**:
- ✅ MCP Server可启动，注册3-5个核心工具
- ✅ Agent可启动，监听HTTP请求
- ✅ Agent监控线程可采集CPU/内存，写入InfluxDB
- ✅ 可通过MCP调用Agent API

---

### 第2周（7天）：压测执行 + 数据查询

**目标**: 完成核心压测流程

| 天数 | 任务 | 交付物 |
|------|------|--------|
| Day 8-9 | 任务执行器（仅支持1个测试） | 可执行unixbench |
| Day 10-11 | 监控关联任务 | 测试时采集监控数据 |
| Day 12-13 | 数据查询接口 | 可查询历史数据 |
| Day 14 | 端到端测试 | 完整流程可跑通 |

**关键产出**:
- ✅ run_benchmark工具可执行unixbench
- ✅ 测试过程中实时采集监控数据
- ✅ 测试结果保存到SQLite
- ✅ query_monitoring_data可查询数据
- ✅ 完整流程：部署Agent → 执行测试 → 查询数据

---

### 第3周（7天）：优化 + 演示准备

**目标**: 稳定性 + Demo

| 天数 | 任务 | 交付物 |
|------|------|--------|
| Day 15-16 | Bug修复 + 稳定性优化 | 无明显bug |
| Day 17-18 | 简单报告生成 | generate_expert_report可用 |
| Day 19-20 | 部署脚本完善 | 一键部署 |
| Day 21 | Demo准备 + 文档 | 可演示的完整流程 |

**关键产出**:
- ✅ 核心功能稳定运行
- ✅ 简单的测试报告（无RAG，仅文本模板）
- ✅ 一键部署脚本
- ✅ Demo演示流程
- ✅ 基础文档

---

## 🎯 MVP功能范围

### 必须实现（核心功能）

| 模块 | 功能 | 工具数 | 优先级 |
|------|------|--------|--------|
| Agent管理 | deploy_agent, check_agent_status | 2 | P0 |
| 压测执行 | run_benchmark, get_benchmark_status | 2 | P0 |
| 监控采集 | Agent内部实现（直写InfluxDB） | - | P0 |
| 数据查询 | query_monitoring_data | 1 | P0 |
| 任务管理 | cancel_benchmark | 1 | P0 |
| 简单报告 | generate_expert_report（简化版） | 1 | P1 |

**总计**: 7个核心工具（占54个的13%）

### 暂缓实现（后续迭代）

❌ 以下功能在MVP阶段**不做**：

1. **RAG知识库**（最耗时）
   - 改为：简单的文本模板报告
   - 后续：集成向量数据库和LLM

2. **完整的54个工具**
   - 改为：仅实现7个核心工具
   - 后续：逐步补充

3. **GPU监控**
   - 改为：仅CPU/内存/温度
   - 后续：添加GPU采集

4. **批量操作**
   - 改为：仅单任务执行
   - 后续：支持批量测试

5. **系统配置管理**
   - 改为：无
   - 后续：添加内核参数调整

---

## 💻 简化实现方案

### 1. MCP Server简化

**原计划（5000行）** → **MVP（800行）**

```python
# server.py（150行）
server = Server("perfa")

# 仅注册7个工具
@server.tool("deploy_agent")           # 1
@server.tool("check_agent_status")     # 2
@server.tool("run_benchmark")          # 3
@server.tool("get_benchmark_status")   # 4
@server.tool("query_monitoring_data")  # 5
@server.tool("cancel_benchmark")       # 6
@server.tool("generate_simple_report") # 7

server.run()
```

**tools目录**:
```
tools/
├── agent.py          # 2个工具（150行）
├── benchmark.py      # 3个工具（200行）
├── monitoring.py     # 1个工具（100行）
└── report.py         # 1个工具（100行）

总计：550行 + server.py 150行 = 700行
```

### 2. Agent简化

**原计划（2000行）** → **MVP（600行）**

```python
# main.py（50行）
agent = Agent(config)
agent.start()

# core/agent.py（150行）
class Agent:
    def start():
        # 仅启动3个组件
        self.api_server.start()     # HTTP API
        self.monitor.start()        # 监控线程
        # 无需：日志推送、健康检查等

# core/monitor.py（150行）
# 仅采集CPU/内存/温度
# 直写InfluxDB

# core/task_executor.py（200行）
# 仅支持unixbench
# 简化结果解析

# api/server.py（100行）
# 仅3个API接口
# /api/run_benchmark
# /api/cancel_task
# /api/task_status
```

### 3. 报告生成简化

**原计划**（RAG + LLM） → **MVP**（文本模板）

```python
# tools/report.py
def generate_simple_report(result_id):
    # 从SQLite读取结果
    result = sqlite.get_result(result_id)
    
    # 简单模板（无RAG）
    report = f"""
    # 测试报告
    
    ## 基本信息
    - 测试名称: {result['test_name']}
    - 测试时间: {result['timestamp']}
    - 得分: {result['score']}
    
    ## 硬件配置
    - CPU: {result['cpu_model']}
    - 内存: {result['memory_gb']}GB
    
    ## 简单分析
    - 性能评级: {"优秀" if result['score'] > 2000 else "良好"}
    - 温度范围: {result['min_temp']}°C - {result['max_temp']}°C
    
    ## 建议
    - 如果温度过高，建议检查散热
    - 如果得分偏低，建议检查系统配置
    """
    
    return {"report": report}
```

---

## 🚀 快速启动脚本

### 一键部署脚本

```bash
#!/bin/bash
# deploy.sh

echo "=== Perfa MVP 快速部署 ==="

# 1. 检查环境
command -v python3 >/dev/null 2>&1 || { echo "需要Python3"; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "需要Docker"; exit 1; }

# 2. 启动InfluxDB
echo "启动InfluxDB..."
docker run -d --name perfa-influxdb \
  -p 8086:8086 \
  -e DOCKER_INFLUXDB_INIT_MODE=setup \
  -e DOCKER_INFLUXDB_INIT_USERNAME=admin \
  -e DOCKER_INFLUXDB_INIT_PASSWORD=admin123 \
  -e DOCKER_INFLUXDB_INIT_ORG=perfa \
  -e DOCKER_INFLUXDB_INIT_BUCKET=metrics \
  -e DOCKER_INFLUXDB_INIT_ADMIN_TOKEN=my-token \
  influxdb:2.0

# 3. 安装MCP Server依赖
echo "安装MCP Server依赖..."
cd mcp_server_project/
pip3 install -r requirements.txt

# 4. 启动MCP Server
echo "启动MCP Server..."
python3 server.py &
MCP_PID=$!

# 5. 打包Agent
echo "打包Agent..."
cd ../daemonset_agent/
tar -czf ../agent.tar.gz .

# 6. 等待启动
sleep 5

echo "=== 部署完成 ==="
echo "MCP Server PID: $MCP_PID"
echo "Agent包: agent.tar.gz"
echo ""
echo "下一步："
echo "1. 复制agent.tar.gz到被测服务器"
echo "2. 解压并配置config.yaml"
echo "3. 运行: python3 main.py"
```

### 快速测试脚本

```python
# test_mvp.py
"""快速测试MVP功能"""

import requests
import time

MCP_URL = "http://localhost:8000"

def test_mvp():
    print("=== 测试MVP功能 ===")
    
    # 1. 部署Agent（假设已手动部署）
    print("1. 检查Agent状态...")
    response = requests.post(f"{MCP_URL}/tools/call", json={
        "tool": "check_agent_status",
        "params": {"agent_id": "agent_localhost"}
    })
    print(f"   Agent状态: {response.json()}")
    
    # 2. 执行压测
    print("2. 执行unixbench测试...")
    response = requests.post(f"{MCP_URL}/tools/call", json={
        "tool": "run_benchmark",
        "params": {
            "agent_id": "agent_localhost",
            "test_name": "unixbench",
            "params": {"iterations": 1}
        }
    })
    task_id = response.json()['task_id']
    print(f"   任务ID: {task_id}")
    
    # 3. 查询进度
    print("3. 查询进度...")
    for i in range(10):
        response = requests.post(f"{MCP_URL}/tools/call", json={
            "tool": "get_benchmark_status",
            "params": {"task_id": task_id}
        })
        status = response.json()
        print(f"   进度: {status.get('progress_percent', 0)}%")
        if status['status'] == 'completed':
            break
        time.sleep(10)
    
    # 4. 查询监控数据
    print("4. 查询监控数据...")
    response = requests.post(f"{MCP_URL}/tools/call", json={
        "tool": "query_monitoring_data",
        "params": {"task_id": task_id}
    })
    print(f"   数据点数: {len(response.json()['data'])}")
    
    # 5. 生成报告
    print("5. 生成报告...")
    response = requests.post(f"{MCP_URL}/tools/call", json={
        "tool": "generate_simple_report",
        "params": {"result_id": task_id}
    })
    print(f"   报告:\n{response.json()['report']}")
    
    print("=== 测试完成 ===")

if __name__ == "__main__":
    test_mvp()
```

---

## 📊 代码量估算

| 组件 | 原计划 | MVP | 削减比例 |
|------|--------|-----|----------|
| MCP Server | 5000行 | 800行 | 84% ↓ |
| Agent | 2000行 | 600行 | 70% ↓ |
| **总计** | 7000行 | 1400行 | **80% ↓** |

**MVP只需编写1400行代码！**

---

## 📝 MVP交付清单

### 第1周交付

- [ ] MCP Server可启动
- [ ] Agent可启动并监听端口
- [ ] Agent可采集CPU/内存并写入InfluxDB
- [ ] deploy_agent工具可用
- [ ] check_agent_status工具可用

### 第2周交付

- [ ] run_benchmark工具可执行unixbench
- [ ] 测试过程中采集监控数据
- [ ] query_monitoring_data工具可用
- [ ] 完整流程可跑通

### 第3周交付

- [ ] 核心功能稳定
- [ ] generate_simple_report工具可用
- [ ] 一键部署脚本
- [ ] Demo演示流程
- [ ] 基础文档

---

## 🎯 Demo演示流程（5分钟）

```
1. 启动InfluxDB (10秒)
   docker run -d influxdb:2.0

2. 启动MCP Server (5秒)
   python server.py

3. 部署Agent到测试服务器 (30秒)
   # 假设已提前部署好
   curl http://192.168.1.100:9000/health

4. 执行unixbench测试 (2分钟)
   # 演示过程中实时显示监控数据
   run_benchmark(agent_id, "unixbench")

5. 查询监控曲线 (30秒)
   # 从InfluxDB查询温度/频率曲线

6. 生成简单报告 (20秒)
   # 展示测试报告

7. 总结 (30秒)
   - 完成1次完整压测流程
   - 实时监控数据
   - 自动生成报告
```

---

## ⚠️ 风险控制

### 技术风险

| 风险 | 应对方案 |
|------|----------|
| PTS安装失败 | 提前准备安装脚本，改用Docker方式 |
| InfluxDB连接问题 | 提前测试连接，准备备用SQLite方案 |
| Agent部署失败 | 准备手动部署文档，支持本地测试 |
| 监控数据写入慢 | 降低采样频率，仅保留必要指标 |

### 时间风险

| 风险 | 应对方案 |
|------|----------|
| 第1周未完成 | 削减Agent部署功能，手动部署演示 |
| 第2周未完成 | 仅实现单个测试，简化结果解析 |
| 第3周未完成 | 准备PPT演示未完成部分，承诺后续迭代 |

---

## 💡 关键建议

### 1. 不要追求完美

❌ **不要**：
- 实现54个工具
- 集成RAG知识库
- 完善的错误处理
- 精美的UI

✅ **要做**：
- 7个核心工具
- 简单文本报告
- 基本错误提示
- 可用的Demo

### 2. 快速验证

- **Day 1就要有代码运行起来**
- **Day 7就要能跑通基本流程**
- **Day 14就要接近完成**
- **Day 21只做优化和测试**

### 3. 借助现有工具

- 使用Flask而非自己写HTTP服务器
- 使用psutil而非自己实现监控
- 使用subprocess而非自己实现进程管理
- 使用现成的Docker镜像

### 4. 可演示即可

- 代码质量可以粗糙
- 错误处理可以简化
- 文档可以简单
- **只要能演示成功就行**

---

## 📅 每日检查清单

### 第1周每日检查

- [ ] 今天写了多少行代码？
- [ ] 核心功能能否运行？
- [ ] 是否遇到阻塞问题？
- [ ] 明天计划做什么？

### 第2周每日检查

- [ ] 压测能否执行？
- [ ] 监控数据能否采集？
- [ ] 数据能否查询？
- [ ] 完整流程能否跑通？

### 第3周每日检查

- [ ] 是否有严重bug？
- [ ] Demo流程是否顺畅？
- [ ] 文档是否完成？
- [ ] 准备是否充分？

---

## 🚨 紧急预案

如果时间不够，按以下顺序削减功能：

1. **首先削减**: RAG报告 → 简单文本模板
2. **其次削减**: GPU监控 → 仅CPU/内存
3. **再次削减**: 多测试支持 → 仅unixbench
4. **最后削减**: 自动部署 → 手动部署脚本

**底线**: 必须能演示1次完整的压测流程！

---

## ✅ 成功标准

**MVP成功标准**（最低要求）：

- [x] 可以部署Agent到目标服务器
- [x] 可以执行unixbench测试
- [x] 测试过程中采集CPU/内存监控数据
- [x] 监控数据写入InfluxDB
- [x] 可以查询测试结果和监控数据
- [x] 可以生成简单的测试报告
- [x] 完整流程可在5分钟内演示

**做到了这7点，MVP就成功了！**

---

**现在就开始Day 1的工作吧！时间紧迫，行动起来！** 🚀
