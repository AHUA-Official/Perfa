#!/bin/bash
# 查看本地完整开发链路状态

set -e

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

check_get "Node Agent" "http://127.0.0.1:8080/health"
check_head "MCP Server" "http://127.0.0.1:9000/sse?api_key=test-key-123"
check_get "LangChain Backend" "http://127.0.0.1:10000/health"
check_head "WebUI V2" "http://127.0.0.1:3002"
