#!/bin/bash
# 查看完整链路状态

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

check_get() {
    local name="$1"
    local url="$2"
    echo "$name:"
    if ! curl -sS --max-time 5 "$url"; then
        echo "UNAVAILABLE"
    fi
    echo ""
}

check_head() {
    local name="$1"
    local url="$2"
    echo "$name:"
    if ! curl -I -sS --max-time 5 "$url"; then
        echo "UNAVAILABLE"
    fi
    echo ""
}

bash "$SCRIPT_DIR/status-point.sh"
echo ""
bash "$SCRIPT_DIR/status-otel.sh"
echo ""
check_head "MCP Server" "http://127.0.0.1:9000/sse?api_key=test-key-123"
check_get "LangChain Backend" "http://127.0.0.1:10000/health"
check_head "WebUI V2" "http://127.0.0.1:3002"
echo "tmux sessions:"
for session in perfa-node-agent perfa-mcp-server perfa-langchain-backend perfa-webui-v2; do
    if tmux has-session -t "$session" 2>/dev/null; then
        echo "  ✅ $session"
    else
        echo "  ❌ $session"
    fi
done
