#!/bin/bash

echo "🛑 停止SEED钓鱼攻击与AI防护系统..."
echo "======================================================"

# 停止AI和攻击服务
if [ -f "output/docker-compose-services.yml" ]; then
    echo "🤖 停止AI和攻击服务..."
    cd output
    docker-compose -f docker-compose-services.yml down --remove-orphans
    cd ..
fi

# 停止网络基础设施
if [ -f "output/docker-compose.yml" ]; then
    echo "🌐 停止网络基础设施..."
    cd output
    docker-compose down --remove-orphans
    cd ..
fi

# 清理网络
echo "🧹 清理Docker网络..."
docker network prune -f

echo "✅ 系统已完全停止"
echo "💡 如需重新启动，请运行: ./start_phishing_ai.sh"
