"""
MCP Server 和 Agent 完整交互示例
演示完整的压测流程
"""

# ==================== 场景1: 部署Agent到目标服务器 ====================

"""
1. 用户告诉AI: "在192.168.1.100服务器上部署Agent"

2. AI调用MCP工具:
"""
mcp_client.call_tool("deploy_agent", {
    "host": "192.168.1.100",
    "ssh_port": 22,
    "credentials": {
        "username": "root",
        "password": "xxx"
    }
})

"""
3. MCP Server执行 (mcp_server_project/tools/agent.py):
"""
async def deploy_agent(host, ssh_port, credentials):
    # SSH连接
    ssh_client = SSHClient(host, ssh_port, credentials)
    await ssh_client.connect()
    
    # 上传Agent代码
    await ssh_client.upload("daemonset_agent.tar.gz", "/opt/perfa/")
    
    # 解压
    await ssh_client.execute("cd /opt/perfa && tar -xzf daemonset_agent.tar.gz")
    
    # 安装依赖
    await ssh_client.execute("cd /opt/perfa/daemonset_agent && pip install -r requirements.txt")
    
    # 配置
    config = {
        "agent": {"id": f"agent_{host.replace('.', '_')}"},
        "mcp_server": {"url": "http://mcp-server:8000"},
        "influxdb": {"url": "http://influxdb:8086"}
    }
    await ssh_client.write_file("/opt/perfa/daemonset_agent/config.yaml", yaml.dump(config))
    
    # 启动Agent
    await ssh_client.execute("systemctl start perfa-agent")
    
    # 等待Agent上线
    agent_id = f"agent_{host.replace('.', '_')}"
    await wait_for_agent_online(agent_id)
    
    return {
        "agent_id": agent_id,
        "status": "deployed"
    }

"""
4. Agent启动 (daemonset_agent/main.py):
"""
# Agent启动后：
# - 启动HTTP API服务器（端口9000）
# - 启动监控线程（直写InfluxDB）
# - 向MCP Server注册


# ==================== 场景2: 执行压测任务 ====================

"""
1. 用户告诉AI: "在这台服务器上执行unixbench测试"

2. AI调用MCP工具:
"""
mcp_client.call_tool("run_benchmark", {
    "agent_id": "agent_192_168_1_100",
    "test_name": "unixbench",
    "params": {"iterations": 3}
})

"""
3. MCP Server执行 (mcp_server_project/tools/benchmark.py):
"""
async def run_benchmark(agent_id, test_name, params):
    # 获取Agent地址
    agent_info = await db.get_agent_info(agent_id)
    agent_host = agent_info['host']  # 192.168.1.100
    
    # 发送HTTP请求给Agent
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"http://{agent_host}:9000/api/run_benchmark",
            json={
                "task_id": task_id,
                "test_name": test_name,
                "params": params
            }
        )
    
    return {
        "task_id": task_id,
        "status": "running"
    }

"""
4. Agent执行 (daemonset_agent/api/server.py):
"""
@app.route('/api/run_benchmark', methods=['POST'])
def run_benchmark():
    data = request.json
    test_name = data['test_name']
    params = data['params']
    task_id = data['task_id']
    
    # 关联监控（监控数据会标记task_id）
    monitor.set_task_id(task_id)
    
    # 执行任务
    result = task_executor.run_benchmark(test_name, params)
    
    return jsonify(result)

"""
5. Agent任务执行器 (daemonset_agent/core/task_executor.py):
"""
def run_benchmark(self, test_name, params):
    # 启动PTS测试
    process = subprocess.Popen([
        'phoronix-test-suite',
        'benchmark',
        'unixbench'
    ])
    
    # 等待完成
    stdout, stderr = process.communicate()
    
    # 解析结果
    result = parse_result(stdout)
    
    # 写入SQLite
    sqlite_writer.save_result({
        'task_id': task_id,
        'score': result['score']
    })
    
    return result

"""
6. Agent监控线程 (daemonset_agent/core/monitor.py):
"""
# 监控线程一直在运行（独立于任务执行）
def monitoring_loop():
    while active:
        # 采集指标
        metrics = {
            'cpu_percent': psutil.cpu_percent(),
            'cpu_temp_c': get_cpu_temp(),
            'memory_used_gb': psutil.virtual_memory().used / 1e9
        }
        
        # 直接写入InfluxDB（不走MCP）
        influxdb_client.write(
            measurement='system_metrics',
            tags={
                'agent_id': 'agent_192_168_1_100',
                'task_id': current_task_id  # 如果有任务
            },
            fields=metrics
        )
        
        time.sleep(5)  # 每5秒采集一次


# ==================== 场景3: 查询监控数据 ====================

"""
1. 用户告诉AI: "查看刚才的测试监控数据"

2. AI调用MCP工具:
"""
mcp_client.call_tool("query_monitoring_data", {
    "task_id": "bench_20260310_153000",
    "time_range": {
        "start": "2026-03-10T14:00:00Z",
        "end": "2026-03-10T15:00:00Z"
    }
})

"""
3. MCP Server执行 (mcp_server_project/tools/monitoring.py):
"""
async def query_monitoring_data(task_id, time_range):
    # 直接从InfluxDB查询（Agent已提前写入）
    query = f'''
    from(bucket: "metrics")
      |> range(start: {time_range["start"]}, stop: {time_range["end"]})
      |> filter(fn: (r) => r["task_id"] == "{task_id}")
    '''
    
    result = influxdb_client.query(query)
    
    return {
        "task_id": task_id,
        "data": result
    }

# 注意：数据是Agent提前写入InfluxDB的，MCP Server只是查询


# ==================== 场景4: 生成专家报告 ====================

"""
1. 用户告诉AI: "生成这次测试的分析报告"

2. AI调用MCP工具:
"""
mcp_client.call_tool("generate_expert_report", {
    "result_id": "result_20260310_153000"
})

"""
3. MCP Server执行 (mcp_server_project/tools/intelligence.py):
"""
async def generate_expert_report(result_id):
    # 1. 从SQLite读取测试结果
    result = await sqlite.get_result(result_id)
    
    # 2. 从InfluxDB读取监控数据
    monitoring_data = await influxdb.query(result['task_id'])
    
    # 3. 检测异常
    anomalies = detect_anomalies(monitoring_data)
    
    # 4. RAG检索知识库
    for anomaly in anomalies:
        docs = vector_db.search(
            query=f"{result['cpu_model']} {anomaly['type']}",
            top_k=3
        )
        anomaly['knowledge_refs'] = docs
    
    # 5. LLM生成报告
    report = llm.generate(
        template="expert_report",
        context={
            "result": result,
            "anomalies": anomalies
        }
    )
    
    return report


# ==================== 完整数据流向 ====================

"""
控制流（指令）:
AI → MCP Server → Agent
    (调用工具)  (HTTP请求)

数据流（监控）:
Agent → InfluxDB → MCP Server → AI
(直写)  (查询)    (返回结果)

数据流（结果）:
Agent → SQLite → MCP Server → AI
(直写)  (查询)  (返回结果)

日志流:
Agent → MCP Server
(WebSocket推送)
"""


# ==================== 关键代码位置 ====================

"""
MCP Server代码:
├── server.py                      # 主入口，注册工具
├── tools/
│   ├── agent.py                  # deploy_agent, check_agent_status
│   ├── benchmark.py              # run_benchmark, get_benchmark_status
│   └── monitoring.py             # query_monitoring_data

Agent代码:
├── main.py                        # 主入口
├── core/
│   ├── agent.py                  # Agent主类
│   ├── monitor.py                # 监控采集，直写InfluxDB
│   └── task_executor.py          # 任务执行，写SQLite
├── api/
│   └── server.py                 # HTTP API，接收MCP指令
└── storage/
    ├── influxdb_writer.py        # InfluxDB写入
    └── sqlite_writer.py          # SQLite写入
"""


# ==================== 项目分离 ====================

"""
两个独立项目：

1. mcp_server_project/
   - 运行在管理服务器
   - 提供MCP接口给AI调用
   - 管理多个Agent
   - 查询数据库

2. daemonset_agent/
   - 运行在被测服务器
   - 执行压测任务
   - 采集监控数据
   - 直写数据库

通信方式：
- MCP Server → Agent: HTTP API
- Agent → MCP Server: HTTP注册 + WebSocket日志
- Agent → InfluxDB: HTTP直写
"""
