#!/bin/bash
# 查看 MCP Server 状态

set -e

SESSION_NAME="${PERFA_MCP_SESSION:-perfa-mcp-server}"

echo "MCP Server:"
if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "  状态: ✅ 运行中"
    echo "  tmux: $SESSION_NAME"
    echo "  SSE: http://127.0.0.1:9000/sse?api_key=test-key-123"
    echo "  attach: tmux attach -t $SESSION_NAME"
else
    echo "  状态: ❌ 未运行"
fi
