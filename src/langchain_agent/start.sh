#!/bin/bash

# 同时启动 CLI 和 Web 两种模式

cd "$(dirname "$0")/.."

# 设置 Python 路径
export PYTHONPATH=/home/ubuntu/Perfa/src

# 加载环境变量
if [ -f "src/langchain_agent/.env" ]; then
    export $(cat src/langchain_agent/.env | grep -v '^#' | xargs)
fi

echo "=========================================="
echo "Perfa LangChain Agent 启动"
echo "=========================================="

# 创建日志目录
mkdir -p logs

# 1. 后台启动 Web 模式
echo "启动 Web API (端口 10000)..."
nohup python3 -m uvicorn src.langchain_agent.backend.main:app \
    --host 0.0.0.0 \
    --port 10000 \
    > /dev/null 2>&1 &

WEB_PID=$!
echo "Web API PID: $WEB_PID"

# 等待 Web 启动
sleep 3

# 检查 Web 是否启动成功
if curl -s http://localhost:10000/health > /dev/null 2>&1; then
    echo "✓ Web API 启动成功"
else
    echo "✗ Web API 启动失败，检查日志: logs/langchain_agent.log"
fi

echo ""
echo "=========================================="
echo "访问地址:"
echo "  - Web API: http://localhost:10000"
echo "  - API 文档: http://localhost:10000/docs"
echo "  - 日志文件: logs/langchain_agent.log"
echo "=========================================="
echo ""

# 2. 前台启动 CLI 模式
echo "启动 CLI 交互模式..."
echo ""
python3 -m src.langchain_agent.main -i

# CLI 退出后，停止 Web 服务
echo ""
echo "停止 Web API..."
kill $WEB_PID 2>/dev/null
echo "所有服务已停止"
