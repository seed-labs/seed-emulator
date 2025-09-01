#!/bin/bash

echo "🎣====================================================================🎣"
echo "          SEED 钓鱼攻击与AI防护系统启动脚本"
echo "                 30-phishing-ai-system"
echo "🎣====================================================================🎣"
echo ""

# 检查Docker环境
echo "🔍 检查Docker环境..."
if ! docker --version &> /dev/null; then
    echo "❌ Docker未安装或未启动"
    exit 1
fi

if ! docker-compose --version &> /dev/null; then
    echo "❌ Docker Compose未安装"
    exit 1
fi

echo "✅ Docker环境检查完成"
echo ""

# 生成系统配置
echo "🏗️ 生成系统配置..."
if [ ! -f "output/docker-compose.yml" ]; then
    echo "📦 生成网络基础设施..."
    python3 phishing_ai_system.py arm
    
    if [ $? -ne 0 ]; then
        echo "❌ 网络配置生成失败"
        exit 1
    fi
fi

echo "✅ 系统配置生成完成"
echo ""

# 启动网络基础设施
echo "🌐 启动网络基础设施..."
cd output
docker-compose up -d

if [ $? -ne 0 ]; then
    echo "❌ 网络启动失败"
    exit 1
fi

echo "✅ 网络基础设施启动完成"
echo ""

# 启动AI和攻击服务
echo "🤖 启动AI和攻击服务..."
if [ -f "docker-compose-services.yml" ]; then
    docker-compose -f docker-compose-services.yml up -d
    
    if [ $? -ne 0 ]; then
        echo "⚠️  部分AI服务启动可能失败，请检查日志"
    else
        echo "✅ AI和攻击服务启动完成"
    fi
else
    echo "⚠️  AI服务配置文件未找到，将跳过AI服务启动"
fi

cd ..
echo ""

# 等待服务启动
echo "⏳ 等待服务完全启动..."
sleep 30

# 检查服务状态
echo "📊 检查服务状态..."

check_service() {
    local service_name=$1
    local port=$2
    local protocol=${3:-http}
    
    if curl -s --connect-timeout 5 "$protocol://localhost:$port" > /dev/null 2>&1; then
        echo "✅ $service_name ($protocol://localhost:$port)"
        return 0
    else
        echo "❌ $service_name ($protocol://localhost:$port)"
        return 1
    fi
}

echo ""
echo "🔍 服务状态检查:"

# 检查核心服务
working_services=0
total_services=0

# Web管理界面
if check_service "Web管理界面" "5000"; then
    ((working_services++))
fi
((total_services++))

# Gophish
if check_service "Gophish钓鱼平台" "3333" "https"; then
    ((working_services++))
fi
((total_services++))

# Grafana监控
if check_service "Grafana监控" "3000"; then
    ((working_services++))
fi
((total_services++))

# Ollama AI
if check_service "Ollama AI服务" "11434"; then
    ((working_services++))
fi
((total_services++))

echo ""
echo "📈 服务状态: $working_services/$total_services 服务正常运行"

# 显示访问信息
echo ""
echo "🎯====================================================================🎯"
echo "                          系统访问信息"
echo "🎯====================================================================🎯"
echo ""
echo "🌐 Web服务:"
echo "   📊 主控制台:        http://localhost:5000"
echo "   🎣 Gophish平台:     https://localhost:3333"
echo "   📈 监控面板:        http://localhost:3000"
echo "   🧠 AI API文档:      http://localhost:8001/docs"
echo ""
echo "📧 邮件服务:"
echo "   🏢 企业邮件:        localhost:2500 (SMTP)"
echo "   📬 IMAP访问:        localhost:1430"
echo ""
echo "🤖 AI服务:"
echo "   🧠 Ollama LLM:      http://localhost:11434"
echo "   🛡️ 钓鱼检测器:       http://localhost:8001"
echo "   🖼️ 图像分析器:       http://localhost:8002"
echo "   📊 行为分析器:       http://localhost:8003"
echo ""
echo "🔐 默认凭据:"
echo "   Gophish:           admin / SeedEmail2024!"
echo "   Grafana:           admin / SeedEmail2024!"
echo "   数据库:            seeduser / SeedEmail2024!"
echo ""

# 显示快速操作指南
echo "🚀 快速操作指南:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. 📊 访问主控制台:"
echo "   在浏览器中打开: http://localhost:5000"
echo ""
echo "2. 🎣 开始钓鱼实验:"
echo "   a) 访问 Gophish: https://localhost:3333"
echo "   b) 使用默认账户登录"
echo "   c) 创建钓鱼活动和模板"
echo ""
echo "3. 🧠 使用AI生成钓鱼邮件:"
echo "   a) 在主控制台选择 '钓鱼生成器'"
echo "   b) 输入目标信息和攻击场景"
echo "   c) 点击 'AI生成' 按钮"
echo ""
echo "4. 🛡️ 测试AI防护:"
echo "   a) 在主控制台选择 '安全检测器'"
echo "   b) 粘贴邮件内容"
echo "   c) 点击 '检测钓鱼风险'"
echo ""
echo "5. 📈 查看监控数据:"
echo "   访问 Grafana: http://localhost:3000"
echo ""

# 显示安全提醒
echo "⚠️  安全提醒:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔒 所有攻击活动仅限于仿真环境内"
echo "📋 仅用于授权的安全教育和研究目的"
echo "🛡️ 严格遵守网络安全伦理准则"
echo "📝 系统将记录所有操作的审计日志"
echo ""

# 显示故障排除信息
if [ $working_services -lt $total_services ]; then
    echo "🔧 故障排除:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "如果某些服务未正常启动:"
    echo "1. 检查Docker日志: docker-compose logs [service_name]"
    echo "2. 重启服务: docker-compose restart [service_name]"
    echo "3. 检查端口占用: netstat -tlnp | grep [port]"
    echo "4. 重新启动整个系统: ./stop_phishing_ai.sh && ./start_phishing_ai.sh"
    echo ""
fi

echo "🎉 SEED 钓鱼攻击与AI防护系统启动完成！"
echo "🎯 开始您的网络安全实验之旅吧！"
echo ""
echo "🎣====================================================================🎣"
