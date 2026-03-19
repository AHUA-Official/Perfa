#!/bin/bash

# 启动 Perfa Agent 后端 API

echo "启动 Perfa Agent 后端..."

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装"
    exit 1
fi

# 检查依赖
python3 -c "import fastapi" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "安装依赖..."
    pip3 install fastapi uvicorn sse-starlette
fi

# 加载 .env 文件
if [ -f "$SCRIPT_DIR/.env" ]; then
    echo "加载环境变量: $SCRIPT_DIR/.env"
    export $(cat "$SCRIPT_DIR/.env" | grep -v '^#' | xargs)
fi

# 端口配置（可通过环境变量覆盖）
PORT=${LANGCHAIN_API_PORT:-10000}

# 启动服务
echo ""
echo "启动 FastAPI 服务（端口 $PORT）..."
echo "访问地址："
echo "  - API: http://localhost:$PORT"
echo "  - Docs: http://localhost:$PORT/docs"
echo "  - OpenAI Compatible: http://localhost:$PORT/v1/chat/completions"
echo ""

# 设置 PYTHONPATH
export PYTHONPATH=/home/ubuntu/Perfa/src:$PYTHONPATH

# 切换到项目根目录
cd "$PROJECT_ROOT"

# 使用 uvicorn 启动
python3 -m uvicorn src.langchain_agent.backend.main:app --host 0.0.0.0 --port $PORT --reload
