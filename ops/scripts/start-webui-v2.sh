#!/bin/bash
# 启动 webui-v2

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WEBUI_DIR="$PROJECT_DIR/webui-v2"
LOG_FILE="${PERFA_WEBUI_LOG:-/tmp/perfa_webui.log}"
PORT="${PERFA_WEBUI_PORT:-3002}"
MODE="${1:---daemon}"

wait_for_http() {
    local url="$1"
    local name="$2"
    local max_attempts="${3:-30}"
    local i

    for ((i=1; i<=max_attempts; i++)); do
        if curl -fsSI --max-time 5 "$url" >/dev/null 2>&1; then
            echo "✅ $name 已就绪"
            return 0
        fi
        sleep 1
    done

    echo "❌ $name 未在预期时间内就绪: $url"
    return 1
}

echo "启动 WebUI V2..."
bash "$SCRIPT_DIR/stop-webui-v2.sh" >/dev/null 2>&1 || true
: >"$LOG_FILE"

cd "$WEBUI_DIR"

if [ "$MODE" = "--foreground" ]; then
    exec npm run dev
fi

setsid bash -lc "cd '$WEBUI_DIR' && exec nohup npm run dev </dev/null >>'$LOG_FILE' 2>&1" >/dev/null 2>&1 &
sleep 1
wait_for_http "http://127.0.0.1:$PORT" "WebUI V2" 30
echo "✅ WebUI V2 启动成功，日志: $LOG_FILE"
