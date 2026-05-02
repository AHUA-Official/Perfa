#!/bin/bash
# 停止本地监控栈与 Node Agent

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
GRAFANA_COMPOSE_FILE="$PROJECT_DIR/ops/compose/grafana.compose.yml"
NODE_AGENT_CMD="$PROJECT_DIR/src/node_agent/main.py"

if sudo -n true >/dev/null 2>&1; then
    SUDO="sudo"
else
    SUDO=""
fi

echo "================================================"
echo "    Perfa 本地基础设施停止"
echo "================================================"
echo ""

echo "[1/3] 停止 Node Agent..."
if pgrep -f "$NODE_AGENT_CMD" > /dev/null; then
    pkill -TERM -f "$NODE_AGENT_CMD"
    sleep 2
    if pgrep -f "$NODE_AGENT_CMD" > /dev/null; then
        pkill -9 -f "$NODE_AGENT_CMD"
        sleep 1
    fi
    echo "      ✅ Node Agent 已停止"
else
    echo "      Node Agent 未运行"
fi
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
    $SUDO docker stop victoria-metrics > /dev/null 2>&1
    $SUDO docker rm victoria-metrics > /dev/null 2>&1
    echo "      ✅ Victoria Metrics 已停止"
else
    echo "      Victoria Metrics 未运行"
fi
echo ""

echo "================================================"
echo "    本地基础设施已停止"
echo "================================================"
