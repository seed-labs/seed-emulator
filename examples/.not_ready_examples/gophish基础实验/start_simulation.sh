#!/bin/bash

echo "🚀 启动钓鱼后仿真系统..."

# 创建日志目录
mkdir -p logs

# 检查Python依赖
echo "检查Python依赖..."
python -c "import flask" 2>/dev/null || {
    echo "正在安装Flask..."
    pip install flask
}

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 启动各个服务器
echo "启动损失评估仪表板..."
cd "$SCRIPT_DIR/dashboard" && python dashboard.py > ../logs/dashboard.log 2>&1 &

sleep 2

echo "启动XSS漏洞服务器..."
cd "$SCRIPT_DIR/vulnerable_servers/web_xss" && python xss_server.py > ../../logs/xss_server.log 2>&1 &

sleep 2

echo "启动SQL注入漏洞服务器..."
cd "$SCRIPT_DIR/vulnerable_servers/db_sqli" && python sqli_server.py > ../../logs/sqli_server.log 2>&1 &

sleep 2

echo "启动Heartbleed仿真服务器..."
cd "$SCRIPT_DIR/vulnerable_servers/heartbleed_sim" && python heartbleed_server.py > ../../logs/heartbleed_server.log 2>&1 &

sleep 2

echo ""
echo "🌐 所有服务已启动："
echo "  - XSS漏洞服务器: http://localhost:5001"
echo "  - SQL注入服务器: http://localhost:5002" 
echo "  - Heartbleed仿真: http://localhost:5003"
echo "  - 损失评估仪表板: http://localhost:5888"
echo "  - Gophish管理面板: https://localhost:3333"
echo ""
echo "🔧 使用说明："
echo "1. 访问 https://localhost:3333 配置Gophish钓鱼邮件"
echo "2. 配置QQ邮箱SMTP: smtp.qq.com:465"
echo "3. 发送钓鱼邮件后，引导目标访问漏洞服务器"
echo "4. 在损失评估仪表板查看攻击统计和损失评估"
echo ""
echo "按 Ctrl+C 停止所有服务"

# 等待用户中断
wait
