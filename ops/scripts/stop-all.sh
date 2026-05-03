#!/bin/bash
# 停止完整链路

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

bash "$SCRIPT_DIR/stop-langchain-backend.sh"
bash "$SCRIPT_DIR/stop-mcp-server.sh"
bash "$SCRIPT_DIR/stop-webui-v2.sh"
bash "$SCRIPT_DIR/stop-otel.sh"
bash "$SCRIPT_DIR/stop-point.sh"
