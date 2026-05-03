# 部署与启动

## 本地启动面向的组件

当前仓库内已有较明确启动脚本或入口的组件：

- Node Agent
- MCP Server
- VictoriaMetrics
- Grafana
- LangChain Agent API
- Web UI V2

当前仓库也提供了 OTel Collector / Jaeger 的 compose 和配置，但它们不属于默认本地启动链路。

## 现有脚本

### `ops/scripts/start-point.sh`

这是面向本地全栈中“监控栈 + Node Agent”的脚本，当前会：

1. 启动 VictoriaMetrics
2. 启动 Grafana
3. 启动 Node Agent
4. 配置 Grafana 数据源
5. 导入 Dashboard

它不负责启动：

- MCP Server
- LangChain Agent API
- Web UI V2

### `ops/scripts/status-point.sh`

用于查看：

- VictoriaMetrics
- Grafana
- Node Agent

## 推荐启动顺序

### 方案 A：完整本地研发链路

直接使用统一入口：

```bash
bash /home/ubuntu/Perfa/ops/scripts/start-all.sh
```

它会按顺序拉起：

1. 监控栈和 Node Agent
2. MCP Server
3. LangChain Agent API
4. Web UI V2

并等待关键端口就绪。

### 参考命令

```bash
# 启动
bash /home/ubuntu/Perfa/ops/scripts/start-all.sh

# 查看状态
bash /home/ubuntu/Perfa/ops/scripts/status-all.sh

# 停止
bash /home/ubuntu/Perfa/ops/scripts/stop-all.sh
```

## 远程 / 混合部署现实

当前拓扑已经单独整理在 [environments-and-topology.md](./environments-and-topology.md)。

## OTel 部署

`ops/assets/otel/` 与 `ops/compose/otel.compose.yml` 已经具备 Collector 和 Jaeger 配置，但是否启用取决于当前联调环境。

如果要让追踪真正打通，还需要确保相关进程带上：

```bash
OTEL_EXPORTER_OTLP_ENDPOINT=localhost:4317
```

## 当前注意点

- `ops/scripts/start-point.sh` 会调用 `sudo docker`，适合本地运维启动，不适合作为纯开发脚本假设。
- LangChain Agent 当前最稳定的后台启动方式，已经固化在 `ops/scripts/start-all.sh` 中。
