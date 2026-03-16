#!/bin/bash
# Perfa 全栈启动脚本
# 启动顺序: Victoria Metrics -> Grafana -> Node Agent

set -e

# 自动检测脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
VM_DIR="$PROJECT_DIR/deploy/vm"
GRAFANA_DIR="$PROJECT_DIR/deploy/grafana"
AGENT_DIR="$PROJECT_DIR/src/node_agent"

echo "================================================"
echo "    Perfa 全栈启动"
echo "================================================"
echo ""

# 1. 启动 Victoria Metrics
echo "[1/3] 启动 Victoria Metrics..."
if sudo docker ps | grep -q victoria-metrics; then
    echo "      Victoria Metrics 已在运行"
else
    # 清理可能存在的旧容器
    sudo docker rm -f victoria-metrics 2>/dev/null || true
    
    sudo docker run -d --name victoria-metrics \
        -p 8428:8428 \
        -v $VM_DIR:/config \
        -v $PROJECT_DIR/data/vm-storage:/victoria-metrics-data \
        victoriametrics/victoria-metrics:latest \
        -promscrape.config=/config/vm_scrape.yml
    
    sleep 2
    if sudo docker ps | grep -q victoria-metrics; then
        echo "      ✅ Victoria Metrics 启动成功 (端口 8428)"
    else
        echo "      ❌ Victoria Metrics 启动失败"
        exit 1
    fi
fi
echo ""

# 2. 启动 Grafana
echo "[2/3] 启动 Grafana..."
if sudo docker ps | grep -q grafana; then
    echo "      Grafana 已在运行"
else
    # 清理可能存在的旧容器
    cd $GRAFANA_DIR
    sudo docker compose down 2>/dev/null || sudo docker-compose down 2>/dev/null || true
    
    # 兼容新旧版本 Docker Compose
    if sudo docker compose version &>/dev/null; then
        sudo docker compose up -d
    elif sudo docker-compose version &>/dev/null; then
        sudo docker-compose up -d
    else
        echo "      ❌ Docker Compose 未安装"
        exit 1
    fi
    
    sleep 3
    if sudo docker ps | grep -q grafana; then
        echo "      ✅ Grafana 启动成功 (端口 3000)"
    else
        echo "      ❌ Grafana 启动失败"
        exit 1
    fi
fi
echo ""

# 3. 启动 Node Agent
echo "[3/3] 启动 Node Agent..."
if pgrep -f "python3 main.py" > /dev/null; then
    echo "      Node Agent 已在运行"
else
    cd $AGENT_DIR
    nohup python3 main.py > /tmp/agent.log 2>&1 &
    
    sleep 2
    if pgrep -f "python3 main.py" > /dev/null; then
        echo "      ✅ Node Agent 启动成功"
        echo "         - 控制面板: http://localhost:8080"
        echo "         - Prometheus: http://localhost:8000/metrics"
    else
        echo "      ❌ Node Agent 启动失败，查看日志: tail -f /tmp/agent.log"
        exit 1
    fi
fi
echo ""

# 4. 配置 Grafana 数据源
echo "[配置] 设置 Grafana 数据源..."
sleep 5
curl -s -X POST http://localhost:3000/api/datasources \
    -H "Content-Type: application/json" \
    -u admin:admin123 \
    -d '{"name":"VictoriaMetrics","type":"prometheus","url":"http://172.17.0.1:8428","access":"proxy","isDefault":true}' \
    > /dev/null 2>&1 || true
echo "      ✅ 数据源已配置"
echo ""

# 5. 导入 Dashboard
echo "[配置] 导入 Grafana Dashboard..."
# 获取数据源 UID
DS_UID=$(curl -s http://localhost:3000/api/datasources -u admin:admin123 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d[0]['uid'] if d else '')" 2>/dev/null)

if [ -n "$DS_UID" ]; then
    # 更新 Dashboard 中的数据源 UID
    DASHBOARD_FILE="$GRAFANA_DIR/dashboards/node-agent.json"
    sed -i "s/\"uid\": \"victoriametrics\"/\"uid\": \"$DS_UID\"/g" "$DASHBOARD_FILE" 2>/dev/null || true
    sed -i "s/\"uid\": \"[a-z0-9]*\"/\"uid\": \"$DS_UID\"/g" "$DASHBOARD_FILE" 2>/dev/null || true
    
    # 导入 Dashboard
    python3 -c "
import json
with open('$DASHBOARD_FILE') as f:
    d = json.load(f)
payload = {'dashboard': d, 'overwrite': True}
print(json.dumps(payload))
" | curl -s -X POST http://localhost:3000/api/dashboards/db \
    -H "Content-Type: application/json" \
    -u admin:admin123 \
    -d @- > /dev/null 2>&1
    
    echo "      ✅ Dashboard 已导入"
else
    echo "      ⚠️  Dashboard 导入失败，请手动导入"
fi
echo ""

echo "================================================"
echo "    全部服务启动完成！"
echo "================================================"
echo ""
echo "访问地址:"
echo "  - 控制面板: http://localhost:8080/"
echo "  - Agent API: http://localhost:8080/health"
echo "  - Victoria Metrics: http://localhost:8428"
echo "  - Victoria Metrics UI: http://localhost:8428/vmui"
echo "  - Grafana: http://localhost:3000 (admin/admin123)"
echo "  - Grafana Dashboard: http://localhost:3000/d/node-agent-dashboard"
echo "  - Agent Metrics: http://localhost:8000/metrics"
echo ""
echo "日志位置:"
echo "  - Agent: /tmp/agent.log"
echo "  - VM: sudo docker logs victoria-metrics"
echo "  - Grafana: sudo docker logs grafana"
