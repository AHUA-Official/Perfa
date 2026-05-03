#!/bin/bash
# 停止 webui-v2

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WEBUI_DIR="$PROJECT_DIR/webui-v2"
SESSION_NAME="${PERFA_WEBUI_SESSION:-perfa-webui-v2}"
LEGACY_SESSION_NAME="${PERFA_WEBUI_LEGACY_SESSION:-perfa-webui}"

if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    tmux kill-session -t "$SESSION_NAME"
fi

if tmux has-session -t "$LEGACY_SESSION_NAME" 2>/dev/null; then
    tmux kill-session -t "$LEGACY_SESSION_NAME"
fi

# 优先按工作目录匹配，避免误杀其他 Next/NPM 进程。
if pgrep -af "$WEBUI_DIR" >/dev/null 2>&1; then
    pkill -f "$WEBUI_DIR.*next dev" 2>/dev/null || true
    pkill -f "$WEBUI_DIR.*next start" 2>/dev/null || true
    pkill -f "$WEBUI_DIR.*npm run dev" 2>/dev/null || true
    pkill -f "$WEBUI_DIR.*npm exec next start" 2>/dev/null || true
fi

# 兜底匹配 Next.js 开发服务器在 3002 端口的常见命令行。
pkill -f "next dev -p 3002" 2>/dev/null || true
pkill -f "next start -p 3002" 2>/dev/null || true
pkill -f "npm run dev" 2>/dev/null || true
sleep 1

# 兜底停止占用 3002 端口的进程。
if command -v lsof >/dev/null 2>&1; then
    PIDS="$(lsof -ti tcp:3002 2>/dev/null || true)"
    if [ -n "$PIDS" ]; then
        kill $PIDS 2>/dev/null || true
        sleep 1
        PIDS="$(lsof -ti tcp:3002 2>/dev/null || true)"
        if [ -n "$PIDS" ]; then
            kill -9 $PIDS 2>/dev/null || true
        fi
    fi
fi

echo "✅ WebUI V2 已停止"
