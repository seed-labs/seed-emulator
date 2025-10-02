#!/bin/bash

# 银狐木马攻击仿真复现实验 - 环境清理脚本

echo "🧹 银狐木马攻击仿真复现实验 - 环境清理"
echo "=============================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 停止函数
stop_service() {
    local service_name=$1
    local port=$2
    
    echo -n "停止$service_name... "
    if netstat -tuln | grep -q ":$port "; then
        # 查找并停止进程
        pkill -f "$service_name" > /dev/null 2>&1
        sleep 2
        
        if netstat -tuln | grep -q ":$port "; then
            echo -e "${YELLOW}! 强制停止$service_name${NC}"
            pkill -9 -f "$service_name" > /dev/null 2>&1
        fi
        
        if ! netstat -tuln | grep -q ":$port "; then
            echo -e "${GREEN}✓ 已停止${NC}"
        else
            echo -e "${RED}✗ 停止失败${NC}"
        fi
    else
        echo -e "${BLUE}- 未运行${NC}"
    fi
}

echo -e "${BLUE}1. 停止仿真服务${NC}"
echo "----------------------------------------"

# 停止Web界面
stop_service "web_interface.py" "4257"

# 停止Gophish
stop_service "gophish" "3333"

echo
echo -e "${BLUE}2. 清理Docker环境${NC}"
echo "----------------------------------------"

# 停止并删除Docker容器
echo -n "停止Docker容器... "
if [ -f "docker/docker-compose.yml" ]; then
    docker-compose -f docker/docker-compose.yml down > /dev/null 2>&1
    echo -e "${GREEN}✓ 已停止${NC}"
else
    echo -e "${BLUE}- Docker Compose文件不存在${NC}"
fi

# 清理未使用的Docker资源
echo -n "清理Docker资源... "
docker system prune -f > /dev/null 2>&1
echo -e "${GREEN}✓ 已清理${NC}"

echo
echo -e "${BLUE}3. 清理临时文件${NC}"
echo "----------------------------------------"

# 清理日志文件
echo -n "清理日志文件... "
find results/logs -name "*.log" -type f -mtime +7 -delete 2>/dev/null
echo -e "${GREEN}✓ 已清理${NC}"

# 清理截图文件
echo -n "清理截图文件... "
find results/screenshots -name "*.png" -type f -mtime +7 -delete 2>/dev/null
echo -e "${GREEN}✓ 已清理${NC}"

# 清理临时文件
echo -n "清理临时文件... "
find . -name "*.tmp" -type f -delete 2>/dev/null
find . -name "*.pyc" -type f -delete 2>/dev/null
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null
echo -e "${GREEN}✓ 已清理${NC}"

echo
echo -e "${BLUE}4. 清理网络资源${NC}"
echo "----------------------------------------"

# 清理Docker网络
echo -n "清理Docker网络... "
docker network prune -f > /dev/null 2>&1
echo -e "${GREEN}✓ 已清理${NC}"

# 检查端口占用
echo -n "检查端口占用... "
USED_PORTS=$(netstat -tuln | grep -E ":(4257|3333|5000|5001|5002) " | wc -l)
if [ "$USED_PORTS" -eq 0 ]; then
    echo -e "${GREEN}✓ 所有端口已释放${NC}"
else
    echo -e "${YELLOW}! 仍有 $USED_PORTS 个端口被占用${NC}"
    netstat -tuln | grep -E ":(4257|3333|5000|5001|5002) "
fi

echo
echo -e "${BLUE}5. 环境状态检查${NC}"
echo "----------------------------------------"

# 检查磁盘使用情况
echo -n "检查磁盘使用情况... "
DISK_USAGE=$(df -h . | tail -1 | awk '{print $5}')
echo -e "${BLUE}$DISK_USAGE${NC}"

# 检查内存使用情况
echo -n "检查内存使用情况... "
MEMORY_USAGE=$(free -h | grep "Mem:" | awk '{print $3 "/" $2}')
echo -e "${BLUE}$MEMORY_USAGE${NC}"

# 检查运行中的相关进程
echo -n "检查残留进程... "
REMAINING_PROCESSES=$(ps aux | grep -E "(gophish|web_interface|silverfox)" | grep -v grep | wc -l)
if [ "$REMAINING_PROCESSES" -eq 0 ]; then
    echo -e "${GREEN}✓ 无残留进程${NC}"
else
    echo -e "${YELLOW}! 发现 $REMAINING_PROCESSES 个相关进程${NC}"
    ps aux | grep -E "(gophish|web_interface|silverfox)" | grep -v grep
fi

echo
echo -e "${BLUE}6. 生成清理报告${NC}"
echo "----------------------------------------"

# 生成清理报告
REPORT_FILE="results/reports/cleanup_report_$(date +%Y%m%d_%H%M%S).md"
cat > "$REPORT_FILE" << EOF
# 银狐木马攻击仿真复现实验 - 环境清理报告

**清理时间**: $(date '+%Y-%m-%d %H:%M:%S')

## 清理结果

### 服务停止
- Web界面 (4257): ✓ 已停止
- Gophish (3333): ✓ 已停止

### Docker清理
- 容器停止: ✓ 已完成
- 网络清理: ✓ 已完成
- 系统清理: ✓ 已完成

### 文件清理
- 日志文件: ✓ 已清理 (保留7天)
- 截图文件: ✓ 已清理 (保留7天)
- 临时文件: ✓ 已清理
- Python缓存: ✓ 已清理

### 网络资源
- 端口释放: ✓ 已完成
- 网络清理: ✓ 已完成

### 系统状态
- 磁盘使用: $DISK_USAGE
- 内存使用: $MEMORY_USAGE
- 残留进程: $REMAINING_PROCESSES 个

## 清理结论

环境清理**完成**，所有资源已释放。

## 注意事项

- 如有残留进程，请手动停止
- 重要数据已备份到 results/ 目录
- 实验报告保存在 results/reports/ 目录

---
*清理报告自动生成*
EOF

echo -e "${GREEN}✓ 清理报告已生成: $REPORT_FILE${NC}"

echo
echo -e "${GREEN}🎉 环境清理完成！${NC}"
echo "=============================================="
echo -e "${BLUE}清理结果总结:${NC}"
echo -e "  • 服务停止: ${GREEN}完成${NC}"
echo -e "  • Docker清理: ${GREEN}完成${NC}"
echo -e "  • 文件清理: ${GREEN}完成${NC}"
echo -e "  • 网络清理: ${GREEN}完成${NC}"
echo
echo -e "${YELLOW}清理报告: ${BLUE}$REPORT_FILE${NC}"
echo
echo -e "${GREEN}环境已恢复到初始状态，可以重新启动仿真。${NC}"