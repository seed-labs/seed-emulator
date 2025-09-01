#!/bin/bash

echo "🌐 启动 SEED 邮件系统 Web 管理界面"
echo "========================================"
echo ""

# 检查Docker环境
if ! docker ps &> /dev/null; then
    echo "❌ 无法连接到Docker，请确保Docker服务已启动"
    exit 1
fi

# 检查邮件系统是否运行
cd output
if ! docker-compose ps | grep -q "Up"; then
    echo "⚠️  邮件系统似乎没有运行，是否需要先启动？"
    echo "   运行: cd output && docker-compose up -d"
    echo ""
fi
cd ..

# 启动Web服务器
echo "🚀 启动Web管理界面..."
echo "   访问地址: http://localhost:5000"
echo ""
echo "✨ 功能特色:"
echo "   📧 邮件服务器状态监控"
echo "   👤 邮件账户管理"
echo "   📬 测试邮件发送"
echo "   🔍 网络连通性测试"
echo ""
echo "按 Ctrl+C 停止服务"
echo "========================================"

python3 webmail_server.py
