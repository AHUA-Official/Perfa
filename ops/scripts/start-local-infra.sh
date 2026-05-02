#!/bin/bash
# 启动本地监控栈与 Node Agent

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VM_DIR="$PROJECT_DIR/ops/assets/vm"
GRAFANA_ASSETS_DIR="$PROJECT_DIR/ops/assets/grafana"
GRAFANA_COMPOSE_FILE="$PROJECT_DIR/ops/compose/grafana.compose.yml"
AGENT_DIR="$PROJECT_DIR/src/node_agent"
NODE_AGENT_CMD="$PROJECT_DIR/src/node_agent/main.py"

if sudo -n true >/dev/null 2>&1; then
    SUDO="sudo"
else
    SUDO=""
fi

echo "================================================"
echo "    Perfa 本地基础设施启动"
echo "================================================"
echo ""

echo "[1/3] 启动 Victoria Metrics..."
if $SUDO docker ps 2>/dev/null | grep -q victoria-metrics; then
    echo "      Victoria Metrics 已在运行"
else
    $SUDO docker rm -f victoria-metrics 2>/dev/null || true

    $SUDO docker run -d --name victoria-metrics \
        -p 8428:8428 \
        -v "$VM_DIR:/config" \
        -v "$PROJECT_DIR/data/vm-storage:/victoria-metrics-data" \
        victoriametrics/victoria-metrics:latest \
        -promscrape.config=/config/vm_scrape.yml

    sleep 2
    if $SUDO docker ps 2>/dev/null | grep -q victoria-metrics; then
        echo "      ✅ Victoria Metrics 启动成功 (端口 8428)"
    else
        echo "      ❌ Victoria Metrics 启动失败"
        exit 1
    fi
fi
echo ""

echo "[2/3] 启动 Grafana..."
if $SUDO docker ps 2>/dev/null | grep -q grafana; then
    echo "      Grafana 已在运行"
else
    cd "$(dirname "$GRAFANA_COMPOSE_FILE")"
    if $SUDO docker compose -f "$GRAFANA_COMPOSE_FILE" version &>/dev/null; then
        $SUDO docker compose -f "$GRAFANA_COMPOSE_FILE" down 2>/dev/null || true
        $SUDO docker compose -f "$GRAFANA_COMPOSE_FILE" up -d
    elif $SUDO docker-compose -f "$GRAFANA_COMPOSE_FILE" version &>/dev/null; then
        $SUDO docker-compose -f "$GRAFANA_COMPOSE_FILE" down 2>/dev/null || true
        $SUDO docker-compose -f "$GRAFANA_COMPOSE_FILE" up -d
    else
        echo "      ❌ Docker Compose 未安装"
        exit 1
    fi

    sleep 3
    if $SUDO docker ps 2>/dev/null | grep -q grafana; then
        echo "      ✅ Grafana 启动成功 (端口 3000)"
    else
        echo "      ❌ Grafana 启动失败"
        exit 1
    fi
fi
echo ""

echo "[3/3] 启动 Node Agent..."
if pgrep -f "$NODE_AGENT_CMD" > /dev/null; then
    echo "      Node Agent 已在运行"
else
    cd "$AGENT_DIR"
    nohup python3 "$NODE_AGENT_CMD" > /tmp/agent.log 2>&1 &

    sleep 2
    if pgrep -f "$NODE_AGENT_CMD" > /dev/null; then
        echo "      ✅ Node Agent 启动成功"
        echo "         - 控制面板: http://localhost:8080"
        echo "         - Prometheus: http://localhost:8000/metrics"
    else
        echo "      ❌ Node Agent 启动失败，查看日志: tail -f /tmp/agent.log"
        exit 1
    fi
fi
echo ""

echo "[配置] 设置 Grafana 数据源..."
sleep 5
curl -s -X POST http://localhost:3000/api/datasources \
    -H "Content-Type: application/json" \
    -u admin:admin123 \
    -d '{"name":"VictoriaMetrics","type":"prometheus","url":"http://172.17.0.1:8428","access":"proxy","isDefault":true}' \
    > /dev/null 2>&1 || true
echo "      ✅ 数据源已配置"
echo ""

echo "[配置] 导入 Grafana Dashboard..."
DS_UID=$(curl -s http://localhost:3000/api/datasources -u admin:admin123 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d[0]['uid'] if d else '')" 2>/dev/null)

if [ -n "$DS_UID" ]; then
    DASHBOARD_FILE="$GRAFANA_ASSETS_DIR/dashboards/node-agent.json"
    python3 -c "
import json
with open('$DASHBOARD_FILE') as f:
    d = json.load(f)
for panel in d.get('panels', []):
    datasource = panel.get('datasource')
    if isinstance(datasource, dict) and datasource.get('type') == 'prometheus':
        datasource['uid'] = '$DS_UID'
    for target in panel.get('targets', []):
        target_ds = target.get('datasource')
        if isinstance(target_ds, dict) and target_ds.get('type') == 'prometheus':
            target_ds['uid'] = '$DS_UID'
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
echo "    本地基础设施启动完成"
echo "================================================"
