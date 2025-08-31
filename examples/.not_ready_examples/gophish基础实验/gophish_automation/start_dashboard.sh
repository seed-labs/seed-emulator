#!/bin/bash

# Gophish AI自动化管理表盘启动脚本

echo "🎯 启动Gophish AI自动化管理表盘"
echo "=================================="

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 检查conda环境
echo "🔍 检查conda环境..."
if conda list | grep -q "gophish\|openai\|flask"; then
    echo "✅ conda环境已配置"
else
    echo "⚠️ conda环境可能未正确配置"
    echo "请运行: conda activate gophish-test"
fi

# 检查Gophish是否运行
echo "🔍 检查Gophish状态..."
if curl -s -k https://localhost:3333 > /dev/null 2>&1; then
    echo "✅ Gophish正在运行"
else
    echo "⚠️ Gophish未运行，请先启动:"
    echo "   cd .. && ./gophish"
fi

# 检查其他服务
echo "🔍 检查支持服务..."

services=(
    "5888:损失评估仪表板"
    "5001:XSS服务器"
    "5002:SQL注入服务器"
    "5003:Heartbleed服务器"
)

for service in "${services[@]}"; do
    port=$(echo $service | cut -d: -f1)
    name=$(echo $service | cut -d: -f2)
    
    if curl -s http://localhost:$port > /dev/null 2>&1; then
        echo "  ✅ $name (:$port)"
    else
        echo "  ❌ $name (:$port) - 未运行"
    fi
done

echo ""
echo "🚀 启动管理表盘..."
echo "📍 访问地址: http://localhost:6789"
echo ""
echo "🔧 功能说明:"
echo "  • 📊 系统状态监控"
echo "  • 📁 文件清单管理"
echo "  • 🤖 AI内容生成"
echo "  • 📧 批量邮件发送"
echo "  • 💥 漏洞利用可视化"
echo "  • 🎯 推荐测试目标: zzw4257@gmail.com, 3230106267@zju.edu.cn, 809050685@qq.com"
echo ""
echo "按 Ctrl+C 停止服务"
echo "=================================="

# 启动Flask应用
python dashboard_app.py
