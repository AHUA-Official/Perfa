#!/bin/bash
# 查看 LangChain Agent 后端状态

set -e

SESSION_NAME="${PERFA_LANGCHAIN_SESSION:-perfa-langchain-backend}"

echo "LangChain Backend:"
if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "  状态: ✅ 运行中"
    echo "  tmux: $SESSION_NAME"
    echo "  HTTP: http://127.0.0.1:10000/health"
    echo "  attach: tmux attach -t $SESSION_NAME"
else
    echo "  状态: ❌ 未运行"
fi
