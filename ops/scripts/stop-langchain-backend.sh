#!/bin/bash
# 停止 LangChain Agent 后端

set -e

SESSION_NAME="${PERFA_LANGCHAIN_SESSION:-perfa-langchain-backend}"

echo "停止 LangChain 后端..."

if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    tmux kill-session -t "$SESSION_NAME"
    echo "✅ LangChain 后端 tmux session 已停止"
else
    pkill -f "langchain_agent.backend.main" 2>/dev/null || true
    echo "LangChain 后端未运行或已停止"
fi
