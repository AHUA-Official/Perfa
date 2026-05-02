# 运行与端口

## 当前端口分配

结合 `PORTS.md`、`webui-v2/README.md` 和最近进度文档，当前应重点关注这些端口：

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

## 端口文档的使用建议

`PORTS.md` 仍然适合保留为“单点端口登记表”，但不适合承载更完整的运行说明。完整上下文应优先看本目录文档。

## 当前有效性说明

- `PORTS.md` 中 Web UI 标的是 `3001`，那是旧前端口。
- `webui-v2/README.md` 明确当前 V2 开发端口是 `3002`。
- 因此实际维护时应把 `3001` 视为旧版，`3002` 视为当前主 UI。
