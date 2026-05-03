#!/bin/bash
# 启动 MCP Server

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MCP_DIR="$PROJECT_DIR/src/mcp_server"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="${PERFA_MCP_SERVER_LOG:-$LOG_DIR/mcp_server.log}"
SESSION_NAME="${PERFA_MCP_SESSION:-perfa-mcp-server}"
MODE="${1:---tmux}"

echo "======================================"
echo "  MCP Server 启动脚本"
echo "======================================"

if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到 Python3"
    exit 1
fi

cd "$MCP_DIR"
mkdir -p "$LOG_DIR"

if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
fi

source venv/bin/activate
pip install -q -r requirements.txt

export MCP_API_KEY="${MCP_API_KEY:-test-key-123}"
export MCP_DB_PATH="${MCP_DB_PATH:-$PROJECT_DIR/data/mcp/perfa_mcp.db}"
export MCP_HOST="${MCP_HOST:-0.0.0.0}"
export MCP_PORT="${MCP_PORT:-9000}"

echo "配置:"
echo "  Host: $MCP_HOST"
echo "  Port: $MCP_PORT"
echo "  API Key: $MCP_API_KEY"
echo "  Database: $MCP_DB_PATH"

if lsof -Pi :"$MCP_PORT" -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "警告: 端口 $MCP_PORT 已被占用"
fi

if [ "$MODE" = "--foreground" ]; then
    exec python3 main.py
fi

if ! command -v tmux &> /dev/null; then
    echo "错误: 未找到 tmux"
    exit 1
fi

if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "MCP Server 已在 tmux session 中运行: $SESSION_NAME"
    echo "日志: $LOG_FILE"
    echo "attach: tmux attach -t $SESSION_NAME"
    exit 0
fi

tmux new-session -d -s "$SESSION_NAME" \
    "bash -lc 'cd \"$MCP_DIR\" && source venv/bin/activate && export MCP_API_KEY=\"$MCP_API_KEY\" MCP_DB_PATH=\"$MCP_DB_PATH\" MCP_HOST=\"$MCP_HOST\" MCP_PORT=\"$MCP_PORT\" PERFA_LOG_TO_STDOUT=true PERFA_MCP_SERVER_LOG=\"$LOG_FILE\" && python3 main.py'"

echo "MCP Server 已在 tmux session 中启动: $SESSION_NAME"
echo "日志: $LOG_FILE"
echo "attach: tmux attach -t $SESSION_NAME"
