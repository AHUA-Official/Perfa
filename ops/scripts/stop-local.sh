#!/bin/bash
# 停止本地完整开发链路

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MCP_PID_FILE="/tmp/perfa_mcp.pid"

pkill -f "langchain_agent.backend.main" 2>/dev/null || true
if [ -f "$MCP_PID_FILE" ]; then
    MCP_PID="$(cat "$MCP_PID_FILE" 2>/dev/null || true)"
    if [ -n "$MCP_PID" ]; then
        kill "$MCP_PID" 2>/dev/null || true
    fi
    rm -f "$MCP_PID_FILE"
fi
pkill -f "$PROJECT_DIR/src/mcp_server/main.py" 2>/dev/null || true
pkill -f "python3 main.py" 2>/dev/null || true
bash "$SCRIPT_DIR/stop-webui-v2.sh"
bash "$SCRIPT_DIR/stop-local-infra.sh"
