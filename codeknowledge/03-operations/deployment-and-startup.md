# 部署与启动

## 本地启动面向的组件

当前仓库内已有较明确启动脚本或入口的组件：

- Node Agent
- VictoriaMetrics
- Grafana
- LangChain Agent API
- Web UI V2
- OTel Collector / Jaeger

## 现有脚本

### `ops/scripts/start-local-infra.sh`

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

### `ops/scripts/status-local-infra.sh`

用于查看：

- VictoriaMetrics
- Grafana
- Node Agent

## 推荐启动顺序

### 方案 A：完整本地研发链路

1. 启动监控栈和 Node Agent
2. 启动 MCP Server
3. 启动 LangChain Agent API
4. 启动 Web UI V2

### 参考命令

```bash
# 1. 监控栈 + Node Agent
cd /home/ubuntu/Perfa/deploy
bash /home/ubuntu/Perfa/ops/scripts/start-local-infra.sh

# 2. MCP Server
bash /home/ubuntu/Perfa/ops/scripts/start-mcp-server.sh

# 3. LangChain Agent API
bash /home/ubuntu/Perfa/ops/scripts/start-langchain-backend.sh

# 4. Web UI V2
bash /home/ubuntu/Perfa/ops/scripts/start-webui-v2.sh
```

## 远程 / 混合部署现实

根据 `doc/PROGRESS.md`，项目也存在一种混合形态：

- MCP Server 可能运行在远端
- Node Agent 可能运行在被测远端服务器
- 本机只跑 LangChain Agent 和前端

因此后续如果继续整理，建议再补一个 `environments.md`，专门描述：

- 全本地开发模式
- 本地前端 + 本地 Agent + 远程 MCP 模式
- 多被测节点模式

## OTel 部署

`ops/assets/otel/` 与 `ops/compose/otel.compose.yml` 已经具备 Collector 和 Jaeger 配置，但是否启用取决于当前联调环境。

如果要让追踪真正打通，还需要确保相关进程带上：

```bash
OTEL_EXPORTER_OTLP_ENDPOINT=localhost:4317
```

## 当前注意点

- `ops/scripts/start-local-infra.sh` 会调用 `sudo docker`，适合本地运维启动，不适合作为纯开发脚本假设。
- LangChain Agent 的启动路径要从 `src/` 层级进入，否则包导入可能不对。
