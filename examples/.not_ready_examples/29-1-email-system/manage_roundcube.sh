#!/bin/bash
#
# Roundcube Webmail 管理脚本
# 用于 SEED 邮件系统 (29-email-system)
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose-roundcube.yml"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查邮件服务器是否运行
check_mail_servers() {
    print_info "检查邮件服务器状态..."
    
    cd "$SCRIPT_DIR/output" 2>/dev/null || {
        print_error "output目录不存在，请先运行 email_simple.py 生成配置"
        return 1
    }
    
    MAIL_SERVERS=$(docker-compose ps 2>/dev/null | grep -E "mail-15[0-2]" | grep "Up" | wc -l)
    
    if [ "$MAIL_SERVERS" -eq 3 ]; then
        print_success "3个邮件服务器都在运行"
        return 0
    else
        print_warning "只有 $MAIL_SERVERS 个邮件服务器在运行（应该是3个）"
        print_info "启动邮件服务器..."
        docker-compose up -d
        sleep 10
        return 0
    fi
}

# 启动Roundcube
start_roundcube() {
    print_info "启动 Roundcube Webmail..."
    
    # 检查邮件服务器
    check_mail_servers || return 1
    
    # 启动Roundcube
    cd "$SCRIPT_DIR"
    docker-compose -f "$COMPOSE_FILE" up -d
    
    if [ $? -eq 0 ]; then
        print_success "Roundcube Webmail 启动成功！"
        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "  📬 Roundcube Webmail: http://localhost:8082"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
        echo "测试账户："
        echo "  • user@qq.com (密码: password123)"
        echo "  • user@gmail.com (密码: password123)"
        echo "  • user@163.com (密码: password123)"
        echo ""
        echo "支持的邮件服务商："
        echo "  • qq.com (QQ邮箱)"
        echo "  • 163.com (163邮箱)"
        echo "  • gmail.com (Gmail)"
        echo "  • outlook.com (Outlook)"
        echo "  • company.cn (企业邮箱)"
        echo "  • startup.net (自建邮箱)"
        echo ""
    else
        print_error "Roundcube 启动失败"
        return 1
    fi
}

# 停止Roundcube
stop_roundcube() {
    print_info "停止 Roundcube Webmail..."
    cd "$SCRIPT_DIR"
    docker-compose -f "$COMPOSE_FILE" down
    
    if [ $? -eq 0 ]; then
        print_success "Roundcube Webmail 已停止"
    else
        print_error "停止失败"
        return 1
    fi
}

# 重启Roundcube
restart_roundcube() {
    print_info "重启 Roundcube Webmail..."
    stop_roundcube
    sleep 2
    start_roundcube
}

# 查看状态
status_roundcube() {
    print_info "Roundcube 服务状态："
    echo ""
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(roundcube|NAME)"
    echo ""
    
    # 检查服务是否可访问
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:8081 | grep -q "200\|302"; then
        print_success "Roundcube 网页可访问: http://localhost:8081"
    else
        print_warning "Roundcube 网页暂时无法访问"
    fi
}

# 查看日志
logs_roundcube() {
    print_info "Roundcube 日志 (按 Ctrl+C 退出)："
    docker logs -f roundcube-webmail-29-1
}

# 创建测试账户（29-1版本：6个邮件服务商）
create_test_accounts() {
    print_info "创建测试邮件账户..."
    
    # QQ邮箱
    printf "password123\npassword123\n" | docker exec -i mail-qq-tencent setup email add user@qq.com 2>/dev/null
    if [ $? -eq 0 ]; then
        print_success "创建 user@qq.com"
    else
        print_warning "user@qq.com 可能已存在"
    fi
    
    # 163邮箱
    printf "password123\npassword123\n" | docker exec -i mail-163-netease setup email add user@163.com 2>/dev/null
    if [ $? -eq 0 ]; then
        print_success "创建 user@163.com"
    else
        print_warning "user@163.com 可能已存在"
    fi
    
    # Gmail
    printf "password123\npassword123\n" | docker exec -i mail-gmail-google setup email add user@gmail.com 2>/dev/null
    if [ $? -eq 0 ]; then
        print_success "创建 user@gmail.com"
    else
        print_warning "user@gmail.com 可能已存在"
    fi
    
    # Outlook
    printf "password123\npassword123\n" | docker exec -i mail-outlook-microsoft setup email add user@outlook.com 2>/dev/null
    if [ $? -eq 0 ]; then
        print_success "创建 user@outlook.com"
    else
        print_warning "user@outlook.com 可能已存在"
    fi
    
    # 企业邮箱
    printf "password123\npassword123\n" | docker exec -i mail-company-aliyun setup email add admin@company.cn 2>/dev/null
    if [ $? -eq 0 ]; then
        print_success "创建 admin@company.cn"
    else
        print_warning "admin@company.cn 可能已存在"
    fi
    
    # 自建邮箱
    printf "password123\npassword123\n" | docker exec -i mail-startup-selfhosted setup email add founder@startup.net 2>/dev/null
    if [ $? -eq 0 ]; then
        print_success "创建 founder@startup.net"
    else
        print_warning "founder@startup.net 可能已存在"
    fi
    
    echo ""
    print_success "测试账户准备完成！可以使用这些账户登录 Roundcube"
    echo ""
    echo "测试账户列表："
    echo "  • user@qq.com / password123"
    echo "  • user@163.com / password123"
    echo "  • user@gmail.com / password123"
    echo "  • user@outlook.com / password123"
    echo "  • admin@company.cn / password123"
    echo "  • founder@startup.net / password123"
}

# 显示帮助信息
show_help() {
    echo ""
    echo "Roundcube Webmail 管理脚本"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "用法: $0 <command>"
    echo ""
    echo "命令："
    echo "  start       - 启动 Roundcube Webmail"
    echo "  stop        - 停止 Roundcube Webmail"
    echo "  restart     - 重启 Roundcube Webmail"
    echo "  status      - 查看运行状态"
    echo "  logs        - 查看实时日志"
    echo "  accounts    - 创建测试邮件账户"
    echo "  help        - 显示此帮助信息"
    echo ""
    echo "示例："
    echo "  $0 start     # 启动 Roundcube"
    echo "  $0 status    # 查看状态"
    echo "  $0 accounts  # 创建测试账户"
    echo ""
}

# 主程序
main() {
    case "$1" in
        start)
            start_roundcube
            ;;
        stop)
            stop_roundcube
            ;;
        restart)
            restart_roundcube
            ;;
        status)
            status_roundcube
            ;;
        logs)
            logs_roundcube
            ;;
        accounts)
            create_test_accounts
            ;;
        help|--help|-h|"")
            show_help
            ;;
        *)
            print_error "未知命令: $1"
            show_help
            exit 1
            ;;
    esac
}

main "$@"

