#!/bin/bash

echo "🧪====================================================================🧪"
echo "           SEED邮件系统 - 集成测试工具"
echo "           验证29/29-1/30项目功能完整性"
echo "🧪====================================================================🧪"
echo ""

# 测试项目选择
PROJECT=${1:-"29"}
TIMEOUT=${2:-30}

echo "🎯 测试项目: $PROJECT"
echo "⏱️  超时时间: ${TIMEOUT}秒"
echo ""

# 设置环境
cd /home/parallels/seed-email-system
source development.env 2>/dev/null || true
conda activate seed-emulator 2>/dev/null || true
cd examples/.not_ready_examples/

# 测试函数
test_port() {
    local port=$1
    local service=$2
    echo -n "🔌 测试端口 $port ($service)... "
    if curl -s --connect-timeout 5 http://localhost:$port > /dev/null 2>&1; then
        echo "✅ 正常"
        return 0
    else
        echo "❌ 失败"
        return 1
    fi
}

test_docker_containers() {
    echo "📦 测试Docker容器状态..."
    local containers=$(docker ps --format "{{.Names}}" | grep -E "(mail-|as.*h-|seedemu)" | wc -l)
    echo "   发现 $containers 个相关容器"
    
    if [ $containers -gt 0 ]; then
        echo "   ✅ 容器正在运行"
        return 0
    else
        echo "   ❌ 没有发现运行中的容器"
        return 1
    fi
}

test_email_servers() {
    echo "📧 测试邮件服务器..."
    local mail_containers=$(docker ps --format "{{.Names}}" | grep "mail-" | wc -l)
    echo "   发现 $mail_containers 个邮件服务器"
    
    if [ $mail_containers -ge 3 ]; then
        echo "   ✅ 邮件服务器正常运行"
        return 0
    else
        echo "   ❌ 邮件服务器数量不足"
        return 1
    fi
}

test_network_connectivity() {
    echo "🌐 测试网络连通性..."
    local mail_container=$(docker ps --format "{{.Names}}" | grep "mail-" | head -1)
    
    if [ -n "$mail_container" ]; then
        echo -n "   测试容器网络... "
        if docker exec "$mail_container" ping -c 1 8.8.8.8 > /dev/null 2>&1; then
            echo "✅ 网络正常"
            return 0
        else
            echo "❌ 网络连接失败"
            return 1
        fi
    else
        echo "   ⚠️  没有找到邮件容器"
        return 1
    fi
}

# 开始测试
echo "🚀 开始 ${PROJECT} 项目集成测试..."
echo ""

case $PROJECT in
    "29")
        echo "📧 测试 29-email-system (基础版)"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
        # 检查项目目录
        if [ ! -d "29-email-system" ]; then
            echo "❌ 29-email-system 目录不存在"
            exit 1
        fi
        
        cd 29-email-system
        
        # 检查配置文件
        if [ ! -f "output/docker-compose.yml" ]; then
            echo "⚠️  配置文件不存在，正在生成..."
            python3 email_simple.py arm
        fi
        
        # 测试容器
        test_docker_containers
        test_email_servers
        
        # 测试端口
        test_port 8080 "Internet Map"
        test_port 5000 "Web管理界面"
        test_port 2525 "seedemail.net SMTP"
        test_port 2526 "corporate.local SMTP"
        test_port 2527 "smallbiz.org SMTP"
        
        # 测试网络
        test_network_connectivity
        
        cd ..
        ;;
        
    "29-1")
        echo "🌐 测试 29-1-email-system (真实版)"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
        if [ ! -d "29-1-email-system" ]; then
            echo "❌ 29-1-email-system 目录不存在"
            exit 1
        fi
        
        cd 29-1-email-system
        
        if [ ! -f "output/docker-compose.yml" ]; then
            echo "⚠️  配置文件不存在，正在生成..."
            python3 email_realistic.py arm
        fi
        
        test_docker_containers
        test_email_servers
        test_port 8080 "Internet Map"
        
        # 测试真实邮件服务商端口
        test_port 2200 "QQ邮箱"
        test_port 2201 "163邮箱"
        test_port 2202 "Gmail"
        test_port 2203 "Outlook"
        test_port 2204 "企业邮箱"
        test_port 2205 "自建邮箱"
        
        test_network_connectivity
        
        cd ..
        ;;
        
    "30")
        echo "🤖 测试 30-phishing-ai-system (AI钓鱼版)"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
        if [ ! -d "30-phishing-ai-system" ]; then
            echo "❌ 30-phishing-ai-system 目录不存在"
            exit 1
        fi
        
        cd 30-phishing-ai-system
        
        test_docker_containers
        test_port 5000 "AI控制台"
        test_port 3333 "Gophish"
        test_port 11434 "Ollama AI"
        test_port 8001 "钓鱼检测"
        test_port 8002 "图像分析"
        test_port 8003 "行为分析"
        
        cd ..
        ;;
        
    *)
        echo "❌ 未知项目: $PROJECT"
        echo "   支持的项目: 29, 29-1, 30"
        exit 1
        ;;
esac

echo ""
echo "📊 测试结果总结"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 统计运行中的容器
running_containers=$(docker ps --format "{{.Names}}" | grep -E "(mail-|as.*h-|seedemu)" | wc -l)
total_processes=$(ps aux | grep -E "(webmail_server|gophish|ollama)" | grep -v grep | wc -l)

echo "🐳 Docker容器: $running_containers 个正在运行"
echo "⚙️  相关进程: $total_processes 个正在运行"

# 端口状态
echo ""
echo "🔌 端口状态检查:"
critical_ports=(5000 8080 2525 2526 2527 11434 3333)
for port in "${critical_ports[@]}"; do
    if lsof -ti :$port >/dev/null 2>&1; then
        echo "   ✅ $port 端口正在使用"
    else
        echo "   ⚪ $port 端口空闲"
    fi
done

echo ""
echo "🎯 访问地址:"
if lsof -ti :5000 >/dev/null 2>&1; then
    echo "   🌐 Web界面: http://localhost:5000"
fi
if lsof -ti :8080 >/dev/null 2>&1; then
    echo "   🗺️  网络图: http://localhost:8080/map.html"
fi
if lsof -ti :3333 >/dev/null 2>&1; then
    echo "   🎣 Gophish: https://localhost:3333"
fi

echo ""
echo "🧪====================================================================🧪"
echo "                    集成测试完成"
echo "🧪====================================================================🧪"
