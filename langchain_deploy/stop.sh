#!/bin/bash

echo "停止 Perfa LangChain 依赖服务..."

# 停止容器
docker-compose down

echo "✓ 所有服务已停止"
