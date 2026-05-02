# Ops Layout

`ops/` 是 Perfa 仓库中统一承载运行、部署、compose 与运维资源的目录。

## 目录

```text
ops/
├── README.md
├── scripts/
├── compose/
└── assets/
```

## 约定

- `scripts/` 只放启动、停止、状态、部署脚本
- `compose/` 只放 compose 文件
- `assets/` 只放 Grafana / OTel / VM 等部署资源
- `src/`、`webui-v2/` 等代码目录不再承担运维入口职责
