#!/bin/bash

# 29-email-system 项目别名快速加载器
# 使用方法: source load_aliases.sh

echo "🐳 加载29项目Docker别名..."

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

# 29项目专用别名
alias start-29='function _start_29(){
    echo "🚀 启动29邮件系统..."
    if [ ! -f "output/docker-compose.yml" ]; then
        echo "📦 生成配置..."
        python3 email_simple.py arm
    fi
    cd output && dcupd && cd ..
    echo "✅ 启动完成! Web界面: http://localhost:5000"
}; _start_29'

alias stop-29='function _stop_29(){
    echo "🛑 停止29邮件系统..."
    if [ -d "output" ]; then
        cd output && dcdown && cd ..
    fi
    echo "✅ 系统已停止"
}; _stop_29'

alias web-29='function _web_29(){
    echo "🌐 启动Web管理界面..."
    ./start_webmail.sh
}; _web_29'

alias mail-test='function _mail_test(){
    echo "📧 邮件服务测试"
    echo "可用邮件服务器:"
    dockps | grep mail
    echo ""
    echo "测试邮件发送:"
    echo "docker exec -it [邮件服务器] setup email add [用户名@域名]"
}; _mail_test'

alias logs-29='function _logs_29(){
    echo "📋 29项目日志查看"
    if [ -d "output" ]; then
        cd output
        if [ -n "$1" ]; then
            dclogf "$1"
        else
            echo "可用服务:"
            dcps
            echo ""
            echo "使用: logs-29 <服务名> 查看特定服务日志"
            dclogf
        fi
        cd ..
    else
        echo "❌ 项目未启动"
    fi
}; _logs_29'

alias status-29='function _status_29(){
    echo "📊 29-email-system 状态"
    echo "========================"
    echo ""
    echo "🐳 容器状态:"
    if [ -d "output" ]; then
        cd output && dcps && cd ..
    else
        echo "❌ 项目未部署"
    fi
    echo ""
    echo "🌐 Web服务:"
    if curl -s http://localhost:5000 > /dev/null 2>&1; then
        echo "✅ Web界面: http://localhost:5000"
    else
        echo "❌ Web界面未运行"
    fi
    echo ""
    echo "📧 邮件服务:"
    if nc -z localhost 2525 2>/dev/null; then
        echo "✅ SMTP服务: localhost:2525"
    else
        echo "❌ SMTP服务未运行"
    fi
}; _status_29'

# 显示可用命令
alias help-29='function _help_29(){
    echo "📚 29-email-system 专用命令"
    echo "============================"
    echo ""
    echo "🚀 项目管理:"
    echo "  start-29         - 启动29邮件系统"
    echo "  stop-29          - 停止29邮件系统"
    echo "  status-29        - 检查系统状态"
    echo "  web-29           - 启动Web管理界面"
    echo ""
    echo "📧 邮件管理:"
    echo "  mail-test        - 邮件服务测试指南"
    echo ""
    echo "📋 日志管理:"
    echo "  logs-29 [服务]   - 查看日志"
    echo ""
    echo "🐳 Docker命令:"
    echo "  dcup/dcdown      - 启动/停止容器"
    echo "  dockps           - 查看容器状态"
    echo "  docksh <id>      - 进入容器"
    echo ""
    echo "💡 使用 seed-help 查看完整命令列表"
}; _help_29'

echo "✅ 29项目别名已加载!"
echo "💡 输入 'help-29' 查看项目专用命令"
echo "💡 输入 'seed-help' 查看所有命令"
