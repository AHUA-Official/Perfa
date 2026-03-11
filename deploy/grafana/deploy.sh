#!/bin/bash
# Grafana 一键部署脚本

set -e

DEPLOY_DIR="/home/ubuntu/Perfa/deploy/grafana"

echo "=== 部署 Grafana ==="

cd "$DEPLOY_DIR"

# 创建必要目录
mkdir -p provisioning/datasources
mkdir -p provisioning/dashboards
mkdir -p dashboards

echo "启动 Grafana..."
sudo docker compose up -d

echo ""
echo "等待 Grafana 启动..."
sleep 5

echo ""
echo "✅ Grafana 部署完成!"
echo ""
echo "访问地址: http://<服务器IP>:3000"
echo "默认账号: admin"
echo "默认密码: admin123"
echo ""
echo "数据源已自动配置: VictoriaMetrics (http://127.0.0.1:8428)"
echo "Dashboard 已自动加载: Node Agent 监控面板"
