#!/bin/bash
# 查看 WebUI V2 状态

set -e

SESSION_NAME="${PERFA_WEBUI_SESSION:-perfa-webui-v2}"

echo "WebUI V2:"
if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "  状态: ✅ 运行中"
    echo "  tmux: $SESSION_NAME"
    echo "  HTTP: http://127.0.0.1:3002"
    echo "  attach: tmux attach -t $SESSION_NAME"
else
    echo "  状态: ❌ 未运行"
fi
