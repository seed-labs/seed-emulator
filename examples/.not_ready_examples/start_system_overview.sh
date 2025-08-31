#!/bin/bash

# SEED邮件系统综合总览启动脚本
# 端口: 4257

echo "🌟 SEED邮件系统综合总览启动脚本"
echo "=================================="
echo ""

# 检查Python环境
echo "🐍 检查Python环境..."
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到Python3"
    echo "💡 请安装Python3: sudo apt install python3"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d. -f1-2)
echo "✅ Python版本: $PYTHON_VERSION"

# 检查必要的依赖
echo ""
echo "📦 检查Python依赖..."

# 检查Flask
if ! python3 -c "import flask" 2>/dev/null; then
    echo "❌ 缺少Flask，正在安装..."
    pip3 install flask || {
        echo "❌ Flask安装失败"
        echo "💡 请手动安装: pip3 install flask"
        exit 1
    }
fi
echo "✅ Flask 已安装"

# 检查其他依赖
REQUIRED_PACKAGES=("pathlib" "subprocess" "json" "time")
for package in "${REQUIRED_PACKAGES[@]}"; do
    if ! python3 -c "import $package" 2>/dev/null; then
        echo "⚠️  缺少标准库包: $package"
    fi
done

# 检查端口占用
echo ""
echo "🔌 检查端口占用..."
if lsof -ti :4257 >/dev/null 2>&1; then
    echo "⚠️  端口4257已被占用，正在清理..."
    kill -9 $(lsof -ti :4257) 2>/dev/null || true
    sleep 2
fi
echo "✅ 端口4257可用"

# 检查应用文件
echo ""
echo "📁 检查应用文件..."
if [ ! -f "system_overview_app.py" ]; then
    echo "❌ 未找到 system_overview_app.py"
    exit 1
fi

if [ ! -d "templates" ]; then
    echo "❌ 未找到 templates 目录"
    mkdir -p templates
fi

if [ ! -f "templates/system_overview.html" ]; then
    echo "❌ 未找到 system_overview.html 模板"
    exit 1
fi

echo "✅ 应用文件完整"

# 显示启动信息
echo ""
echo "🚀 启动信息"
echo "============"
echo "🌐 访问地址: http://localhost:4257"
echo "📊 功能特性:"
echo "  • 实时项目状态监控 (29/29-1/30/31)"
echo "  • 一键项目启动/停止/测试"
echo "  • 代码结构可视化浏览"
echo "  • 技术文档集成查看"
echo "  • 实践指南和最佳实践"
echo "  • 自动化测试执行"
echo "  • 问题诊断和故障排查"
echo ""
echo "🎯 项目概览:"
echo "  📧 29基础版   - 端口5000 (Docker Mailserver)"
echo "  🌐 29-1真实版 - 端口5001 (多提供商仿真)"
echo "  🤖 30 AI版    - 端口5002 (智能钓鱼系统)"
echo "  🚀 31高级版   - 端口5003 (OpenAI APT系统)"
echo ""
echo "💡 操作指南:"
echo "  1. 使用浏览器访问 http://localhost:4257"
echo "  2. 查看各项目的实时状态"
echo "  3. 使用快速操作按钮管理项目"
echo "  4. 浏览技术文档和代码结构"
echo "  5. 运行自动化测试验证功能"
echo ""
echo "⚠️  安全提醒:"
echo "  • 仅限教育和研究用途"
echo "  • 在隔离环境中运行测试"
echo "  • 定期清理测试数据"
echo ""

# 询问用户确认
read -p "是否开始启动系统总览？(y/N): " confirm
if [[ ! $confirm =~ ^[Yy]$ ]]; then
    echo "❌ 操作已取消"
    exit 0
fi

echo ""
echo "🔄 正在启动SEED邮件系统综合总览..."
echo "====================================="
echo ""

# 启动应用
python3 system_overview_app.py

# 脚本执行完成
echo ""
echo "✅ 系统总览已停止"
echo "💡 再次启动请运行: ./start_system_overview.sh"
echo "🌟 访问地址: http://localhost:4257"
