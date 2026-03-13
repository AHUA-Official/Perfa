#!/bin/bash

# MCP Server 快速启动脚本

echo "======================================"
echo "  MCP Server 启动脚本"
echo "======================================"

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到 Python3"
    exit 1
fi

# 检查依赖
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
fi

echo "激活虚拟环境..."
source venv/bin/activate

echo "安装依赖..."
pip install -q -r requirements.txt

# 设置默认环境变量
if [ -z "$MCP_API_KEY" ]; then
    export MCP_API_KEY="test-key-123"
    echo "警告: 使用默认 API Key (仅用于测试)"
fi

if [ -z "$MCP_DB_PATH" ]; then
    export MCP_DB_PATH="./mcp.db"
fi

if [ -z "$MCP_HOST" ]; then
    export MCP_HOST="0.0.0.0"
fi

if [ -z "$MCP_PORT" ]; then
    export MCP_PORT="9000"
fi

echo ""
echo "配置:"
echo "  Host: $MCP_HOST"
echo "  Port: $MCP_PORT"
echo "  API Key: $MCP_API_KEY"
echo "  Database: $MCP_DB_PATH"
echo ""

# 检查端口是否被占用
if lsof -Pi :$MCP_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "警告: 端口 $MCP_PORT 已被占用"
    echo "尝试停止旧进程..."
    lsof -ti:$MCP_PORT | xargs kill -9 2>/dev/null
    sleep 1
fi

echo "启动 MCP Server..."
python main.py
