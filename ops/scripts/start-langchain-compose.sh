#!/bin/bash
# 启动 LangChain 依赖服务（ChromaDB）

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE_FILE="$PROJECT_DIR/ops/compose/langchain.compose.yml"

echo "启动 Perfa LangChain 依赖服务..."

cd "$PROJECT_DIR"
docker network create perfa-network 2>/dev/null || true

if command -v docker-compose &> /dev/null; then
    docker-compose -f "$COMPOSE_FILE" up -d
else
    docker compose -f "$COMPOSE_FILE" up -d
fi

echo "等待 ChromaDB 启动..."
sleep 5
echo "✓ ChromaDB 应已启动，访问地址: http://localhost:8001"
