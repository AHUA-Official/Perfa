#!/bin/bash

# 启动 ChatGPT-Next-Web 前端

echo "启动 Perfa Web UI..."

cd "$(dirname "$0")"

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安装，请先安装 Docker"
    exit 1
fi

# 检查 docker-compose 是否安装
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose 未安装，请先安装 docker-compose"
    exit 1
fi

# 启动服务
docker-compose up -d

# 检查状态
if [ $? -eq 0 ]; then
    echo "✅ Web UI 启动成功！"
    echo ""
    echo "访问地址："
    echo "  http://localhost:3001"
    echo ""
    echo "配置说明："
    echo "  - API 地址：http://host.docker.internal:10000/v1"
    echo "  - 确保后端已启动在 8080 端口"
    echo ""
    echo "停止服务："
    echo "  docker-compose down"
else
    echo "❌ 启动失败"
    exit 1
fi
