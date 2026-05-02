#!/bin/bash
# 启动 MCP Server

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MCP_DIR="$PROJECT_DIR/src/mcp_server"

echo "======================================"
echo "  MCP Server 启动脚本"
echo "======================================"

if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到 Python3"
    exit 1
fi

cd "$MCP_DIR"

if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
fi

source venv/bin/activate
pip install -q -r requirements.txt

export MCP_API_KEY="${MCP_API_KEY:-test-key-123}"
export MCP_DB_PATH="${MCP_DB_PATH:-/tmp/perfa_mcp.db}"
export MCP_HOST="${MCP_HOST:-0.0.0.0}"
export MCP_PORT="${MCP_PORT:-9000}"

echo "配置:"
echo "  Host: $MCP_HOST"
echo "  Port: $MCP_PORT"
echo "  API Key: $MCP_API_KEY"
echo "  Database: $MCP_DB_PATH"

if lsof -Pi :"$MCP_PORT" -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "警告: 端口 $MCP_PORT 已被占用"
fi

python3 main.py
