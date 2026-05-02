# 环境与拓扑

这个文件只描述当前代码和当前可运行脚本支持的拓扑，不复述已删除旧文档里的历史方案。

## 本地完整开发链路

当前最直接、已实跑通过的统一入口是：

```bash
bash /home/ubuntu/Perfa/ops/scripts/start-local.sh
```

对应拓扑：

```text
浏览器
  -> webui-v2 (:3002)
  -> langchain_agent (:10000)
  -> mcp_server (:9000)
  -> node_agent (:8080)

node_agent metrics (:8000)
  -> VictoriaMetrics (:8428)
  -> Grafana (:3000)
```

## 本地基础设施模式

如果只需要监控栈和执行端，入口是：

```bash
bash /home/ubuntu/Perfa/ops/scripts/start-local-infra.sh
```

对应拓扑：

```text
node_agent (:8080 / :8000)
  -> VictoriaMetrics (:8428)
  -> Grafana (:3000)
```

这条模式不启动：

- `mcp_server`
- `langchain_agent`
- `webui-v2`

## 混合模式

从当前代码实现看，系统支持混合部署，但仓库中现成、统一且已验证的入口仍以本地模式为主。

代码层支持的混合拓扑是：

```text
浏览器
  -> 本机 webui-v2
  -> 本机 langchain_agent
  -> 本机或远端 mcp_server
  -> 一个或多个远端 node_agent
```

依据：

- `langchain_agent` 通过 MCP SSE 地址连接 `mcp_server`
- `mcp_server` 通过 `agent_client/` 访问 `node_agent`
- `DeployAgentTool` / `UninstallAgentTool` 已切换到 `ops/scripts/start-local-infra.sh` 和 `ops/scripts/stop-local-infra.sh`

## 远端节点模式

对远端被测机，更符合当前代码现实的理解是：

```text
控制机
  -> mcp_server
  -> HTTP / SSH
  -> 远端服务器上的 node_agent
```

## 当前结论

- 最可靠、最完整、已实跑验证的标准模式是本地完整开发链路。
- `ops/scripts/start-local.sh` 是当前统一总入口。
- 混合模式在代码上成立，但仓库里还没有比本地链路更完整的统一一键脚本。
- 阅读和维护时，应优先把 `ops/` 视为运行入口，把 `src/` 视为实现入口。
