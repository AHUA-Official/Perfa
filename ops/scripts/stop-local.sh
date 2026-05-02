#!/bin/bash
# 停止本地完整开发链路

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

pkill -f "langchain_agent.backend.main" 2>/dev/null || true
pkill -f "$PROJECT_DIR/src/mcp_server/main.py" 2>/dev/null || true
pkill -f "next dev" 2>/dev/null || true
bash "$SCRIPT_DIR/stop-local-infra.sh"
