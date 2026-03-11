#!/bin/bash
# Perfa 全栈状态检查脚本

PROJECT_DIR="/home/ubuntu/Perfa"

echo "================================================"
echo "    Perfa 服务状态"
echo "================================================"
echo ""

# Victoria Metrics
echo "Victoria Metrics:"
if sudo docker ps | grep -q victoria-metrics; then
    echo "  状态: ✅ 运行中"
    echo "  端口: 8428"
    echo "  UI: http://localhost:8428/vmui"
else
    echo "  状态: ❌ 未运行"
fi
echo ""

# Grafana
echo "Grafana:"
if sudo docker ps | grep -q grafana; then
    echo "  状态: ✅ 运行中"
    echo "  端口: 3000"
    echo "  UI: http://localhost:3000"
else
    echo "  状态: ❌ 未运行"
fi
echo ""

# Node Agent
echo "Node Agent:"
if pgrep -f "python3 main.py" > /dev/null; then
    PID=$(pgrep -f "python3 main.py")
    echo "  状态: ✅ 运行中"
    echo "  PID: $PID"
    echo "  端口: 8000"
    echo "  Metrics: http://localhost:8000/metrics"
    echo "  日志: /tmp/agent.log"
else
    echo "  状态: ❌ 未运行"
fi
echo ""

# 数据目录
echo "数据目录:"
echo "  VM 存储: $PROJECT_DIR/data/vm-storage"
if [ -d "$PROJECT_DIR/data/vm-storage" ]; then
    SIZE=$(du -sh $PROJECT_DIR/data/vm-storage 2>/dev/null | cut -f1)
    echo "  大小: $SIZE"
fi
echo ""

echo "================================================"
