#!/bin/bash

echo "🔧====================================================================🔧"
echo "                SEED邮件系统 Docker别名设置工具"
echo "🔧====================================================================🔧"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ALIASES_FILE="$SCRIPT_DIR/docker_aliases.sh"

# 检查别名文件是否存在
if [ ! -f "$ALIASES_FILE" ]; then
    echo "❌ 找不到Docker别名文件: $ALIASES_FILE"
    exit 1
fi

echo "📋 Docker别名设置选项:"
echo "1. 临时加载别名 (仅当前会话有效)"
echo "2. 永久添加到 ~/.bashrc (所有新会话都有效)"
echo "3. 查看所有可用别名"
echo "4. 测试别名功能"
echo ""

read -p "请选择 [1-4]: " choice

case $choice in
    1)
        echo "⏳ 正在临时加载Docker别名..."
        source "$ALIASES_FILE"
        echo ""
        echo "✅ 别名已加载到当前会话！"
        echo "💡 您现在可以使用以下命令:"
        echo "   - dcbuild, dcup, dcdown (Docker Compose)"
        echo "   - dockps, docksh (Docker 容器管理)"
        echo "   - seed-29, seed-29-1, seed-30 (快速启动项目)"
        echo "   - seed-help (查看所有命令)"
        echo ""
        echo "⚠️  注意: 这些别名只在当前终端会话中有效"
        ;;
    2)
        echo "⏳ 正在添加别名到 ~/.bashrc..."
        
        # 检查是否已经添加过
        if grep -q "docker_aliases.sh" ~/.bashrc 2>/dev/null; then
            echo "⚠️  别名似乎已经添加到 ~/.bashrc 中"
            read -p "是否要重新添加? [y/N]: " confirm
            if [[ ! $confirm =~ ^[Yy]$ ]]; then
                echo "❌ 操作已取消"
                exit 0
            fi
            
            # 移除旧的条目
            sed -i '/# SEED邮件系统Docker别名/,/^$/d' ~/.bashrc
        fi
        
        # 添加新的别名加载代码
        cat >> ~/.bashrc << EOF

# SEED邮件系统Docker别名 - 自动生成 $(date)
if [ -f "$ALIASES_FILE" ]; then
    source "$ALIASES_FILE"
fi

EOF
        
        echo "✅ 别名已添加到 ~/.bashrc！"
        echo "💡 请运行以下命令之一来激活:"
        echo "   source ~/.bashrc"
        echo "   或重新打开终端"
        echo ""
        echo "🎯 激活后，您可以使用 'seed-help' 查看所有命令"
        ;;
    3)
        echo "📋 查看所有可用的SEED Docker别名..."
        echo ""
        source "$ALIASES_FILE"
        seed-help
        ;;
    4)
        echo "🧪 测试别名功能..."
        echo ""
        
        # 临时加载别名
        source "$ALIASES_FILE"
        
        echo "测试基本别名:"
        echo "  dcbuild → $(type dcbuild 2>/dev/null | head -1)"
        echo "  dcup → $(type dcup 2>/dev/null | head -1)"
        echo "  dockps → $(type dockps 2>/dev/null | head -1)"
        echo ""
        
        echo "测试SEED专用别名:"
        echo "  seed-status → $(type seed-status 2>/dev/null | head -1)"
        echo "  seed-help → $(type seed-help 2>/dev/null | head -1)"
        echo ""
        
        echo "✅ 别名功能测试完成！"
        echo "💡 运行 'seed-help' 查看完整命令列表"
        ;;
    *)
        echo "❌ 无效选择，请重新运行脚本"
        exit 1
        ;;
esac

echo ""
echo "🎉 Docker别名设置完成！"
echo ""

# 显示快速使用指南
cat << 'EOF'
🚀 快速使用指南:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📦 Docker Compose 快捷命令:
   dcbuild          # docker-compose build
   dcup             # docker-compose up
   dcupd            # docker-compose up -d (后台)
   dcdown           # docker-compose down
   dclogs           # docker-compose logs

🐳 Docker 容器管理:
   dockps           # 查看运行中的容器
   docksh <id>      # 进入容器Shell (只需输入ID前几位)

🎯 SEED 项目快速启动:
   seed-29          # 启动29基础版 (带Web界面)
   seed-29-1        # 启动29-1真实版
   seed-30          # 启动30 AI钓鱼版
   seed-stop        # 停止所有项目

📊 系统监控:
   seed-status      # 检查系统状态
   seed-ai-status   # 检查AI服务状态

📧 邮件测试:
   seed-mail-send <发件人> <收件人> <主题> <内容>
   seed-ping <容器> <目标IP>

💡 获取帮助:
   seed-help        # 查看完整命令列表

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EOF

echo ""
echo "🎓 现在您可以更高效地管理SEED邮件系统了！"
