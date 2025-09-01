#!/bin/bash

echo "🚀====================================================================🚀"
echo "           SEED邮件系统 - 快速启动脚本"
echo "           一键启动和管理邮件实验环境"
echo "🚀====================================================================🚀"
echo ""

# 项目选择
PROJECT=${1:-""}
ACTION=${2:-"start"}

show_usage() {
    echo "📖 使用方法:"
    echo "   ./quick_start.sh <项目> [动作]"
    echo ""
    echo "🎯 支持的项目:"
    echo "   29     - 基础版邮件系统 (带Web界面)"
    echo "   29-1   - 真实版邮件系统 (真实ISP)"
    echo "   30     - AI钓鱼系统 (AI驱动)"
    echo ""
    echo "⚙️  支持的动作:"
    echo "   start  - 启动项目 (默认)"
    echo "   stop   - 停止项目"
    echo "   status - 查看状态"
    echo "   test   - 运行测试"
    echo "   clean  - 清理环境"
    echo ""
    echo "💡 示例:"
    echo "   ./quick_start.sh 29        # 启动29项目"
    echo "   ./quick_start.sh 29-1 test # 测试29-1项目"
    echo "   ./quick_start.sh 30 stop   # 停止30项目"
    echo ""
}

# 设置环境
setup_environment() {
    echo "📦 设置运行环境..."
    cd /home/parallels/seed-email-system
    source development.env 2>/dev/null || true
    conda activate seed-emulator 2>/dev/null || true
    cd examples/.not_ready_examples/
    
    # 加载别名
    source docker_aliases.sh 2>/dev/null || true
    echo "   ✅ 环境设置完成"
}

# 启动项目
start_project() {
    local project=$1
    echo "🚀 启动 $project 项目..."
    
    case $project in
        "29")
            if command -v seed-29 &> /dev/null; then
                seed-29
            else
                echo "   📦 使用手动启动方式..."
                cd 29-email-system
                if [ ! -f "output/docker-compose.yml" ]; then
                    python3 email_simple.py arm
                fi
                cd output && docker-compose up -d
                cd .. && nohup python3 webmail_server.py > webmail.log 2>&1 &
                echo "   ✅ 29项目启动完成！"
                echo "   🌐 Web界面: http://localhost:5000"
                echo "   🗺️ 网络图: http://localhost:8080/map.html"
            fi
            ;;
            
        "29-1")
            if command -v seed-29-1 &> /dev/null; then
                seed-29-1
            else
                echo "   📦 使用手动启动方式..."
                cd 29-1-email-system
                if [ ! -f "output/docker-compose.yml" ]; then
                    python3 email_realistic.py arm
                fi
                cd output && docker-compose up -d
                echo "   ✅ 29-1项目启动完成！"
                echo "   🗺️ 网络图: http://localhost:8080/map.html"
            fi
            ;;
            
        "30")
            if command -v seed-30 &> /dev/null; then
                seed-30
            else
                echo "   📦 使用手动启动方式..."
                cd 30-phishing-ai-system
                ./start_phishing_ai.sh
            fi
            ;;
            
        *)
            echo "❌ 未知项目: $project"
            show_usage
            return 1
            ;;
    esac
}

# 停止项目
stop_project() {
    local project=$1
    echo "🛑 停止 $project 项目..."
    
    case $project in
        "29")
            cd 29-email-system
            pkill -f "webmail_server.py" 2>/dev/null || true
            if [ -d "output" ]; then
                cd output && docker-compose down --remove-orphans
            fi
            echo "   ✅ 29项目已停止"
            ;;
            
        "29-1")
            cd 29-1-email-system
            if [ -d "output" ]; then
                cd output && docker-compose down --remove-orphans
            fi
            echo "   ✅ 29-1项目已停止"
            ;;
            
        "30")
            cd 30-phishing-ai-system
            if [ -f "stop_phishing_ai.sh" ]; then
                ./stop_phishing_ai.sh
            else
                docker-compose down --remove-orphans 2>/dev/null || true
                docker-compose -f docker-compose-services.yml down --remove-orphans 2>/dev/null || true
            fi
            echo "   ✅ 30项目已停止"
            ;;
            
        "all")
            echo "   🧹 停止所有项目..."
            if [ -f "force_cleanup.sh" ]; then
                ./force_cleanup.sh
            else
                for p in 29 29-1 30; do
                    stop_project $p
                done
            fi
            echo "   ✅ 所有项目已停止"
            ;;
            
        *)
            echo "❌ 未知项目: $project"
            return 1
            ;;
    esac
}

# 查看状态
show_status() {
    local project=$1
    echo "📊 查看 $project 项目状态..."
    
    # 容器状态
    echo ""
    echo "🐳 Docker容器状态:"
    case $project in
        "29")
            docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "(mail-15|as15|seedemu)" | head -10
            ;;
        "29-1")
            docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "(mail-|as.*h-)" | head -10
            ;;
        "30")
            docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "(gophish|ollama|phishing)" | head -10
            ;;
        "all")
            docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "(mail-|as.*h-|seedemu|gophish|ollama)" | head -15
            ;;
    esac
    
    # 端口状态
    echo ""
    echo "🔌 关键端口状态:"
    ports=(5000 8080 2525 2526 2527 3333 11434)
    for port in "${ports[@]}"; do
        if lsof -ti :$port >/dev/null 2>&1; then
            echo "   ✅ $port 端口正在使用"
        else
            echo "   ⚪ $port 端口空闲"
        fi
    done
    
    # 访问地址
    echo ""
    echo "🎯 访问地址:"
    if lsof -ti :5000 >/dev/null 2>&1; then
        echo "   🌐 Web界面: http://localhost:5000"
    fi
    if lsof -ti :8080 >/dev/null 2>&1; then
        echo "   🗺️ 网络图: http://localhost:8080/map.html"
    fi
    if lsof -ti :3333 >/dev/null 2>&1; then
        echo "   🎣 Gophish: https://localhost:3333"
    fi
}

# 运行测试
run_test() {
    local project=$1
    echo "🧪 运行 $project 项目测试..."
    
    if [ -f "test_integration.sh" ]; then
        ./test_integration.sh $project
    else
        echo "❌ 找不到集成测试脚本"
        return 1
    fi
}

# 清理环境
clean_environment() {
    local project=$1
    echo "🧹 清理 $project 项目环境..."
    
    if [ "$project" = "all" ]; then
        if [ -f "force_cleanup.sh" ]; then
            ./force_cleanup.sh force
        else
            echo "❌ 找不到清理脚本"
            return 1
        fi
    else
        stop_project $project
        
        # 清理特定项目的数据
        case $project in
            "29")
                cd 29-email-system 2>/dev/null || return
                sudo rm -rf output/mail-*-data 2>/dev/null || true
                rm -f webmail.log 2>/dev/null || true
                ;;
            "29-1")
                cd 29-1-email-system 2>/dev/null || return
                sudo rm -rf output/mail-*-data 2>/dev/null || true
                ;;
            "30")
                cd 30-phishing-ai-system 2>/dev/null || return
                docker volume prune -f 2>/dev/null || true
                ;;
        esac
        
        echo "   ✅ $project 项目清理完成"
    fi
}

# 主逻辑
main() {
    if [ -z "$PROJECT" ]; then
        echo "🎯 SEED邮件系统管理工具"
        echo ""
        show_usage
        
        echo "📋 当前系统状态:"
        show_status "all"
        return 0
    fi
    
    # 设置环境
    setup_environment
    
    # 执行动作
    case $ACTION in
        "start")
            start_project $PROJECT
            echo ""
            echo "⏳ 等待服务启动..."
            sleep 5
            show_status $PROJECT
            ;;
        "stop")
            stop_project $PROJECT
            ;;
        "status")
            show_status $PROJECT
            ;;
        "test")
            run_test $PROJECT
            ;;
        "clean")
            clean_environment $PROJECT
            ;;
        *)
            echo "❌ 未知动作: $ACTION"
            show_usage
            return 1
            ;;
    esac
}

# 检查参数
if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    show_usage
    exit 0
fi

# 执行主逻辑
main

echo ""
echo "🚀====================================================================🚀"
echo "                        操作完成"
echo "🚀====================================================================🚀"
