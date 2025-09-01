#!/bin/bash

# 29-1-email-system 项目别名快速加载器
# 使用方法: source load_aliases.sh

echo "🌐 加载29-1项目Docker别名..."

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

# 29-1项目专用别名
alias start-29-1='function _start_29_1(){
    echo "🚀 启动29-1真实邮件系统..."
    if [ ! -f "output/docker-compose.yml" ]; then
        echo "📦 生成真实网络配置..."
        python3 email_realistic.py arm
    fi
    cd output && dcupd && cd ..
    echo "✅ 真实邮件网络启动完成!"
    echo "🌍 网络包含:"
    echo "   - 4个Internet Exchange (北京/上海/广州/海外)"
    echo "   - 3个ISP (电信/联通/移动)"
    echo "   - 6个真实邮件服务商 (QQ/163/Gmail/Outlook/企业/自建)"
    echo "   - 4个用户网络区域"
}; _start_29_1'

alias stop-29-1='function _stop_29_1(){
    echo "🛑 停止29-1邮件系统..."
    if [ -d "output" ]; then
        cd output && dcdown && cd ..
    fi
    echo "✅ 系统已停止"
}; _stop_29_1'

alias test-29-1='function _test_29_1(){
    echo "🧪 运行29-1网络测试..."
    if [ -f "test_network.py" ]; then
        python3 test_network.py
    else
        echo "❌ 未找到测试脚本"
    fi
}; _test_29_1'

alias status-29-1='function _status_29_1(){
    echo "📊 29-1-email-system 状态"
    echo "=========================="
    echo ""
    echo "🐳 容器状态:"
    if [ -d "output" ]; then
        cd output
        echo "总容器数: $(dcps | wc -l)"
        echo "运行状态:"
        dcps | head -10
        cd ..
    else
        echo "❌ 项目未部署"
    fi
    echo ""
    echo "🌐 网络架构:"
    echo "  - Internet Exchange: 4个 (IX-100至103)"
    echo "  - ISP网络: 3个 (AS-2,3,4)"
    echo "  - 邮件服务商: 6个 (AS-200至205)"
    echo "  - 用户网络: 4个 (AS-150至153)"
    echo ""
    echo "📧 邮件服务商分布:"
    echo "  - QQ邮箱 (AS-200): 广州"
    echo "  - 163邮箱 (AS-201): 上海"
    echo "  - Gmail (AS-202): 海外"
    echo "  - Outlook (AS-203): 海外"
    echo "  - 企业邮箱 (AS-204): 上海"
    echo "  - 自建邮箱 (AS-205): 北京"
}; _status_29_1'

alias network-test='function _network_test(){
    if [ $# -lt 2 ]; then
        echo "🌐 网络连通性测试"
        echo "使用方法: network-test <源容器> <目标IP>"
        echo ""
        echo "常用容器:"
        echo "  北京用户: as150h-host_0-10.150.0.71"
        echo "  上海用户: as151h-host_0-10.151.0.71"
        echo "  广州用户: as152h-host_0-10.152.0.71"
        echo ""
        echo "邮件服务器IP:"
        echo "  QQ邮箱: 10.200.0.71"
        echo "  163邮箱: 10.201.0.71"
        echo "  Gmail: 10.202.0.71"
        echo "  Outlook: 10.203.0.71"
        echo ""
        echo "示例: network-test as150h-host_0-10.150.0.71 10.200.0.71"
        return 1
    fi
    
    local source="$1"
    local target="$2"
    
    echo "🌐 测试连通性: $source → $target"
    docker exec -it "$source" ping -c 4 "$target"
}; _network_test'

alias route-test='function _route_test(){
    if [ $# -lt 2 ]; then
        echo "🛣️ 路由跟踪测试"
        echo "使用方法: route-test <源容器> <目标IP>"
        echo "示例: route-test as150h-host_0-10.150.0.71 10.200.0.71"
        return 1
    fi
    
    local source="$1"
    local target="$2"
    
    echo "🛣️ 跟踪路由: $source → $target"
    docker exec -it "$source" traceroute "$target" 2>/dev/null || \
    docker exec -it "$source" tracepath "$target"
}; _route_test'

alias bgp-routes='function _bgp_routes(){
    echo "🛣️ BGP路由表查看"
    if [ -z "$1" ]; then
        echo "可用的BGP路由器:"
        dockps | grep "brd-r" | head -5
        echo ""
        echo "使用方法: bgp-routes <路由器容器>"
        echo "例如: bgp-routes as2brd-r100-10.100.0.2"
        return 1
    fi
    
    local router="$1"
    echo "查看 $router 的BGP路由表:"
    docker exec -it "$router" birdc show route
}; _bgp_routes'

alias logs-29-1='function _logs_29_1(){
    echo "📋 29-1项目日志查看"
    if [ -d "output" ]; then
        cd output
        if [ -n "$1" ]; then
            dclogf "$1"
        else
            echo "可用服务 (显示前10个):"
            dcps | head -10
            echo ""
            echo "使用: logs-29-1 <服务名> 查看特定服务日志"
        fi
        cd ..
    else
        echo "❌ 项目未启动"
    fi
}; _logs_29_1'

# 显示可用命令
alias help-29-1='function _help_29_1(){
    echo "📚 29-1-email-system 专用命令"
    echo "==============================="
    echo ""
    echo "🚀 项目管理:"
    echo "  start-29-1       - 启动29-1真实邮件系统"
    echo "  stop-29-1        - 停止29-1邮件系统"
    echo "  status-29-1      - 检查系统状态"
    echo "  test-29-1        - 运行网络测试"
    echo ""
    echo "🌐 网络测试:"
    echo "  network-test     - 网络连通性测试"
    echo "  route-test       - 路由跟踪测试"
    echo "  bgp-routes       - BGP路由表查看"
    echo ""
    echo "📋 日志管理:"
    echo "  logs-29-1 [服务] - 查看日志"
    echo ""
    echo "🐳 Docker命令:"
    echo "  dcup/dcdown      - 启动/停止容器"
    echo "  dockps           - 查看容器状态"
    echo "  docksh <id>      - 进入容器"
    echo ""
    echo "💡 使用 seed-help 查看完整命令列表"
}; _help_29_1'

echo "✅ 29-1项目别名已加载!"
echo "💡 输入 'help-29-1' 查看项目专用命令"
echo "💡 输入 'seed-help' 查看所有命令"
