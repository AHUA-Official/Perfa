#!/bin/bash
# 停止 Node Agent

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
NODE_AGENT_CMD="$PROJECT_DIR/src/node_agent/main.py"
NODE_AGENT_SESSION="${PERFA_NODE_AGENT_SESSION:-perfa-node-agent}"

echo "停止 Node Agent..."

if tmux has-session -t "$NODE_AGENT_SESSION" 2>/dev/null; then
    tmux kill-session -t "$NODE_AGENT_SESSION"
    sleep 1
    echo "✅ Node Agent tmux session 已停止"
elif pgrep -f "$NODE_AGENT_CMD" >/dev/null 2>&1; then
    pkill -TERM -f "$NODE_AGENT_CMD"
    sleep 2
    if pgrep -f "$NODE_AGENT_CMD" >/dev/null 2>&1; then
        pkill -9 -f "$NODE_AGENT_CMD"
        sleep 1
    fi
    echo "✅ Node Agent 进程已停止"
else
    echo "Node Agent 未运行"
fi

if command -v fuser >/dev/null 2>&1; then
    if fuser 8000/tcp >/dev/null 2>&1; then
        fuser -k 8000/tcp >/dev/null 2>&1 || true
        sleep 1
    fi
fi
