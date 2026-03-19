#!/bin/bash

echo "启动 Perfa LangChain 依赖服务..."

# 创建网络
docker network create perfa-network 2>/dev/null || true

# 启动 ChromaDB
docker-compose up -d

# 等待服务就绪
echo "等待 ChromaDB 启动..."
sleep 5

# 检查状态
if docker ps | grep -q perfa-chromadb; then
    echo "✓ ChromaDB 已启动，访问地址: http://localhost:8001"
    echo "✓ 数据持久化目录: ./chroma_data"
else
    echo "✗ ChromaDB 启动失败"
    exit 1
fi

echo "所有服务启动完成！"
