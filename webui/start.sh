#!/bin/bash

# 启动 ChatGPT-Next-Web 前端

echo "启动 Perfa Web UI..."

cd "$(dirname "$0")"

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安装，请先安装 Docker"
    exit 1
fi

# 检查 compose 可用性
if command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
elif docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
else
    echo "❌ docker-compose / docker compose 未安装，请先安装 Docker Compose"
    exit 1
fi

# 启动服务
if [ "$COMPOSE_CMD" = "docker compose" ]; then
    docker compose up -d
else
    docker-compose up -d
fi

# 检查状态
if [ $? -eq 0 ]; then
    echo "✅ Web UI 启动成功！"
    echo ""
    echo "访问地址："
    echo "  http://localhost:3001"
    echo ""
    echo "配置说明："
    echo "  - API 地址：http://host.docker.internal:10000/v1"
    echo "  - 确保后端已启动在 10000 端口"
    echo ""
    echo "停止服务："
    echo "  ${COMPOSE_CMD} down"
else
    echo "❌ 启动失败"
    exit 1
fi
