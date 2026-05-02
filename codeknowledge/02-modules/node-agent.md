# Node Agent

## 定位

`src/node_agent/` 是被测节点上的执行端。它直接接触操作系统和压测工具，负责四类能力：

- 资源监控
- 压测工具管理
- 压测任务执行
- HTTP API 暴露

## 代码入口

- 主入口: `src/node_agent/main.py`
- API 服务器: `src/node_agent/api/server.py`
- 路由: `src/node_agent/api/routes/`
- 监控: `src/node_agent/monitor/`
- 工具管理: `src/node_agent/tool/`
- 压测执行: `src/node_agent/benchmark/`

## 启动过程

`NodeAgent.start()` 当前会按这个顺序初始化：

1. 初始化 `ToolManager`
2. 初始化 `BenchmarkExecutor`
3. 启动 Prometheus 指标服务，默认端口 `8000`
4. 启动 `Monitor` 后台线程
5. 启动 Flask API，默认端口 `8080`

## 关键对象

### `NodeAgent`

- 保存 `monitor`、`tool_manager`、`benchmark_executor`、`api_server`
- 负责生命周期控制

### `ToolManager`

- 位于 `src/node_agent/tool/manager.py`
- 负责检查工具状态、安装、卸载和校验
- 当前支持的工具从目录和 runner 命名可见，包括：
  - `fio`
  - `stream`
  - `unixbench`
  - `mlc`
  - `superpi`
  - `hping3`

### `BenchmarkExecutor`

- 位于 `src/node_agent/benchmark/executor.py`
- 启动时注册多个 Runner
- 当前由 `main.py` 显式注册：
  - `FioRunner`
  - `StreamRunner`
  - `UnixBenchRunner`
  - `MlcRunner`
  - `SuperPiRunner`
  - `Hping3Runner`

### `Monitor`

- 位于 `src/node_agent/monitor/monitor.py`
- 采集周期默认 5 秒
- 当前启用指标类型：`cpu`、`memory`、`disk`、`network`

## API 层

当前 API Server 使用 Flask，入口是 `src/node_agent/api/server.py`。

已注册的蓝图来自：

- `health_bp`
- `monitor_bp`
- `tool_bp`
- `benchmark_bp`

根路由 `/` 会返回静态目录中的控制面板页面：`src/node_agent/api/static/index.html`。

## 模块拆分

```text
src/node_agent/
├── main.py
├── api/
├── benchmark/
│   ├── executor.py
│   ├── task.py
│   ├── result.py
│   ├── cleaner.py
│   └── runners/
├── monitor/
│   ├── monitor.py
│   ├── collectors.py
│   └── info.py
└── tool/
    ├── manager.py
    ├── base.py
    ├── cpu_tools.py
    ├── mem_tools.py
    ├── disk_tools.py
    ├── net_tools.py
    ├── binaries/
    └── sources/
```

## 对外角色

Node Agent 本身不是用户直接交互的主要入口，它主要被两类调用者使用：

- 本地运维或测试脚本通过 HTTP 调用
- MCP Server 通过 `agent_client` 访问它的 API

## 文档可信度判断

- `src/node_agent/design.md` 对模块边界、接口分类、工具清单仍然有帮助。
- 但它描述的是设计视角，不应替代 `main.py`、`api/`、`benchmark/` 的当前实现。
