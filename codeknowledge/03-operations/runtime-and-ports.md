# 运行与端口

## 当前端口分配

结合当前代码和已实跑通过的 `ops/scripts/start-all.sh`，当前应重点关注这些端口：

| 服务 | 端口 | 备注 |
|------|------|------|
| Node Agent API | 8080 | Flask API |
| Node Agent Metrics | 8000 | Prometheus metrics |
| MCP Server | 9000 | SSE MCP 服务 |
| LangChain Agent API | 10000 | OpenAI 兼容 API |
| Web UI V1 | 3001 | 旧前端 |
| Web UI V2 | 3002 | 当前主前端 |
| Grafana | 3000 | 可视化 |
| VictoriaMetrics | 8428 | 时序数据库 |
| OTel Collector | 4317 / 4318 | gRPC / HTTP |
| Jaeger UI | 16686 | 链路追踪查看 |

## 运行链路

### 最小对话链路

```text
webui-v2:3002
  -> langchain_agent:10000
  -> mcp_server:9000
  -> node_agent:8080
```

### 监控链路

```text
node_agent:8000
  -> victoriametrics:8428
  -> grafana:3000
```

## 当前有效性说明

- `3002` 是当前主前端 `webui-v2` 的开发端口。
- `3001` 只对应旧前端 `webui/`，不应再作为主入口端口理解。
- `9000` 是 MCP SSE 服务端口，探活更适合使用 `HEAD /sse?api_key=...`。
