#!/bin/bash

echo "🚀 启动高级网络安全实验室..."
echo "==============================================="

# 检查Python依赖
echo "🔧 检查系统依赖..."
python -c "import flask" 2>/dev/null || {
    echo "正在安装Flask..."
    pip install flask
}

python -c "import requests" 2>/dev/null || {
    echo "正在安装Requests..."
    pip install requests
}

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 创建日志目录
mkdir -p "$SCRIPT_DIR/logs"

echo ""
echo "🎯 启动基础钓鱼仿真系统..."
echo "==============================================="

# 启动基础系统
echo "📊 启动损失评估仪表板..."
cd "$SCRIPT_DIR/dashboard" && python dashboard.py > ../logs/dashboard.log 2>&1 &
sleep 2

echo "🚨 启动XSS漏洞服务器..."
cd "$SCRIPT_DIR/vulnerable_servers/web_xss" && python xss_server.py > ../../logs/xss_server.log 2>&1 &
sleep 2

echo "💾 启动SQL注入服务器..."
cd "$SCRIPT_DIR/vulnerable_servers/db_sqli" && python sqli_server.py > ../../logs/sqli_server.log 2>&1 &
sleep 2

echo "🔐 启动Heartbleed仿真服务器..."
cd "$SCRIPT_DIR/vulnerable_servers/heartbleed_sim" && python heartbleed_server.py > ../../logs/heartbleed_server.log 2>&1 &
sleep 2

echo ""
echo "⚡ 启动高级安全实验模块..."
echo "==============================================="

echo "🎯 启动APT攻击链仿真系统..."
cd "$SCRIPT_DIR" && python advanced_security_lab.py > logs/apt_simulation.log 2>&1 &
sleep 3

echo "🦠 启动恶意软件分析沙箱..."
cd "$SCRIPT_DIR/malware_analysis" && python malware_sandbox.py > ../logs/malware_sandbox.log 2>&1 &
sleep 3

echo "⚔️ 启动红蓝对抗演练平台..."
cd "$SCRIPT_DIR/red_blue_teams" && python red_blue_exercise.py > ../logs/red_blue_exercise.log 2>&1 &
sleep 3

echo "🏠 启动IoT安全实验室..."
cd "$SCRIPT_DIR/IoT_security" && python iot_security_lab.py > ../logs/iot_security.log 2>&1 &
sleep 3

echo ""
echo "🌐 所有服务已启动完成！"
echo "==============================================="
echo ""
echo "📋 基础钓鱼仿真系统:"
echo "  - 损失评估仪表板: http://localhost:5888"
echo "  - XSS漏洞服务器: http://localhost:5001"
echo "  - SQL注入服务器: http://localhost:5002"
echo "  - Heartbleed仿真: http://localhost:5003"
echo "  - Gophish管理面板: https://localhost:3333"
echo ""
echo "🔬 高级安全实验室:"
echo "  - APT攻击链仿真: http://localhost:5004"
echo "  - 恶意软件沙箱: http://localhost:5005"
echo "  - 红蓝对抗平台: http://localhost:5006"
echo "  - IoT安全实验室: http://localhost:5007"
echo ""
echo "🎓 实验场景建议:"
echo "  1. 基础渗透测试: 使用基础漏洞服务器"
echo "  2. APT攻击模拟: 使用攻击链仿真系统"  
echo "  3. 恶意软件分析: 使用沙箱分析平台"
echo "  4. 红蓝对抗演练: 使用对抗演练平台"
echo "  5. IoT设备安全: 使用IoT安全实验室"
echo "  6. 综合安全评估: 组合使用所有模块"
echo ""
echo "⚠️  使用提醒:"
echo "  - 仅在授权环境中使用"
echo "  - 定期备份实验数据"
echo "  - 遵守相关法律法规"
echo ""
echo "按 Ctrl+C 停止所有服务"

# 等待用户中断
wait
