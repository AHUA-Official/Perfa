#!/bin/bash
# 停止 OTel Collector + Jaeger

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE_FILE="$PROJECT_DIR/ops/compose/otel.compose.yml"

echo "停止 OTel / Jaeger..."

cd "$PROJECT_DIR"
if command -v docker-compose &> /dev/null; then
    docker-compose -f "$COMPOSE_FILE" down
else
    docker compose -f "$COMPOSE_FILE" down
fi

echo "✓ OTel / Jaeger 已停止"
