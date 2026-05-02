#!/bin/bash
# Grafana 一键部署脚本

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE_FILE="$PROJECT_DIR/ops/compose/grafana.compose.yml"

echo "=== 部署 Grafana ==="

if sudo -n true >/dev/null 2>&1; then
    SUDO="sudo"
else
    SUDO=""
fi

cd "$(dirname "$COMPOSE_FILE")"
$SUDO docker compose -f "$COMPOSE_FILE" up -d

echo ""
echo "等待 Grafana 启动..."
sleep 5

echo ""
echo "✅ Grafana 部署完成!"
echo "访问地址: http://<服务器IP>:3000"
