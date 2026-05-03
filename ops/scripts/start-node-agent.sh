#!/bin/bash
# 启动 Node Agent

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
AGENT_DIR="$PROJECT_DIR/src/node_agent"
NODE_AGENT_CMD="$PROJECT_DIR/src/node_agent/main.py"
LOG_DIR="$PROJECT_DIR/logs"
AGENT_LOG_FILE="${PERFA_NODE_AGENT_LOG:-$LOG_DIR/node_agent.log}"
NODE_AGENT_SESSION="${PERFA_NODE_AGENT_SESSION:-perfa-node-agent}"

echo "启动 Node Agent..."

if ! command -v tmux >/dev/null 2>&1; then
    echo "❌ tmux 未安装"
    exit 1
fi

if tmux has-session -t "$NODE_AGENT_SESSION" 2>/dev/null; then
    echo "✅ Node Agent 已在运行 (tmux: $NODE_AGENT_SESSION)"
    echo "   attach: tmux attach -t $NODE_AGENT_SESSION"
    exit 0
fi

mkdir -p "$LOG_DIR"
tmux new-session -d -s "$NODE_AGENT_SESSION" \
    "bash -lc 'cd \"$AGENT_DIR\" && export PERFA_LOG_TO_STDOUT=true PERFA_NODE_AGENT_LOG=\"$AGENT_LOG_FILE\" && python3 \"$NODE_AGENT_CMD\"'"

sleep 2
if tmux has-session -t "$NODE_AGENT_SESSION" 2>/dev/null; then
    echo "✅ Node Agent 启动成功"
    echo "   控制面板: http://localhost:8080"
    echo "   Prometheus: http://localhost:8000/metrics"
    echo "   日志文件: $AGENT_LOG_FILE"
    echo "   attach: tmux attach -t $NODE_AGENT_SESSION"
else
    echo "❌ Node Agent 启动失败"
    exit 1
fi
