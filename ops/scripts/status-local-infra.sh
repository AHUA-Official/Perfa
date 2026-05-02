#!/bin/bash
# 查看本地监控栈与 Node Agent 状态

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
NODE_AGENT_CMD="$PROJECT_DIR/src/node_agent/main.py"

if sudo -n true >/dev/null 2>&1; then
    SUDO="sudo"
else
    SUDO=""
fi

echo "================================================"
echo "    Perfa 本地基础设施状态"
echo "================================================"
echo ""

echo "Victoria Metrics:"
if $SUDO docker ps 2>/dev/null | grep -q victoria-metrics; then
    echo "  状态: ✅ 运行中"
    echo "  端口: 8428"
else
    echo "  状态: ❌ 未运行"
fi
echo ""

echo "Grafana:"
if $SUDO docker ps 2>/dev/null | grep -q grafana; then
    echo "  状态: ✅ 运行中"
    echo "  端口: 3000"
else
    echo "  状态: ❌ 未运行"
fi
echo ""

echo "Node Agent:"
if pgrep -f "$NODE_AGENT_CMD" > /dev/null; then
    PID=$(pgrep -f "$NODE_AGENT_CMD")
    echo "  状态: ✅ 运行中"
    echo "  PID: $PID"
    echo "  API: http://localhost:8080/health"
    echo "  Metrics: http://localhost:8000/metrics"
else
    echo "  状态: ❌ 未运行"
fi
echo ""
