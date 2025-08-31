#!/bin/bash

# 30-phishing-ai-system 项目别名快速加载器
# 使用方法: source load_aliases.sh

echo "🎣 加载30项目Docker别名..."

# 加载通用Docker别名
if [ -f "../docker_aliases.sh" ]; then
    source ../docker_aliases.sh
else
    echo "⚠️  未找到通用别名文件，加载基础别名..."
    
    # 基础别名
    alias dcbuild='docker-compose build'
    alias dcup='docker-compose up'
    alias dcupd='docker-compose up -d'
    alias dcdown='docker-compose down'
    alias dclogs='docker-compose logs'
    alias dclogf='docker-compose logs -f'
    alias dockps='docker ps --format "table {{.ID}}\t{{.Names}}\t{{.Status}}\t{{.Ports}}"'
    alias docksh='function _docksh(){ docker exec -it "$1" /bin/bash; }; _docksh'
fi

# 30项目专用别名
alias start-30='function _start_30(){
    echo "🎣 启动30钓鱼攻击与AI防护系统..."
    ./start_phishing_ai.sh
}; _start_30'

alias stop-30='function _stop_30(){
    echo "🛑 停止30钓鱼系统..."
    ./stop_phishing_ai.sh
}; _stop_30'

alias status-30='function _status_30(){
    echo "📊 30-phishing-ai-system 状态"
    echo "==============================="
    echo ""
    echo "🌐 Web服务状态:"
    
    # 检查主要服务
    services=(
        "5000:Web管理界面"
        "3333:Gophish钓鱼平台"
        "3000:Grafana监控"
        "11434:Ollama AI"
        "8001:钓鱼检测API"
        "8002:图像分析API"
        "8003:行为分析API"
    )
    
    for service in "${services[@]}"; do
        port="${service%%:*}"
        name="${service##*:}"
        if nc -z localhost "$port" 2>/dev/null; then
            echo "  ✅ $name: http://localhost:$port"
        else
            echo "  ❌ $name: 未运行"
        fi
    done
    
    echo ""
    echo "🐳 容器状态:"
    if [ -d "output" ]; then
        cd output
        echo "网络基础设施:"
        dcps | head -5
        cd ..
    fi
    
    echo ""
    echo "AI服务:"
    dockps | grep -E "(ollama|phishing|ai)" || echo "❌ AI服务未运行"
    
    echo ""
    echo "🎯 攻击平台:"
    dockps | grep -E "(gophish|phishing)" || echo "❌ 攻击平台未运行"
}; _status_30'

alias ai-status='function _ai_status(){
    echo "🤖 AI服务详细状态"
    echo "=================="
    echo ""
    
    # 检查Ollama
    echo "🧠 Ollama LLM服务:"
    if curl -s http://localhost:11434/api/tags 2>/dev/null | jq . > /dev/null 2>&1; then
        echo "  ✅ Ollama运行正常"
        echo "  📋 已安装模型:"
        curl -s http://localhost:11434/api/tags 2>/dev/null | jq -r '.models[].name' | sed 's/^/    - /'
    else
        echo "  ❌ Ollama服务未响应"
    fi
    
    echo ""
    echo "🛡️ AI检测服务:"
    if curl -s http://localhost:8001/health 2>/dev/null > /dev/null; then
        echo "  ✅ 钓鱼检测服务: http://localhost:8001"
    else
        echo "  ❌ 钓鱼检测服务未运行"
    fi
    
    if curl -s http://localhost:8002/health 2>/dev/null > /dev/null; then
        echo "  ✅ 图像分析服务: http://localhost:8002"
    else
        echo "  ❌ 图像分析服务未运行"
    fi
    
    if curl -s http://localhost:8003/health 2>/dev/null > /dev/null; then
        echo "  ✅ 行为分析服务: http://localhost:8003"
    else
        echo "  ❌ 行为分析服务未运行"
    fi
}; _ai_status'

alias gophish-web='function _gophish_web(){
    echo "🎣 Gophish钓鱼平台访问"
    echo "======================="
    echo ""
    if nc -z localhost 3333 2>/dev/null; then
        echo "✅ Gophish平台正在运行"
        echo "🌐 管理界面: https://localhost:3333"
        echo "🔐 默认账户: admin / SeedEmail2024!"
        echo ""
        echo "💡 快速操作:"
        echo "  1. 创建用户组 (Users & Groups)"
        echo "  2. 设计邮件模板 (Email Templates)"
        echo "  3. 创建着陆页 (Landing Pages)"
        echo "  4. 配置发送配置文件 (Sending Profiles)"
        echo "  5. 启动钓鱼活动 (Campaigns)"
        
        # 尝试打开浏览器
        if command -v xdg-open > /dev/null; then
            read -p "是否要打开浏览器? [y/N]: " open_browser
            if [[ $open_browser =~ ^[Yy]$ ]]; then
                xdg-open https://localhost:3333
            fi
        fi
    else
        echo "❌ Gophish平台未运行"
        echo "💡 请先运行: start-30"
    fi
}; _gophish_web'

alias web-console='function _web_console(){
    echo "🌐 Web控制台访问"
    echo "================"
    echo ""
    if nc -z localhost 5000 2>/dev/null; then
        echo "✅ Web管理界面正在运行"
        echo "🌐 控制台: http://localhost:5000"
        echo ""
        echo "💡 功能模块:"
        echo "  📊 系统仪表板 - 实时监控"
        echo "  🎣 钓鱼生成器 - AI邮件生成"
        echo "  🛡️ 安全检测器 - AI检测"
        echo "  📈 行为分析 - 用户行为"
        echo "  🎭 攻击场景 - 预设场景"
        echo "  🤖 AI模型 - 服务管理"
        
        # 尝试打开浏览器
        if command -v xdg-open > /dev/null; then
            read -p "是否要打开浏览器? [y/N]: " open_browser
            if [[ $open_browser =~ ^[Yy]$ ]]; then
                xdg-open http://localhost:5000
            fi
        fi
    else
        echo "❌ Web管理界面未运行"
        echo "💡 请先运行: start-30"
    fi
}; _web_console'

alias phishing-demo='function _phishing_demo(){
    echo "🎭 钓鱼攻击演示"
    echo "================"
    echo ""
    echo "📋 可用攻击场景:"
    echo "  1. CEO诈骗攻击 (难度: ⭐⭐⭐⭐)"
    echo "  2. 供应链攻击 (难度: ⭐⭐⭐⭐⭐)"
    echo "  3. HR招聘诈骗 (难度: ⭐⭐⭐)"
    echo "  4. 技术支持诈骗 (难度: ⭐⭐)"
    echo "  5. 内部威胁模拟 (难度: ⭐⭐⭐⭐)"
    echo "  6. 金融钓鱼攻击 (难度: ⭐⭐⭐⭐)"
    echo ""
    echo "🚀 演示步骤:"
    echo "  1. 访问 Web控制台: web-console"
    echo "  2. 使用AI生成钓鱼邮件"
    echo "  3. 配置Gophish攻击活动: gophish-web"
    echo "  4. 监控攻击效果和防护检测"
    echo ""
    echo "⚠️  提醒: 仅用于授权的安全教育和研究!"
}; _phishing_demo'

alias ai-test='function _ai_test(){
    echo "🧪 AI功能测试"
    echo "============="
    echo ""
    
    echo "🧠 测试Ollama LLM:"
    if curl -s http://localhost:11434/api/generate -d '"'"'{"model":"qwen2:7b","prompt":"Hello","stream":false}'"'"' | jq . > /dev/null 2>&1; then
        echo "  ✅ LLM响应正常"
    else
        echo "  ❌ LLM服务异常"
    fi
    
    echo ""
    echo "🛡️ 测试钓鱼检测API:"
    test_email="Subject: Urgent: Your account will be suspended
    
Dear user, your account will be suspended in 24 hours. Click here to verify: http://fake-bank.com/verify"
    
    if curl -s -X POST http://localhost:8001/detect \
        -H "Content-Type: application/json" \
        -d "{\"content\":\"$test_email\"}" | jq . > /dev/null 2>&1; then
        echo "  ✅ 钓鱼检测API响应正常"
    else
        echo "  ❌ 钓鱼检测API异常"
    fi
    
    echo ""
    echo "💡 详细测试请访问: http://localhost:5000"
}; _ai_test'

alias logs-30='function _logs_30(){
    echo "📋 30项目日志查看"
    if [ -z "$1" ]; then
        echo "可用服务:"
        echo ""
        echo "🌐 网络基础设施:"
        if [ -d "output" ]; then
            cd output && dcps | head -5 && cd ..
        fi
        echo ""
        echo "🤖 AI和攻击服务:"
        dockps | grep -E "(ollama|gophish|phishing|ai|seed)" | head -5
        echo ""
        echo "使用: logs-30 <服务名> 查看特定服务日志"
        echo "例如: logs-30 seed_ollama_llm"
        return 0
    fi
    
    echo "📋 查看 $1 的日志:"
    docker logs -f --tail=100 "$1"
}; _logs_30'

# 显示可用命令
alias help-30='function _help_30(){
    echo "📚 30-phishing-ai-system 专用命令"
    echo "=================================="
    echo ""
    echo "🚀 项目管理:"
    echo "  start-30         - 启动30钓鱼AI系统"
    echo "  stop-30          - 停止30钓鱼系统"
    echo "  status-30        - 检查系统状态"
    echo ""
    echo "🌐 Web界面:"
    echo "  web-console      - 打开Web管理控制台"
    echo "  gophish-web      - 打开Gophish钓鱼平台"
    echo ""
    echo "🤖 AI服务:"
    echo "  ai-status        - AI服务详细状态"
    echo "  ai-test          - AI功能测试"
    echo ""
    echo "🎣 钓鱼实验:"
    echo "  phishing-demo    - 钓鱼攻击演示指南"
    echo ""
    echo "📋 日志管理:"
    echo "  logs-30 [服务]   - 查看日志"
    echo ""
    echo "🐳 Docker命令:"
    echo "  dcup/dcdown      - 启动/停止容器"
    echo "  dockps           - 查看容器状态"
    echo "  docksh <id>      - 进入容器"
    echo ""
    echo "💡 使用 seed-help 查看完整命令列表"
}; _help_30'

echo "✅ 30项目别名已加载!"
echo "💡 输入 'help-30' 查看项目专用命令"
echo "💡 输入 'seed-help' 查看所有命令"
