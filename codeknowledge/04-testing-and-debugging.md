# 测试与排障

## 当前已有测试资产

### Node Agent

- 测试说明: `test/node_agent_test.md`
- 脚本目录: `test/node_agent/`
- 关键脚本：
  - `run_all.py`
  - `test_monitor.py`
  - `test_tool.py`
  - `test_benchmark.py`
  - `test_storage.py`

### Prompt / Agent

- `test/test_prompt_cases.py`

目前从仓库结构看，最成体系的是 Node Agent API 相关测试。

## 常用验证点

### Node Agent 是否存活

```bash
curl http://localhost:8080/health
curl http://localhost:8080/api/status
curl http://localhost:8000/metrics
```

### MCP Server 是否存活

```bash
curl -N "http://localhost:9000/sse?api_key=YOUR_KEY"
```

### LangChain Agent 是否存活

```bash
curl http://localhost:10000/health
curl http://localhost:10000/
```

### Web UI V2 是否存活

直接访问 `http://localhost:3002`

## 常见排障方向

### 前端有页面，后端没响应

优先检查：

- `webui-v2` 的代理是否指向正确后端
- `langchain_agent` 是否运行在 `10000`
- `/v1/chat/completions` 是否可访问

### Agent 能回答，但不能调用真实能力

优先检查：

- `langchain_agent` 到 `mcp_server` 的连接
- `MCP_API_KEY`
- `mcp_server` 中 Tool 是否正确注册
- Node Agent 是否可达

### Tool 调用了，但压测没真正执行

优先检查：

- Node Agent 的工具安装状态
- `BenchmarkExecutor` 是否已注册对应 Runner
- `/tmp/agent.log`

### 监控页面没数据

优先检查：

- `node_agent:8000/metrics` 是否正常
- VictoriaMetrics 是否启动
- Grafana 数据源是否成功配置

## 日志与状态入口

- Node Agent 日志: `/tmp/agent.log`
- Node Agent 健康接口: `http://localhost:8080/health`
- FastAPI 根接口: `http://localhost:10000/`
- 部署状态脚本: `ops/scripts/status-point.sh`

## 测试文档的定位

`test/node_agent_test.md` 是一份很好的“人工联调脚本说明”，适合作为测试操作手册来源，但它仍然主要覆盖 Node Agent，不覆盖全系统。
