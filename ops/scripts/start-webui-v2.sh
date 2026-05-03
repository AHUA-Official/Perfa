#!/bin/bash
# 启动 webui-v2

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WEBUI_DIR="$PROJECT_DIR/webui-v2"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="${PERFA_WEBUI_LOG:-$LOG_DIR/webui-v2.log}"
PORT="${PERFA_WEBUI_PORT:-3002}"
SESSION_NAME="${PERFA_WEBUI_SESSION:-perfa-webui-v2}"
LEGACY_SESSION_NAME="${PERFA_WEBUI_LEGACY_SESSION:-perfa-webui}"
MODE="${1:---tmux}"

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
mkdir -p "$LOG_DIR"
: >"$LOG_FILE"

cd "$WEBUI_DIR"

rm -rf "$WEBUI_DIR/.next"

if [ "$MODE" = "--foreground" ]; then
    exec npm run dev
fi

if ! command -v tmux &> /dev/null; then
    echo "❌ tmux 未安装"
    exit 1
fi

if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "✅ WebUI V2 已在 tmux session 中运行: $SESSION_NAME"
    echo "   tmux attach: tmux attach -t $SESSION_NAME"
    exit 0
fi

tmux new-session -d -s "$SESSION_NAME" \
    "bash -lc 'cd \"$WEBUI_DIR\" && npm run dev 2>&1 | tee -a \"$LOG_FILE\"'"

for _ in $(seq 1 10); do
    if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
        break
    fi
    sleep 1
done

if ! tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "❌ WebUI V2 tmux session 启动失败: $SESSION_NAME"
    if tmux has-session -t "$LEGACY_SESSION_NAME" 2>/dev/null; then
        echo "   检测到旧 session 仍存在: $LEGACY_SESSION_NAME"
    fi
    exit 1
fi

wait_for_http "http://127.0.0.1:$PORT" "WebUI V2" 30
echo "✅ WebUI V2 启动成功"
echo "   tmux attach: tmux attach -t $SESSION_NAME"
