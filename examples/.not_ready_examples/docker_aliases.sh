#!/bin/bash

# =============================================================================
# SEED邮件系统 Docker 命令别名配置
# =============================================================================
# 使用方法:
#   source docker_aliases.sh
# 或添加到 ~/.bashrc:
#   echo "source $(pwd)/docker_aliases.sh" >> ~/.bashrc
# =============================================================================

echo "🐳 加载SEED邮件系统Docker别名..."

# Docker Compose 命令别名
alias dcbuild='docker-compose build'
alias dcup='docker-compose up'
alias dcdown='docker-compose down'
alias dcrestart='docker-compose restart'
alias dcstop='docker-compose stop'
alias dcstart='docker-compose start'
alias dclogs='docker-compose logs'
alias dcps='docker-compose ps'

# Docker Compose 扩展命令
alias dcupd='docker-compose up -d'                    # 后台启动
alias dcdown-clean='docker-compose down --remove-orphans -v'  # 完全清理
alias dcbuild-clean='docker-compose build --no-cache'  # 无缓存构建
alias dclogf='docker-compose logs -f'                 # 跟踪日志

# Docker 容器管理别名
alias dockps='docker ps --format "table {{.ID}}\t{{.Names}}\t{{.Status}}\t{{.Ports}}"'
alias dockpsa='docker ps -a --format "table {{.ID}}\t{{.Names}}\t{{.Status}}\t{{.CreatedAt}}"'
alias docksh='function _docksh(){ docker exec -it "$1" /bin/bash; }; _docksh'
alias docksh-sh='function _docksh_sh(){ docker exec -it "$1" /bin/sh; }; _docksh_sh'

# Docker 系统管理别名
alias docker-clean='docker system prune -f'
alias docker-clean-all='docker system prune -af'
alias docker-clean-volumes='docker volume prune -f'
alias docker-clean-networks='docker network prune -f'

# SEED项目特定别名
alias seed-status='function _seed_status(){ 
    echo "📊 SEED邮件系统状态检查"
    echo "=================================="
    echo ""
    echo "🐳 Docker容器状态:"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(seed|mail|gophish|ollama)"
    echo ""
    echo "🌐 网络状态:"
    docker network ls | grep -E "(seed|mail|net_)"
    echo ""
    echo "📦 镜像状态:"
    docker images | grep -E "(seed|mail|gophish|ollama)" | head -10
}; _seed_status'

alias seed-logs='function _seed_logs(){
    if [ -z "$1" ]; then
        echo "使用方法: seed-logs <容器名称>"
        echo "可用容器:"
        docker ps --format "{{.Names}}" | grep -E "(seed|mail|gophish|ollama)"
        return 1
    fi
    docker logs -f --tail=100 "$1"
}; _seed_logs'

alias seed-shell='function _seed_shell(){
    if [ -z "$1" ]; then
        echo "使用方法: seed-shell <容器名称>"
        echo "可用容器:"
        docker ps --format "{{.Names}}" | grep -E "(seed|mail|gophish|ollama)"
        return 1
    fi
    echo "🚀 连接到容器: $1"
    if docker exec -it "$1" /bin/bash 2>/dev/null; then
        echo "✅ 会话结束"
    elif docker exec -it "$1" /bin/sh 2>/dev/null; then
        echo "✅ 会话结束"
    else
        echo "❌ 无法连接到容器 $1"
    fi
}; _seed_shell'

# 快速启动项目的别名
alias seed-29='function _seed_29(){
    echo "🚀 启动 29-email-system..."
    cd 29-email-system
    
    # 确保必要的环境变量和虚拟环境
    if [ -z "$PYTHONPATH" ]; then
        echo "📦 设置环境变量..."
        cd /home/parallels/seed-email-system
        source development.env
        conda activate seed-emulator 2>/dev/null || true
        cd - > /dev/null
    fi
    
    if [ ! -f "output/docker-compose.yml" ]; then
        echo "📦 首次运行，生成配置..."
        python3 email_simple.py arm
    fi
    
    echo "🛠️ 构建Docker镜像..."
    cd output && dcbuild
    echo "🐳 启动Docker容器..."
    dcupd
    
    echo "🌐 启动Web管理界面..."
    cd .. && nohup python3 webmail_server.py > webmail.log 2>&1 &
    sleep 3
    
    echo "✅ 29项目启动完成！"
    echo "🌐 Web界面: http://localhost:5000"
    echo "🗺️ 网络图: http://localhost:8080/map.html"
    echo "📧 邮件服务: localhost:2525 (seedemail.net)"
    echo "             localhost:2526 (corporate.local)"
    echo "             localhost:2527 (smallbiz.org)"
}; _seed_29'

alias seed-29-1='function _seed_29_1(){
    echo "🚀 启动 29-1-email-system..."
    cd 29-1-email-system
    
    # 确保必要的环境变量和虚拟环境
    if [ -z "$PYTHONPATH" ]; then
        echo "📦 设置环境变量..."
        cd /home/parallels/seed-email-system
        source development.env
        conda activate seed-emulator 2>/dev/null || true
        cd - > /dev/null
    fi
    
    if [ ! -f "output/docker-compose.yml" ]; then
        echo "📦 首次运行，生成配置..."
        python3 email_realistic.py arm
    fi
    
    echo "🛠️ 构建Docker镜像..."
    cd output && dcbuild
    echo "🐳 启动Docker容器..."
    dcupd
    
    echo "🌐 启动Web管理界面..."
    cd .. && nohup python3 webmail_server.py > webmail.log 2>&1 &
    sleep 3
    
    echo "✅ 29-1项目启动完成！"
    echo "🌐 Web界面: http://localhost:5001"
    echo "🗺️ 网络图: http://localhost:8080/map.html"
    echo "📖 项目概述: http://localhost:5001/project_overview"
    echo ""
    echo "🌍 真实邮件服务商:"
    echo "  📧 QQ邮箱: localhost:2520 (qq.com)"
    echo "  📧 163邮箱: localhost:2521 (163.com)"
    echo "  📧 Gmail: localhost:2522 (gmail.com)"
    echo "  📧 Outlook: localhost:2523 (outlook.com)"
    echo "  📧 Yahoo: localhost:2524 (yahoo.com)"
    echo "  📧 企业邮箱: localhost:2525 (enterprise.cn)"
    echo ""
    echo "🌐 Internet Exchange Points:"
    echo "  • Beijing-IX (100) - 北京互联网交换中心"
    echo "  • Shanghai-IX (101) - 上海互联网交换中心"
    echo "  • Guangzhou-IX (102) - 广州互联网交换中心"
    echo "  • Global-IX (103) - 国际互联网交换中心"
    echo ""
    echo "🏢 ISP运营商:"
    echo "  • AS-2: 中国电信 (全网覆盖)"
    echo "  • AS-3: 中国联通 (北方主导)"
    echo "  • AS-4: 中国移动 (移动网络)"
}; _seed_29_1'

alias seed-30='function _seed_30(){
    echo "🚀 启动 30-phishing-ai-system..."
    cd 30-phishing-ai-system
    
    # 确保必要的环境变量和虚拟环境
    if [ -z "$PYTHONPATH" ]; then
        echo "📦 设置环境变量..."
        cd /home/parallels/seed-email-system
        source development.env
        conda activate seed-emulator 2>/dev/null || true
        cd - > /dev/null
    fi
    
    # 启动AI钓鱼系统
    ./start_phishing_ai.sh
    
    echo "✅ 30项目启动完成！"
    echo "🌐 Web控制台: http://localhost:5002"
    echo "🎣 Gophish管理: http://localhost:3333"
    echo "🤖 AI服务: http://localhost:11434"
    echo "🗺️ 网络图: $MAP_URL"
    echo "📖 项目概述: http://localhost:5002/project_overview"
    echo ""
    echo "🎯 主要功能:"
    echo "  • AI驱动的钓鱼邮件生成"
    echo "  • 多模态威胁检测系统"
    echo "  • 实时行为分析和监控"
    echo "  • 智能攻防对抗演示"
    echo ""
    echo "⚠️  请遵守安全研究伦理，仅在授权环境中使用"
}; _seed_30'

alias seed-31='function _seed_31(){
    echo "🎣 启动 31-advanced-phishing-system..."
    cd 31-advanced-phishing-system
    
    # 确保必要的环境变量和虚拟环境
    if [ -z "$PYTHONPATH" ]; then
        echo "📦 设置环境变量..."
        cd /home/parallels/seed-email-system
        source development.env
        conda activate seed-emulator 2>/dev/null || true
        cd - > /dev/null
    fi
    
    # 启动高级钓鱼系统
    ./start_advanced_phishing.sh
    
    echo "✅ 31高级系统启动完成！"
    echo "🌐 高级控制台: http://localhost:5003"
    echo "🔗 API接口: http://localhost:8003"
    echo "⚡ WebSocket: ws://localhost:9003"
    echo "🗺️ 网络图: $MAP_URL"
    echo "📖 项目概述: http://localhost:5003/project_overview"
    echo ""
    echo "🎯 高级功能:"
    echo "  • AI驱动的APT攻击模拟"
    echo "  • 多阶段复杂攻击链设计"
    echo "  • 高级规避和对抗技术"
    echo "  • 深度社会工程学实验"
    echo "  • 威胁情报AI分析"
    echo "  • 实时攻防对抗演示"
    echo ""
    echo "⚠️  极度危险！仅限高级安全研究使用！"
    echo "🔐 请确保已获得明确授权！"
}; _seed_31'

alias seed-stop='function _seed_stop(){
    echo "🛑 停止所有SEED项目..."
    
    # 使用强力清理脚本
    if [ -f "force_cleanup.sh" ]; then
        echo "🧹 使用强力清理工具..."
        ./force_cleanup.sh
    else
        echo "⚠️  未找到强力清理工具，使用标准方式..."
        
        # 停止30项目
        if [ -d "30-phishing-ai-system" ]; then
            cd 30-phishing-ai-system
            if [ -f "stop_phishing_ai.sh" ]; then
                ./stop_phishing_ai.sh
            fi
            cd ..
        fi
        
        # 停止29-1项目
        if [ -d "29-1-email-system/output" ]; then
            cd 29-1-email-system/output
            dcdown --remove-orphans
            cd ../..
        fi
        
        # 停止29项目
        if [ -d "29-email-system/output" ]; then
            cd 29-email-system/output
            dcdown --remove-orphans
            cd ../..
        fi
        
        # 清理所有SEED相关容器
        echo "🧹 清理残留容器..."
        docker ps -a --filter "name=mail-" --filter "name=seed" --filter "name=as" --format "{{.Names}}" | xargs docker rm -f 2>/dev/null || true
        
        # 清理网络
        echo "🌐 清理网络..."
        docker network prune -f
        
        echo "✅ 标准清理完成"
    fi
}; _seed_stop'

# 邮件测试别名
alias seed-mail-test='function _seed_mail_test(){
    echo "📧 SEED邮件系统测试工具"
    echo "==============================="
    echo ""
    echo "可用的邮件服务器:"
    docker ps --format "{{.Names}}" | grep mail
    echo ""
    echo "使用方法:"
    echo "  seed-mail-send <发件人> <收件人> <主题> <内容>"
    echo "  seed-mail-check <邮件服务器容器名>"
}; _seed_mail_test'

alias seed-mail-send='function _seed_mail_send(){
    if [ $# -lt 4 ]; then
        echo "使用方法: seed-mail-send <发件人> <收件人> <主题> <内容>"
        echo "例如: seed-mail-send admin@seedemail.net user@corporate.local \"测试邮件\" \"这是一条测试邮件\""
        return 1
    fi
    
    local from="$1"
    local to="$2" 
    local subject="$3"
    local body="$4"
    
    # 查找运行中的邮件服务器
    local mailserver=$(docker ps --format "{{.Names}}" | grep mail | head -1)
    
    if [ -z "$mailserver" ]; then
        echo "❌ 未找到运行中的邮件服务器"
        return 1
    fi
    
    echo "📧 发送邮件通过: $mailserver"
    echo "发件人: $from"
    echo "收件人: $to"
    echo "主题: $subject"
    
    # 使用swaks发送测试邮件
    docker exec -it "$mailserver" swaks \
        --to "$to" \
        --from "$from" \
        --server localhost \
        --port 25 \
        --header "Subject: $subject" \
        --body "$body"
}; _seed_mail_send'

# 网络调试别名
alias seed-ping='function _seed_ping(){
    if [ $# -lt 2 ]; then
        echo "使用方法: seed-ping <源容器> <目标IP>"
        echo "例如: seed-ping as150h-host_0-10.150.0.71 10.200.0.71"
        return 1
    fi
    
    local container="$1"
    local target="$2"
    
    echo "🌐 网络连通性测试: $container → $target"
    docker exec -it "$container" ping -c 4 "$target"
}; _seed_ping'

alias seed-traceroute='function _seed_traceroute(){
    if [ $# -lt 2 ]; then
        echo "使用方法: seed-traceroute <源容器> <目标IP>"
        return 1
    fi
    
    local container="$1"
    local target="$2"
    
    echo "🛣️ 路由跟踪: $container → $target"
    docker exec -it "$container" traceroute "$target"
}; _seed_traceroute'

# AI服务管理别名
alias seed-ai-status='function _seed_ai_status(){
    echo "🤖 SEED AI服务状态"
    echo "=================="
    echo ""
    echo "Ollama LLM:"
    curl -s http://localhost:11434/api/tags 2>/dev/null | jq . || echo "❌ Ollama服务未响应"
    echo ""
    echo "AI检测服务:"
    curl -s http://localhost:8001/health 2>/dev/null || echo "❌ 钓鱼检测服务未响应"
    curl -s http://localhost:8002/health 2>/dev/null || echo "❌ 图像分析服务未响应"  
    curl -s http://localhost:8003/health 2>/dev/null || echo "❌ 行为分析服务未响应"
}; _seed_ai_status'

# 帮助信息
alias seed-help='function _seed_help(){
    echo "🎓 SEED邮件系统命令帮助"
    echo "========================="
    echo ""
    echo "📦 Docker Compose 命令:"
    echo "  dcbuild          - 构建容器镜像"
    echo "  dcup             - 启动容器"
    echo "  dcupd            - 后台启动容器"
    echo "  dcdown           - 停止容器"
    echo "  dcrestart        - 重启容器"
    echo "  dclogs           - 查看日志"
    echo "  dclogf           - 跟踪日志"
    echo ""
    echo "🐳 Docker 容器命令:"
    echo "  dockps           - 列出运行中的容器"
    echo "  dockpsa          - 列出所有容器"
    echo "  docksh <id>      - 进入容器Shell"
    echo ""
    echo "🎯 SEED 项目命令:"
    echo "  seed-29          - 启动29基础版"
    echo "  seed-29-1        - 启动29-1真实版"
    echo "  seed-30          - 启动30 AI版"
    echo "  seed-31          - 启动31高级钓鱼版"
    echo "  seed-stop        - 停止所有项目"
    echo "  seed-status      - 检查系统状态"
    echo "  seed-shell <容器> - 进入SEED容器"
    echo ""
    echo "📧 邮件测试命令:"
    echo "  seed-mail-send   - 发送测试邮件"
    echo "  seed-mail-test   - 邮件测试帮助"
    echo ""
    echo "🌐 网络调试命令:"
    echo "  seed-ping        - 网络连通性测试"
    echo "  seed-traceroute  - 路由跟踪"
    echo ""
    echo "🤖 AI服务命令:"
    echo "  seed-ai-status   - AI服务状态检查"
    echo ""
    echo "🧹 清理命令:"
    echo "  docker-clean         - 清理Docker系统"
    echo "  docker-clean-all     - 完全清理Docker"
    echo "  seed-force-cleanup   - SEED强力清理"
    echo "  seed-check-ports     - 检查端口占用"
    echo "  seed-emergency-stop  - 紧急停止程序"
    echo ""
    echo "🌟 系统总览:"
    echo "  seed-overview     - 启动系统总览网页 (端口4257)"
    echo ""
    echo "💡 使用提示:"
    echo "  • 使用 seed-overview 启动综合管理界面"
    echo "  • 访问 http://localhost:4257 查看所有项目信息"
    echo "  • 可以同时运行多个项目进行对比测试"
}; _seed_help'

# SEED强力清理命令
alias seed-force-cleanup='function _seed_force_cleanup(){
    if [ -f "force_cleanup.sh" ]; then
        echo "🧹 启动SEED强力清理..."
        ./force_cleanup.sh force
    else
        echo "❌ 未找到force_cleanup.sh脚本"
        echo "请确保在SEED项目根目录运行"
    fi
}; _seed_force_cleanup'

alias seed-check-ports='function _seed_check_ports(){
    echo "🔌 SEED端口占用检查"
    echo "==================="
    echo ""
    
    # SEED关键端口
    local ports=(2525 2526 2527 5870 5871 5872 1430 1431 1432 9930 9931 9932 5000 3333 8080 11434 8001 8002 8003 3000 9090)
    local occupied=0
    
    for port in "${ports[@]}"; do
        if lsof -ti :$port >/dev/null 2>&1; then
            echo "❌ 端口 $port 被占用 (PID: $(lsof -ti :$port))"
            ((occupied++))
        else
            echo "✅ 端口 $port 空闲"
        fi
    done
    
    echo ""
    if [ $occupied -eq 0 ]; then
        echo "🎉 所有关键端口都空闲！"
    else
        echo "⚠️  有 $occupied 个端口被占用"
        echo "💡 运行 seed-force-cleanup 释放端口"
    fi
}; _seed_check_ports'

alias seed-emergency-stop='function _seed_emergency_stop(){
    echo "🚨 SEED紧急停止程序"
    echo "=================="
    echo "⚠️  这将强制停止所有SEED相关进程！"
    echo ""
    
    read -p "确认执行紧急停止? [y/N]: " confirm
    if [[ ! $confirm =~ ^[Yy]$ ]]; then
        echo "❌ 操作已取消"
        return 0
    fi
    
    echo "🛑 停止所有Docker容器..."
    docker stop $(docker ps -q) 2>/dev/null || true
    
    echo "🗑️  删除所有SEED容器..."
    docker ps -a --filter "name=mail-" --filter "name=seed" --filter "name=as" --format "{{.Names}}" | xargs docker rm -f 2>/dev/null || true
    
    echo "🔫 强制释放SEED端口..."
    local ports=(2525 2526 2527 5870 5871 5872 1430 1431 1432 9930 9931 9932 5000 3333 8080 11434 8001 8002 8003 3000 9090)
    for port in "${ports[@]}"; do
        lsof -ti :$port | xargs kill -9 2>/dev/null || true
    done
    
    echo "🌐 清理所有Docker网络..."
    docker network prune -f
    
    echo "🧹 清理Docker系统..."
    docker system prune -af
    
    echo "✅ 紧急停止完成！"
}; _seed_emergency_stop'

echo "✅ SEED邮件系统Docker别名已加载！"
# 系统总览命令
alias seed-overview='function _seed_overview(){
    echo "🌟 启动SEED邮件系统综合总览"
    echo "================================"

    # 检查Python环境
    if ! command -v python3 &> /dev/null; then
        echo "❌ 未找到Python3，请确保已正确安装"
        return 1
    fi

    # 检查必要的依赖
    echo "📦 检查依赖..."
    python3 -c "import flask" 2>/dev/null || {
        echo "❌ 缺少Flask依赖，正在安装..."
        pip3 install flask 2>/dev/null || echo "⚠️  请手动安装: pip3 install flask"
    }

    # 检查端口占用
    if lsof -ti :4257 >/dev/null 2>&1; then
        echo "⚠️  端口4257已被占用"
        echo "🛑 正在终止占用进程..."
        kill -9 $(lsof -ti :4257) 2>/dev/null || true
        sleep 2
    fi

    # 启动系统总览应用
    echo "🚀 启动系统总览服务器..."
    echo "🌐 访问地址: http://localhost:4257"
    echo ""
    echo "🎯 功能特性:"
    echo "  • 实时项目状态监控"
    echo "  • 一键项目启动/停止"
    echo "  • 代码结构浏览"
    echo "  • 技术文档查看"
    echo "  • 自动化测试"
    echo "  • 实践指南"
    echo ""
    echo "📋 项目概览:"
    echo "  • 29基础版   - 端口5000 (基础邮件系统)"
    echo "  • 29-1真实版 - 端口5001 (多提供商仿真)"
    echo "  • 30 AI版    - 端口5002 (智能钓鱼)"
    echo "  • 31高级版   - 端口5003 (OpenAI APT)"
    echo ""
    echo "💡 操作提示:"
    echo "  • 使用浏览器访问上述地址"
    echo "  • 可以同时运行多个项目"
    echo "  • 按Ctrl+C停止服务器"
    echo ""

    # 启动服务器
    cd /home/parallels/seed-email-system/examples/.not_ready_examples
    python3 system_overview_app.py
}; _seed_overview'

echo "💡 输入 'seed-help' 查看所有可用命令"
echo "🌟 输入 'seed-overview' 启动系统总览网页"
