#!/bin/bash

# 57号实验停止脚本
echo "🛑 停止 57 号综合安全评估实验"
echo "================================"

echo "🔴 停止攻防工具容器..."
docker rm -f gophish pentest-agent openbas 2>/dev/null || true

echo "📧 保留29号邮件系统容器 (如需停止请手动执行)"
echo "   cd ../29-email-system/output && docker-compose down"

echo ""
echo "✅ 57号实验环境已停止"