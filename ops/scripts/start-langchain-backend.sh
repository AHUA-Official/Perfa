#!/bin/bash
# 启动 LangChain Agent 后端

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LANGCHAIN_DIR="$PROJECT_DIR/src/langchain_agent"
SRC_DIR="$PROJECT_DIR/src"
LOG_DIR="$PROJECT_DIR/logs"
SESSION_NAME="${PERFA_LANGCHAIN_SESSION:-perfa-langchain-backend}"
MODE="${1:---tmux}"

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

if [ "$MODE" = "--foreground" ]; then
    cd "$SRC_DIR"
    exec python3 -m uvicorn langchain_agent.backend.main:app --host 0.0.0.0 --port "$PORT"
fi

if ! command -v tmux &> /dev/null; then
    echo "❌ tmux 未安装"
    exit 1
fi

mkdir -p "$LOG_DIR"

if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "✓ LangChain 后端已在 tmux session 中运行: $SESSION_NAME"
    echo "  attach: tmux attach -t $SESSION_NAME"
    exit 0
fi

cd "$SRC_DIR"
tmux new-session -d -s "$SESSION_NAME" \
    "bash -lc 'cd \"$SRC_DIR\" && export PYTHONPATH=\"$SRC_DIR\":\$PYTHONPATH && python3 -m uvicorn langchain_agent.backend.main:app --host 0.0.0.0 --port \"$PORT\"'"

echo "✓ LangChain 后端已在 tmux session 中启动: $SESSION_NAME"
echo "  attach: tmux attach -t $SESSION_NAME"
