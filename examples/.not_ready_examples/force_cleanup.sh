#!/bin/bash

echo "🧹====================================================================🧹"
echo "           SEED邮件系统 - 强力清理工具"
echo "           确保29/29-1/30项目完全停止"
echo "🧹====================================================================🧹"
echo ""

# 设置清理模式和密码
FORCE_MODE=${1:-"normal"}
SUDO_PASSWORD=${2:-"200505071210"}

if [ "$FORCE_MODE" = "force" ]; then
    echo "⚠️  强制清理模式已启用！这将停止所有相关容器和服务"
    echo "🔐 将自动处理权限问题"
else
    echo "🔧 标准清理模式 (使用 './force_cleanup.sh force' 启用强制模式)"
fi

export SUDO_PASSWORD

echo ""

# 函数：停止并删除匹配的容器
cleanup_containers() {
    local pattern="$1"
    local description="$2"
    
    echo "🔍 查找 $description 容器..."
    local containers=$(docker ps -a --filter "name=$pattern" --format "{{.Names}}" 2>/dev/null)
    
    if [ -n "$containers" ]; then
        echo "📦 发现以下容器:"
        echo "$containers" | sed 's/^/   - /'
        echo ""
        
        echo "🛑 停止容器..."
        echo "$containers" | xargs docker stop 2>/dev/null || true
        
        if [ "$FORCE_MODE" = "force" ]; then
            echo "🗑️  删除容器..."
            echo "$containers" | xargs docker rm -f 2>/dev/null || true
        fi
        
        echo "✅ $description 清理完成"
    else
        echo "   ✅ 没有发现 $description 容器"
    fi
    echo ""
}

# 函数：清理Docker Compose项目
cleanup_compose_project() {
    local project_dir="$1"
    local project_name="$2"
    
    echo "🔧 清理 $project_name..."
    
    if [ -d "$project_dir" ]; then
        cd "$project_dir"
        
        # 停止Web服务
        if [ -f "webmail.log" ]; then
            echo "   🌐 停止Web服务..."
            pkill -f "webmail_server.py" 2>/dev/null || true
        fi
        
        # 尝试标准停止
        if [ -f "docker-compose.yml" ]; then
            echo "   📄 使用docker-compose停止..."
            docker-compose down --remove-orphans 2>/dev/null || true
            
            if [ "$FORCE_MODE" = "force" ]; then
                echo "   🗑️  强制清理volumes..."
                docker-compose down -v --remove-orphans 2>/dev/null || true
            fi
        fi
        
        # 清理output目录的compose
        if [ -d "output" ]; then
            cd output
            if [ -f "docker-compose.yml" ]; then
                echo "   📄 清理output中的容器..."
                docker-compose down --remove-orphans 2>/dev/null || true
                
                if [ "$FORCE_MODE" = "force" ]; then
                    docker-compose down -v --remove-orphans 2>/dev/null || true
                fi
            fi
            
            # 清理Docker创建的root权限目录
            if [ -d "mail-"* ] 2>/dev/null; then
                echo "   🔐 清理Docker权限目录..."
                if [ "$FORCE_MODE" = "force" ]; then
                    if [ -n "${SUDO_PASSWORD:-}" ]; then
                        echo "$SUDO_PASSWORD" | sudo -S rm -rf mail-*-data 2>/dev/null || true
                        echo "$SUDO_PASSWORD" | sudo -S chown -R $(whoami):$(whoami) . 2>/dev/null || true
                    else
                        sudo rm -rf mail-*-data 2>/dev/null || true
                        sudo chown -R $(whoami):$(whoami) . 2>/dev/null || true
                    fi
                fi
            fi
            cd ..
        fi
        
        # 清理services compose (30项目)
        if [ -f "docker-compose-services.yml" ]; then
            echo "   🤖 清理AI和服务容器..."
            docker-compose -f docker-compose-services.yml down --remove-orphans 2>/dev/null || true
            
            if [ "$FORCE_MODE" = "force" ]; then
                docker-compose -f docker-compose-services.yml down -v --remove-orphans 2>/dev/null || true
            fi
        fi
        
        cd ..
        echo "   ✅ $project_name 清理完成"
    else
        echo "   ⚠️  $project_name 目录不存在"
    fi
    echo ""
}

# 开始清理过程
echo "🚀 开始SEED项目清理..."
echo ""

# 1. 清理具体的SEED容器
echo "📦 第一阶段: 清理SEED相关容器"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cleanup_containers "mail-*" "邮件服务器"
cleanup_containers "seed*" "SEED服务"
cleanup_containers "gophish*" "Gophish钓鱼平台"
cleanup_containers "ollama*" "Ollama AI服务"
cleanup_containers "*phishing*" "钓鱼相关服务"
cleanup_containers "as*h-*" "SEED网络主机"
cleanup_containers "as*brd-*" "SEED网络路由器"
cleanup_containers "seedemu*" "SEED网络服务"

# 2. 清理Docker Compose项目
echo "📁 第二阶段: 清理Docker Compose项目"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cleanup_compose_project "29-email-system" "29基础版邮件系统"
cleanup_compose_project "29-1-email-system" "29-1真实版邮件系统"
cleanup_compose_project "30-phishing-ai-system" "30钓鱼AI系统"

# 3. 清理特定端口占用
echo "🔌 第三阶段: 检查端口占用"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# SEED项目常用端口
seed_ports=(2525 2526 2527 5870 5871 5872 1430 1431 1432 9930 9931 9932 5000 3333 8080 11434 8001 8002 8003 3000 9090)

for port in "${seed_ports[@]}"; do
    if lsof -ti :$port >/dev/null 2>&1; then
        echo "⚠️  端口 $port 被占用"
        if [ "$FORCE_MODE" = "force" ]; then
            echo "   🔫 强制释放端口 $port..."
            lsof -ti :$port | xargs kill -9 2>/dev/null || true
        else
            echo "   💡 使用强制模式释放: ./force_cleanup.sh force"
        fi
    else
        echo "✅ 端口 $port 空闲"
    fi
done

echo ""

# 4. 清理Docker网络
echo "🌐 第四阶段: 清理Docker网络"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 查找SEED相关网络
seed_networks=$(docker network ls --filter "name=output" --filter "name=seed" --filter "name=net_" --format "{{.Name}}" 2>/dev/null)

if [ -n "$seed_networks" ]; then
    echo "🔍 发现SEED网络:"
    echo "$seed_networks" | sed 's/^/   - /'
    echo ""
    
    if [ "$FORCE_MODE" = "force" ]; then
        echo "🗑️  删除SEED网络..."
        echo "$seed_networks" | xargs docker network rm 2>/dev/null || true
    else
        echo "💡 使用强制模式删除网络: ./force_cleanup.sh force"
    fi
else
    echo "✅ 没有发现SEED相关网络"
fi

# 清理孤立网络
echo ""
echo "🧹 清理孤立网络..."
docker network prune -f >/dev/null 2>&1 || true
echo "✅ 孤立网络清理完成"

echo ""

# 5. 清理Docker系统 (可选)
if [ "$FORCE_MODE" = "force" ]; then
    echo "🧽 第五阶段: Docker系统清理"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    echo "🗑️  清理未使用的容器、网络、镜像..."
    docker system prune -f >/dev/null 2>&1 || true
    
    echo "📦 清理未使用的卷..."
    docker volume prune -f >/dev/null 2>&1 || true
    
    echo "✅ Docker系统清理完成"
    echo ""
fi

# 6. 验证清理结果
echo "✅ 第六阶段: 验证清理结果"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo "🔍 剩余的SEED相关容器:"
remaining_containers=$(docker ps -a --filter "name=mail-" --filter "name=seed" --filter "name=as" --format "{{.Names}}" 2>/dev/null)

if [ -n "$remaining_containers" ]; then
    echo "⚠️  仍有容器运行:"
    echo "$remaining_containers" | sed 's/^/   - /'
    echo ""
    echo "💡 建议运行强制清理: ./force_cleanup.sh force"
else
    echo "✅ 所有SEED容器已清理完成"
fi

echo ""
echo "🔌 关键端口状态:"
critical_ports=(2525 5000 3333 8080)
all_clear=true

for port in "${critical_ports[@]}"; do
    if lsof -ti :$port >/dev/null 2>&1; then
        echo "❌ 端口 $port 仍被占用"
        all_clear=false
    else
        echo "✅ 端口 $port 可用"
    fi
done

echo ""

# 7. 生成清理报告
echo "📊 清理报告"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ "$all_clear" = true ] && [ -z "$remaining_containers" ]; then
    echo "🎉 完美清理！所有SEED项目已完全停止"
    echo "✅ 可以安全重新启动项目"
else
    echo "⚠️  清理不完整，建议采取以下措施:"
    echo ""
    echo "🔧 故障排除步骤:"
    echo "1. 运行强制清理: ./force_cleanup.sh force"
    echo "2. 重启Docker服务: sudo systemctl restart docker"
    echo "3. 重启系统: sudo reboot"
    echo "4. 检查进程: ps aux | grep docker"
fi

echo ""
echo "🛠️  可用的管理命令:"
echo "   seed-status      - 检查系统状态"
echo "   seed-29          - 启动29基础版"
echo "   seed-29-1        - 启动29-1真实版"
echo "   seed-30          - 启动30 AI版"
echo ""

echo "🧹====================================================================🧹"
echo "                        清理完成"
echo "🧹====================================================================🧹"
