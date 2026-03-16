#!/bin/bash

# Docker 和 Docker Compose 快速安装脚本

set -e

echo "======================================"
echo "  Docker & Docker Compose 安装脚本"
echo "======================================"

# 检查是否为 root 用户
if [ "$EUID" -ne 0 ]; then
    echo "请使用 sudo 运行此脚本"
    exit 1
fi

# 检测系统类型
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
else
    echo "无法检测系统类型"
    exit 1
fi

echo "检测到系统: $OS"

# 检查 Docker 是否已安装
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version)
    echo "Docker 已安装: $DOCKER_VERSION"
else
    echo "开始安装 Docker..."
    
    case $OS in
        ubuntu|debian)
            # 更新包索引
            apt-get update
            
            # 安装依赖
            apt-get install -y \
                ca-certificates \
                curl \
                gnupg \
                lsb-release
            
            # 添加 Docker 官方 GPG 密钥
            mkdir -p /etc/apt/keyrings
            curl -fsSL https://download.docker.com/linux/$OS/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
            
            # 设置仓库
            echo \
                "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$OS \
                $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
            
            # 安装 Docker
            apt-get update
            apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
            ;;
            
        centos|rhel|rocky|almalinux)
            # 安装依赖
            yum install -y yum-utils
            
            # 添加 Docker 仓库
            yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
            
            # 安装 Docker
            yum install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
            
            # 启动 Docker
            systemctl start docker
            systemctl enable docker
            ;;
            
        *)
            echo "不支持的系统: $OS"
            echo "请参考官方文档手动安装: https://docs.docker.com/engine/install/"
            exit 1
            ;;
    esac
    
    echo "Docker 安装完成!"
fi

# 检查 Docker Compose 是否已安装
if docker compose version &> /dev/null; then
    COMPOSE_VERSION=$(docker compose version)
    echo "Docker Compose 已安装: $COMPOSE_VERSION"
else
    echo "Docker Compose 未找到，尝试安装..."
    
    # 获取最新版本号
    COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep 'tag_name' | cut -d\" -f4)
    
    if [ -z "$COMPOSE_VERSION" ]; then
        COMPOSE_VERSION="v2.24.0"
    fi
    
    echo "安装 Docker Compose $COMPOSE_VERSION ..."
    
    # 下载 Docker Compose
    curl -L "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" \
        -o /usr/local/bin/docker-compose
    
    # 添加执行权限
    chmod +x /usr/local/bin/docker-compose
    
    echo "Docker Compose 安装完成!"
fi

# 将当前用户添加到 docker 组（可选）
if [ -n "$SUDO_USER" ]; then
    echo "将用户 $SUDO_USER 添加到 docker 组..."
    usermod -aG docker $SUDO_USER
    echo "注意: 请重新登录以使 docker 组权限生效"
fi

# 显示版本信息
echo ""
echo "======================================"
echo "  安装完成!"
echo "======================================"
docker --version
docker compose version
echo ""
echo "使用以下命令验证安装:"
echo "  docker run hello-world"
