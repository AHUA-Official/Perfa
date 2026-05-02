#!/bin/bash
# Perfa 全栈停止脚本
# 停止顺序: Node Agent -> Grafana -> Victoria Metrics

set -e

NODE_AGENT_CMD="/home/ubuntu/Perfa/src/node_agent/main.py"

echo "================================================"
echo "    Perfa 全栈停止"
echo "================================================"
echo ""

# 1. 停止 Node Agent
echo "[1/3] 停止 Node Agent..."
if pgrep -f "$NODE_AGENT_CMD" > /dev/null; then
    # 先发送 SIGTERM 优雅停止
    pkill -TERM -f "$NODE_AGENT_CMD"
    sleep 2
    
    # 如果还在运行，强制杀死
    if pgrep -f "$NODE_AGENT_CMD" > /dev/null; then
        pkill -9 -f "$NODE_AGENT_CMD"
        sleep 1
    fi
    echo "      ✅ Node Agent 已停止"
else
    echo "      Node Agent 未运行"
fi
echo ""

# 2. 停止 Grafana
echo "[2/3] 停止 Grafana..."
if sudo docker ps | grep -q grafana; then
    # 兼容新旧版本 Docker Compose
    if sudo docker compose version &>/dev/null; then
        sudo docker compose down 2>/dev/null || true
    elif sudo docker-compose version &>/dev/null; then
        sudo docker-compose down 2>/dev/null || true
    else
        sudo docker stop grafana 2>/dev/null || true
        sudo docker rm grafana 2>/dev/null || true
    fi
    echo "      ✅ Grafana 已停止"
else
    echo "      Grafana 未运行"
fi
echo ""

# 3. 停止 Victoria Metrics
echo "[3/3] 停止 Victoria Metrics..."
if sudo docker ps | grep -q victoria-metrics; then
    sudo docker stop victoria-metrics > /dev/null 2>&1
    sudo docker rm victoria-metrics > /dev/null 2>&1
    echo "      ✅ Victoria Metrics 已停止"
else
    echo "      Victoria Metrics 未运行"
fi
echo ""

echo "================================================"
echo "    全部服务已停止"
echo "================================================"
