#!/bin/bash

# 57号实验启动脚本 - ARM64兼容版本
# 综合安全评估仿真实验

echo "🛡️ 启动 57 号综合安全评估实验 (ARM64)"
echo "======================================"

# 检查29号邮件基础设施是否启动
echo "📧 检查邮件基础设施状态..."
if ! docker ps | grep -q "mailserver-150"; then
    echo "❌ 29号邮件系统未启动，请先启动29号实验"
    echo "   cd ../29-email-system && python3 email_system.py arm && cd output && docker-compose up -d"
    exit 1
fi

# 检查seed_emulator网络
echo "🌐 检查 seed_emulator 网络..."
if ! docker network ls | grep -q "seed_emulator"; then
    echo "🔧 创建 seed_emulator 网络..."
    docker network create seed_emulator
fi

# 启动模拟的攻防工具 (ARM64兼容)
echo "🟥 启动模拟红队工具..."

# 启动Gophish替代品 (使用nginx模拟)
if ! docker ps | grep -q "gophish"; then
    echo "  📡 启动 Gophish 模拟器..."
    docker run -d --name gophish \
        --network seed_emulator \
        -p 3333:80 \
        -p 8081:8080 \
        nginx:latest
fi

# 启动PentestAgent替代品 (使用alpine模拟)
if ! docker ps | grep -q "pentest-agent"; then
    echo "  🔍 启动 PentestAgent 模拟器..."
    docker run -d --name pentest-agent \
        --network seed_emulator \
        -p 5080:80 \
        alpine:latest sleep 3600
fi

# 启动OpenBAS替代品 (使用httpd模拟)
if ! docker ps | grep -q "openbas"; then
    echo "  🎯 启动 OpenBAS 模拟器..."
    docker run -d --name openbas \
        --network seed_emulator \
        -p 8443:80 \
        httpd:latest
fi

echo ""
echo "✅ 57号实验环境启动完成！"
echo ""
echo "🎛️ 访问地址："
echo "  📧 邮件系统地图: http://localhost:8080/map.html"
echo "  🔴 Gophish模拟器: http://localhost:3333"
echo "  🔍 PentestAgent模拟器: http://localhost:5080"
echo "  🎯 OpenBAS模拟器: http://localhost:8443"
echo "  📊 邮件服务器端口: 2525-2527 (SMTP), 1430-1432 (IMAP)"
echo ""
echo "🧠 这是一个ARM64兼容的模拟版本，用于演示实验架构"
echo "   真实的Gophish/PentestAgent/OpenBAS需要x86_64环境"
echo ""