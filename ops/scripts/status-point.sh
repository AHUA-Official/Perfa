#!/bin/bash
# 查看 point 链路状态

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if sudo -n true >/dev/null 2>&1; then
    SUDO="sudo"
else
    SUDO=""
fi

echo "================================================"
echo "    Perfa Point 状态"
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

bash "$SCRIPT_DIR/status-node-agent.sh"
