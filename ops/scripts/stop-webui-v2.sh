#!/bin/bash
# 停止 webui-v2

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WEBUI_DIR="$PROJECT_DIR/webui-v2"

# 优先按工作目录匹配，避免误杀其他 Next/NPM 进程。
if pgrep -af "$WEBUI_DIR" >/dev/null 2>&1; then
    pkill -f "$WEBUI_DIR.*next dev" 2>/dev/null || true
    pkill -f "$WEBUI_DIR.*next start" 2>/dev/null || true
    pkill -f "$WEBUI_DIR.*npm run dev" 2>/dev/null || true
    pkill -f "$WEBUI_DIR.*npm exec next start" 2>/dev/null || true
fi

# 兜底停止占用 3002 端口的进程。
if command -v lsof >/dev/null 2>&1; then
    PIDS="$(lsof -ti tcp:3002 2>/dev/null || true)"
    if [ -n "$PIDS" ]; then
        kill $PIDS 2>/dev/null || true
    fi
fi

echo "✅ WebUI V2 已停止"
