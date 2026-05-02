#!/bin/bash
# 启动旧版 Web UI

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE_FILE="$PROJECT_DIR/ops/compose/webui-legacy.compose.yml"

echo "启动 Perfa Web UI (legacy)..."

cd "$PROJECT_DIR"

if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安装，请先安装 Docker"
    exit 1
fi

if command -v docker-compose &> /dev/null; then
    docker-compose -f "$COMPOSE_FILE" up -d
elif docker compose version &> /dev/null; then
    docker compose -f "$COMPOSE_FILE" up -d
else
    echo "❌ docker-compose / docker compose 未安装，请先安装 Docker Compose"
    exit 1
fi

echo "✅ Web UI (legacy) 启动成功"
