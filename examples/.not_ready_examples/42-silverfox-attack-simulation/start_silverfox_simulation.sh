#!/bin/bash

# 银狐木马攻击仿真复现实验 - 启动脚本
# Silver Fox Trojan Attack Simulation Reproduction - Startup Script

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查环境
check_environment() {
    log_info "检查仿真环境..."

    # 检查Python
    if ! command -v python3 &> /dev/null; then
        log_error "未找到Python3，请确保Python3已安装"
        exit 1
    fi

    # 检查Conda环境
    if ! command -v conda &> /dev/null; then
        log_error "未找到Conda，请确保Miniconda已安装"
        exit 1
    fi

    # 检查Docker
    if ! command -v docker &> /dev/null; then
        log_error "未找到Docker，请确保Docker已安装"
        exit 1
    fi

    # 检查端口4257是否被占用
    if lsof -Pi :4257 -sTCP:LISTEN -t >/dev/null ; then
        log_error "端口4257已被占用，请停止占用该端口的程序或使用其他端口"
        exit 1
    fi

    log_success "环境检查通过"
}

# 激活Conda环境
activate_environment() {
    log_info "激活seed-emulator环境..."

    # 检查环境是否存在
    if ! conda env list | grep -q "seed-emulator"; then
        log_error "未找到seed-emulator环境，请先创建该环境"
        exit 1
    fi

    # 激活环境
    source "$(conda info --base)/etc/profile.d/conda.sh"
    conda activate seed-emulator

    log_success "环境激活成功"
}

# 检查依赖包
check_dependencies() {
    log_info "检查Python依赖包..."

    # 检查必需的包
    required_packages=("flask" "pyyaml" "requests")

    for package in "${required_packages[@]}"; do
        if ! python3 -c "import $package" 2>/dev/null; then
            log_error "缺少依赖包: $package"
            log_info "请运行: pip install $package"
            exit 1
        fi
    done

    log_success "依赖包检查通过"
}

# 检查配置文件
check_configurations() {
    log_info "检查配置文件..."

    config_files=(
        "config/attack_chain_config.yaml"
        "config/gophish_config.json"
        "config/network_config.yaml"
    )

    for config_file in "${config_files[@]}"; do
        if [ ! -f "$config_file" ]; then
            log_error "缺少配置文件: $config_file"
            exit 1
        fi
    done

    log_success "配置文件检查通过"
}

# 创建必要的目录
create_directories() {
    log_info "创建必要的目录..."

    directories=(
        "results/logs"
        "results/reports"
        "payloads"
        "simulation_framework"
    )

    for dir in "${directories[@]}"; do
        mkdir -p "$dir"
    done

    log_success "目录创建完成"
}

# 启动Web界面
start_web_interface() {
    log_info "启动Web界面..."

    # 启动Web服务器（后台运行）
    nohup python3 web_interface.py > results/logs/web_interface.log 2>&1 &
    WEB_PID=$!

    # 等待几秒让服务启动
    sleep 3

    # 检查服务是否启动成功
    if kill -0 $WEB_PID 2>/dev/null; then
        log_success "Web界面启动成功 (PID: $WEB_PID)"
        log_info "访问地址: http://localhost:4257"
        echo $WEB_PID > .web_pid
    else
        log_error "Web界面启动失败，请检查日志: results/logs/web_interface.log"
        exit 1
    fi
}

# 显示启动信息
show_startup_info() {
    echo
    echo "🦊 银狐木马攻击仿真复现实验"
    echo "=================================================="
    echo "Web界面: http://localhost:4257"
    echo "控制台: http://localhost:4257/dashboard"
    echo "系统总览: http://localhost:4257/overview"
    echo "结果查看: http://localhost:4257/results"
    echo "日志查看: http://localhost:4257/logs"
    echo "=================================================="
    echo "启动时间: $(date)"
    echo "=================================================="
    echo
    log_info "仿真系统已就绪，可以开始实验"
    log_info "按 Ctrl+C 停止仿真系统"
}

# 清理函数
cleanup() {
    log_info "正在停止仿真系统..."

    # 停止Web服务
    if [ -f ".web_pid" ]; then
        WEB_PID=$(cat .web_pid)
        if kill -0 $WEB_PID 2>/dev/null; then
            kill $WEB_PID
            log_success "Web服务已停止"
        fi
        rm -f .web_pid
    fi

    # 停止其他可能的后台进程
    # 这里可以添加更多清理逻辑

    log_success "仿真系统已停止"
    exit 0
}

# 主函数
main() {
    echo
    echo "🦊 银狐木马攻击仿真复现实验 - 启动脚本"
    echo "==============================================="

    # 设置清理函数
    trap cleanup SIGINT SIGTERM

    # 执行启动步骤
    check_environment
    activate_environment
    check_dependencies
    check_configurations
    create_directories
    start_web_interface
    show_startup_info

    # 保持脚本运行，等待用户中断
    log_info "仿真系统运行中... 按 Ctrl+C 停止"

    # 等待用户中断
    while true; do
        sleep 1
    done
}

# 检查是否以正确方式调用
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi