#!/bin/bash
# 停止 point 链路：Node Agent + Grafana + Victoria Metrics

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
GRAFANA_COMPOSE_FILE="$PROJECT_DIR/ops/compose/grafana.compose.yml"

if sudo -n true >/dev/null 2>&1; then
    SUDO="sudo"
else
    SUDO=""
fi

echo "================================================"
echo "    Perfa Point 停止"
echo "================================================"
echo ""

echo "[1/3] 停止 Node Agent..."
bash "$SCRIPT_DIR/stop-node-agent.sh"
echo ""

echo "[2/3] 停止 Grafana..."
if $SUDO docker ps 2>/dev/null | grep -q grafana; then
    if $SUDO docker compose -f "$GRAFANA_COMPOSE_FILE" version &>/dev/null; then
        $SUDO docker compose -f "$GRAFANA_COMPOSE_FILE" down 2>/dev/null || true
    elif $SUDO docker-compose -f "$GRAFANA_COMPOSE_FILE" version &>/dev/null; then
        $SUDO docker-compose -f "$GRAFANA_COMPOSE_FILE" down 2>/dev/null || true
    else
        $SUDO docker stop grafana 2>/dev/null || true
        $SUDO docker rm grafana 2>/dev/null || true
    fi
    echo "      ✅ Grafana 已停止"
else
    echo "      Grafana 未运行"
fi
echo ""

echo "[3/3] 停止 Victoria Metrics..."
if $SUDO docker ps 2>/dev/null | grep -q victoria-metrics; then
    $SUDO docker stop victoria-metrics >/dev/null 2>&1
    $SUDO docker rm victoria-metrics >/dev/null 2>&1
    echo "      ✅ Victoria Metrics 已停止"
else
    echo "      Victoria Metrics 未运行"
fi
echo ""

echo "================================================"
echo "    Point 已停止"
echo "================================================"
