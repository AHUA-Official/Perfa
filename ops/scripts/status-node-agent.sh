#!/bin/bash
# 查看 Node Agent 状态

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
NODE_AGENT_CMD="$PROJECT_DIR/src/node_agent/main.py"
NODE_AGENT_SESSION="${PERFA_NODE_AGENT_SESSION:-perfa-node-agent}"

echo "Node Agent:"
if tmux has-session -t "$NODE_AGENT_SESSION" 2>/dev/null; then
    echo "  状态: ✅ 运行中"
    echo "  tmux: $NODE_AGENT_SESSION"
    echo "  API: http://localhost:8080/health"
    echo "  Metrics: http://localhost:8000/metrics"
    echo "  attach: tmux attach -t $NODE_AGENT_SESSION"
elif pgrep -f "$NODE_AGENT_CMD" >/dev/null 2>&1; then
    PID=$(pgrep -f "$NODE_AGENT_CMD")
    echo "  状态: ⚠️ 进程在运行，但不在 tmux"
    echo "  PID: $PID"
else
    echo "  状态: ❌ 未运行"
fi
