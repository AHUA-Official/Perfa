#!/bin/bash
# 停止 MCP Server

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MCP_DIR="$PROJECT_DIR/src/mcp_server"
SESSION_NAME="${PERFA_MCP_SESSION:-perfa-mcp-server}"

echo "停止 MCP Server..."

if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    tmux kill-session -t "$SESSION_NAME"
    echo "✅ MCP Server tmux session 已停止"
elif pgrep -f "$MCP_DIR/main.py" >/dev/null 2>&1; then
    pkill -f "$MCP_DIR/main.py" 2>/dev/null || true
    echo "✅ MCP Server 进程已停止"
else
    echo "MCP Server 未运行"
fi
