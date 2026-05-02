#!/bin/bash
# 停止 LangChain 依赖服务（ChromaDB）

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE_FILE="$PROJECT_DIR/ops/compose/langchain.compose.yml"

echo "停止 Perfa LangChain 依赖服务..."

cd "$PROJECT_DIR"
if command -v docker-compose &> /dev/null; then
    docker-compose -f "$COMPOSE_FILE" down
else
    docker compose -f "$COMPOSE_FILE" down
fi

echo "✓ 所有服务已停止"
