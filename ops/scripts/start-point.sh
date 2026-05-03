#!/bin/bash
# 启动 point 链路：Victoria Metrics + Grafana + Node Agent

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
VM_DIR="$PROJECT_DIR/ops/assets/vm"
GRAFANA_ASSETS_DIR="$PROJECT_DIR/ops/assets/grafana"
GRAFANA_COMPOSE_FILE="$PROJECT_DIR/ops/compose/grafana.compose.yml"

if sudo -n true >/dev/null 2>&1; then
    SUDO="sudo"
else
    SUDO=""
fi

echo "================================================"
echo "    Perfa Point 启动"
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
cd "$(dirname "$GRAFANA_COMPOSE_FILE")"
if $SUDO docker compose -f "$GRAFANA_COMPOSE_FILE" version &>/dev/null; then
    if $SUDO docker ps -a --format '{{.Names}}' 2>/dev/null | grep -qx grafana; then
        current_project="$($SUDO docker inspect -f '{{ index .Config.Labels "com.docker.compose.project" }}' grafana 2>/dev/null || true)"
        current_config="$($SUDO docker inspect -f '{{ index .Config.Labels "com.docker.compose.project.config_files" }}' grafana 2>/dev/null || true)"
        if [ -z "$current_project" ] || [ "$current_config" != "$GRAFANA_COMPOSE_FILE" ]; then
            echo "      发现非当前 compose 管理的 grafana 容器，先移除后重建"
            $SUDO docker rm -f grafana >/dev/null 2>&1 || true
        fi
    fi
    $SUDO docker compose -f "$GRAFANA_COMPOSE_FILE" up -d --force-recreate
elif $SUDO docker-compose -f "$GRAFANA_COMPOSE_FILE" version &>/dev/null; then
    if $SUDO docker ps -a --format '{{.Names}}' 2>/dev/null | grep -qx grafana; then
        current_project="$($SUDO docker inspect -f '{{ index .Config.Labels "com.docker.compose.project" }}' grafana 2>/dev/null || true)"
        current_config="$($SUDO docker inspect -f '{{ index .Config.Labels "com.docker.compose.project.config_files" }}' grafana 2>/dev/null || true)"
        if [ -z "$current_project" ] || [ "$current_config" != "$GRAFANA_COMPOSE_FILE" ]; then
            echo "      发现非当前 compose 管理的 grafana 容器，先移除后重建"
            $SUDO docker rm -f grafana >/dev/null 2>&1 || true
        fi
    fi
    $SUDO docker-compose -f "$GRAFANA_COMPOSE_FILE" up -d --force-recreate
else
    echo "      ❌ Docker Compose 未安装"
    exit 1
fi
sleep 3
if $SUDO docker ps 2>/dev/null | grep -q grafana; then
    echo "      ✅ Grafana 已按 compose 配置运行 (端口 3000)"
else
    echo "      ❌ Grafana 启动失败"
    exit 1
fi
echo ""

echo "[3/3] 启动 Node Agent..."
bash "$SCRIPT_DIR/start-node-agent.sh"
echo ""

echo "[配置] 设置 Grafana 数据源..."
sleep 5
curl -s -X POST http://localhost:3000/api/datasources \
    -H "Content-Type: application/json" \
    -u admin:admin123 \
    -d '{"name":"VictoriaMetrics","type":"prometheus","url":"http://172.17.0.1:8428","access":"proxy","isDefault":true}' \
    >/dev/null 2>&1 || true
echo "      ✅ 数据源已配置"
echo ""

echo "[配置] 导入 Grafana Dashboard..."
DS_UID=$(curl -s http://localhost:3000/api/datasources -u admin:admin123 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d[0]['uid'] if d else '')" 2>/dev/null || true)

if [ -n "$DS_UID" ]; then
    DASHBOARD_FILE="$GRAFANA_ASSETS_DIR/dashboards/node-agent.json"
    if python3 -c "
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
    -d @- >/dev/null 2>&1; then
        echo "      ✅ Dashboard 已导入"
    else
        echo "      ⚠️  Dashboard 导入失败，请手动导入"
    fi
else
    echo "      ⚠️  Dashboard 导入失败，请手动导入"
fi
echo ""

echo "================================================"
echo "    Point 启动完成"
echo "================================================"
