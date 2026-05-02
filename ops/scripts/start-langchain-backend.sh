#!/bin/bash
# 启动 LangChain Agent 后端

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LANGCHAIN_DIR="$PROJECT_DIR/src/langchain_agent"
SRC_DIR="$PROJECT_DIR/src"

echo "启动 Perfa Agent 后端..."

if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装"
    exit 1
fi

python3 -c "import fastapi, uvicorn" 2>/dev/null || {
    echo "安装依赖..."
    pip3 install fastapi uvicorn sse-starlette
}

if [ -f "$LANGCHAIN_DIR/.env" ]; then
    echo "加载环境变量: $LANGCHAIN_DIR/.env"
    export $(grep -v '^#' "$LANGCHAIN_DIR/.env" | xargs)
fi

PORT=${LANGCHAIN_API_PORT:-10000}
export PYTHONPATH="$SRC_DIR:$PYTHONPATH"

cd "$SRC_DIR"
python3 -m uvicorn langchain_agent.backend.main:app --host 0.0.0.0 --port "$PORT"
