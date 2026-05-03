#!/bin/bash
# 启动 OTel Collector + Jaeger

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE_FILE="$PROJECT_DIR/ops/compose/otel.compose.yml"

echo "启动 OTel / Jaeger..."

cd "$PROJECT_DIR"
docker network create perfa-network 2>/dev/null || true

if command -v docker-compose &> /dev/null; then
    docker-compose -f "$COMPOSE_FILE" up -d
else
    docker compose -f "$COMPOSE_FILE" up -d
fi

echo "等待 Jaeger 启动..."
sleep 5
echo "✓ OTel / Jaeger 应已启动，访问地址: http://127.0.0.1:16686/api/monitor/jaeger"
