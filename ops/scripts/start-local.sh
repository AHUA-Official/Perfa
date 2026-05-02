#!/bin/bash
# 启动本地完整开发链路

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

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

echo "[1/4] 启动本地基础设施..."
bash "$SCRIPT_DIR/start-local-infra.sh"

echo "[2/4] 启动 MCP Server..."
nohup bash "$SCRIPT_DIR/start-mcp-server.sh" >/tmp/perfa_mcp.log 2>&1 &
wait_for_http "http://127.0.0.1:9000/sse?api_key=test-key-123" "MCP Server" 30 HEAD

echo "[3/4] 启动 LangChain 后端..."
setsid bash -lc "cd '$PROJECT_DIR/src' && export PYTHONPATH='$PROJECT_DIR/src':\$PYTHONPATH && exec nohup python3 -m uvicorn langchain_agent.backend.main:app --host 0.0.0.0 --port 10000 </dev/null >/tmp/perfa_backend.log 2>&1" >/dev/null 2>&1 &
wait_for_http "http://127.0.0.1:10000/health" "LangChain 后端"

echo "[4/4] 启动 WebUI V2..."
nohup bash "$SCRIPT_DIR/start-webui-v2.sh" >/tmp/perfa_webui.log 2>&1 &
wait_for_http "http://127.0.0.1:3002" "WebUI V2" 30 HEAD

echo "✅ 本地完整链路已启动"
