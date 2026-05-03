#!/bin/bash
# 启动完整链路

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

wait_for_http() {
    local url="$1"
    local name="$2"
    local max_attempts="${3:-30}"
    local method="${4:-GET}"
    local i

    for ((i=1; i<=max_attempts; i++)); do
        if [ "$method" = "HEAD" ]; then
            if curl -fsSI --max-time 5 "$url" >/dev/null 2>&1; then
                echo "   ✅ $name 已就绪"
                return 0
            fi
        elif curl -fsS --max-time 5 "$url" >/dev/null 2>&1; then
            echo "   ✅ $name 已就绪"
            return 0
        fi
        sleep 1
    done

    echo "   ❌ $name 未在预期时间内就绪: $url"
    return 1
}

echo "[1/5] 启动 Point..."
bash "$SCRIPT_DIR/start-point.sh"

echo "[2/5] 启动 OTel / Jaeger..."
bash "$SCRIPT_DIR/start-otel.sh"
wait_for_http "http://127.0.0.1:16686/api/monitor/jaeger" "Jaeger" 30 HEAD

echo "[3/5] 启动 MCP Server..."
bash "$SCRIPT_DIR/start-mcp-server.sh" --tmux
wait_for_http "http://127.0.0.1:9000/sse?api_key=test-key-123" "MCP Server" 30 HEAD

echo "[4/5] 启动 LangChain 后端..."
bash "$SCRIPT_DIR/start-langchain-backend.sh" --tmux
wait_for_http "http://127.0.0.1:10000/health" "LangChain 后端"

echo "[5/5] 启动 WebUI V2..."
bash "$SCRIPT_DIR/start-webui-v2.sh" --tmux
wait_for_http "http://127.0.0.1:3002" "WebUI V2" 30 HEAD

echo "✅ All 已启动"
