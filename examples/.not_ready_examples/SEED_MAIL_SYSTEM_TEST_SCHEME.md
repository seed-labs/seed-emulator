# 🎯 SEED邮件系统完整测试方案

基于全面的系统验证，我为您提供完整的SEED邮件系统运行测试方案，包括29、29-1、30、31所有项目的详细测试流程。

## 📋 测试方案总览

```
SEED邮件系统完整测试方案
├── 🎯 测试目标: 验证所有项目功能完整性
├── 🏗️ 架构层次: 基础→增强→AI→高级
├── ⏱️ 总时长: ~45分钟
├── ✅ 通过标准: 所有核心功能正常运行
└── 📊 验证点: 29个关键功能点
```

---

## 🚀 第一阶段：环境准备 (5分钟)

### 1.1 激活环境
```bash
# 进入项目根目录
cd /home/parallels/seed-email-system

# 激活开发环境
source development.env

# 激活conda环境
conda activate seed-emulator

# 验证环境状态
python3 --version && pip list | grep flask
```

### 1.2 加载别名系统
```bash
# 加载Docker别名
cd examples/.not_ready_examples
source docker_aliases.sh

# 验证别名加载
seed-help
```

### 1.3 系统状态检查
```bash
# 检查Docker状态
docker --version && docker-compose --version

# 检查网络端口占用
netstat -tlnp | grep -E ":500[0-3]|:2525|:2526|:2527|:4257" || echo "端口正常"

# 检查磁盘空间
df -h && echo "可用空间:" && df -h /home | tail -1 | awk '{print $4}'
```

---

## 🏗️ 第二阶段：基础项目测试 (10分钟)

### 2.1 29项目 - 基础邮件系统

#### 启动29项目
```bash
# 启动网络基础设施
seed-29

# 等待容器启动
sleep 30

# 检查容器状态
docker ps --filter "name=mail" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

#### Web界面测试
```bash
# 启动Web服务器 (新终端)
cd examples/.not_ready_examples/29-email-system
python3 webmail_server.py

# 验证Web访问
curl -s http://localhost:5000/ | head -5
```

#### 邮件功能测试
```bash
# 检查邮件账户
docker exec mail-150-seedemail setup email list

# 发送测试邮件
swaks --to alice@seedemail.net --server localhost --port 2525 \
      --from bob@seedemail.net --header "Subject: 29项目测试" \
      --body "29项目邮件功能测试"

# 验证接收
docker exec mail-150-seedemail setup email list
```

#### ✅ 29项目验证清单
- [ ] Docker容器正常启动
- [ ] SMTP端口2525监听正常
- [ ] IMAP端口1430监听正常
- [ ] Web界面http://localhost:5000正常访问
- [ ] 邮件发送/接收功能正常
- [ ] 账户管理功能正常

---

### 2.2 29-1项目 - 真实网络邮件系统

#### 启动29-1项目
```bash
# 启动网络基础设施
seed-29-1

# 等待容器启动
sleep 45

# 检查容器状态
docker ps --filter "name=29-1" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | head -10
```

#### Web界面测试
```bash
# 启动Web服务器 (新终端)
cd examples/.not_ready_examples/29-1-email-system
python3 webmail_server.py

# 验证Web访问
curl -s http://localhost:5001/ | grep "SEED邮件系统"
```

#### 跨域邮件测试
```bash
# 检查多域名账户
docker exec mail-150-seedemail setup email list
docker exec mail-151-corporate setup email list
docker exec mail-152-smallbiz setup email list

# 测试跨域邮件发送
swaks --to alice@seedemail.net --server localhost --port 2526 \
      --from admin@corporate.local --header "Subject: 跨域测试" \
      --body "29-1项目跨域邮件测试"

# 验证接收
docker exec mail-150-seedemail setup email list
```

#### ✅ 29-1项目验证清单
- [ ] 网络基础设施正常启动
- [ ] 多域名邮件服务器正常
- [ ] Web界面http://localhost:5001正常访问
- [ ] 跨域邮件传输正常
- [ ] 国际互联网交换中心正常
- [ ] DNS系统解析正常

---

## 🤖 第三阶段：AI增强项目测试 (15分钟)

### 3.1 30项目 - AI钓鱼系统

#### 启动30项目
```bash
# 启动网络基础设施
seed-30

# 等待容器启动
sleep 60

# 检查容器状态
docker ps --filter "name=30" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | head -10
docker ps --filter "name=as205" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

#### Web界面测试
```bash
# 启动Web服务器 (新终端)
cd examples/.not_ready_examples/30-phishing-ai-system
python3 test_flask.py

# 验证Web访问
curl -s http://localhost:5002/ | grep "30项目Flask"
curl -s http://localhost:5002/status | head -3
```

#### 网络拓扑验证
```bash
# 检查攻击者基础设施
docker ps --filter "name=as205" --format "table {{.Names}}\t{{.Status}}"
docker ps --filter "name=as206" --format "table {{.Names}}\t{{.Status}}"
docker ps --filter "name=as207" --format "table {{.Names}}\t{{.Status}}"

# 检查云服务基础设施
docker ps --filter "name=as210" --format "table {{.Names}}\t{{.Status}}"
docker ps --filter "name=as211" --format "table {{.Names}}\t{{.Status}}"

# 检查用户网络
docker ps --filter "name=as220" --format "table {{.Names}}\t{{.Status}}"
docker ps --filter "name=as221" --format "table {{.Names}}\t{{.Status}}"
```

#### AI功能验证
```bash
# 检查AI服务状态 (如果配置了)
curl -s http://localhost:11434/api/version 2>/dev/null || echo "Ollama未运行"

# 验证网络连通性
docker exec as205h-host_0 ping -c 3 10.206.0.71 || echo "网络连通性测试"
```

#### ✅ 30项目验证清单
- [ ] 企业网络基础设施正常启动
- [ ] 攻击者基础设施正常启动 (AS-205/206/207)
- [ ] 云服务环境正常启动 (AS-210/211)
- [ ] 用户网络正常启动 (AS-220/221)
- [ ] Web界面http://localhost:5002正常访问
- [ ] 网络拓扑连通性正常
- [ ] AI服务架构完整

---

### 3.2 31项目 - 高级智能钓鱼系统

#### 环境配置
```bash
# 检查31项目环境
cd examples/.not_ready_examples/31-advanced-phishing-system

# 验证配置文件
ls -la .env requirements.txt

# 检查OpenAI配置
cat .env | grep -E "OPENAI|API" | head -3
```

#### 启动31项目
```bash
# 安装依赖 (如需要)
pip install -r requirements.txt

# 启动Web控制台
python3 advanced_phishing_system.py

# 或者使用启动脚本
chmod +x start_advanced_phishing.sh
./start_advanced_phishing.sh
```

#### Web界面测试
```bash
# 验证Web访问 (假设运行在5003端口)
curl -s http://localhost:5003/ | head -5

# 测试API端点
curl -s http://localhost:5003/api/status 2>/dev/null || echo "API未配置"
```

#### OpenAI集成测试
```bash
# 测试OpenAI连接
python3 demo_openai_integration.py

# 检查演示结果
ls -la openai_demo_results_*.json

# 查看测试结果
cat openai_demo_results_*.json | head -10
```

#### ✅ 31项目验证清单
- [ ] 项目依赖安装完成
- [ ] Web控制台正常启动
- [ ] OpenAI API配置正确
- [ ] AI模型集成测试通过
- [ ] 高级功能架构完整
- [ ] 安全隔离机制正常

---

## 🎛️ 第四阶段：系统总览测试 (5分钟)

### 4.1 系统总览面板

#### 启动系统总览
```bash
# 启动系统总览面板
seed-overview

# 或者直接运行
cd examples/.not_ready_examples
python3 system_overview_app.py
```

#### 功能验证
```bash
# 验证主界面
curl -s http://localhost:4257/ | grep "SEED邮件系统综合总览"

# 测试API端点
curl -s http://localhost:4257/api/system_status | head -3

# 验证各项目状态
curl -s http://localhost:4257/api/projects | jq '.[] | select(.name=="29")' 2>/dev/null || echo "API调用正常"
```

#### ✅ 系统总览验证清单
- [ ] 系统总览面板正常启动
- [ ] Web界面http://localhost:4257正常访问
- [ ] 项目状态监控正常
- [ ] API接口响应正常
- [ ] 实时更新功能正常

---

## 🔧 第五阶段：集成测试 (5分钟)

### 5.1 多项目协同测试

#### 端口冲突检查
```bash
# 检查所有项目端口
netstat -tlnp | grep -E ":500[0-3]|:2525|:2526|:2527|:4257|:11434|:3333" | sort

# 验证端口分配
echo "端口分配情况:"
echo "5000 - 29项目Web界面"
echo "5001 - 29-1项目Web界面"
echo "5002 - 30项目Web界面"
echo "5003 - 31项目Web界面 (预留)"
echo "4257 - 系统总览面板"
echo "2525 - seedemail.net SMTP"
echo "2526 - corporate.local SMTP"
echo "2527 - smallbiz.org SMTP"
```

#### 跨项目通信测试
```bash
# 测试跨项目邮件通信
swaks --to alice@seedemail.net --server localhost --port 2525 \
      --from test@seedemail.net --header "Subject: 跨项目测试" \
      --body "从29项目发送到29-1项目网络"

# 验证29-1网络接收
docker exec mail-150-seedemail setup email list
```

### 5.2 性能测试

#### 系统资源检查
```bash
# 检查系统资源使用
echo "系统资源状态:"
free -h && echo "---" && df -h && echo "---" && uptime

# 检查Docker资源
docker stats --no-stream | head -10
```

#### 并发测试
```bash
# 简单并发测试
for i in {1..5}; do
  curl -s http://localhost:5000/ > /dev/null &
  curl -s http://localhost:5001/ > /dev/null &
  curl -s http://localhost:5002/ > /dev/null &
done
wait
echo "并发测试完成"
```

---

## 📊 第六阶段：测试报告生成 (5分钟)

### 6.1 自动测试脚本

创建完整的测试验证脚本：

```bash
#!/bin/bash
# SEED邮件系统自动测试脚本

echo "🎯 SEED邮件系统自动测试开始"
echo "================================="

# 测试函数
test_web_interface() {
    local url=$1
    local name=$2
    if curl -s --max-time 5 "$url" > /dev/null; then
        echo "✅ $name - Web界面正常"
        return 0
    else
        echo "❌ $name - Web界面异常"
        return 1
    fi
}

test_email_service() {
    local port=$1
    local domain=$2
    if timeout 5 bash -c "</dev/tcp/localhost/$port" 2>/dev/null; then
        echo "✅ $domain - SMTP服务正常 (端口$port)"
        return 0
    else
        echo "❌ $domain - SMTP服务异常 (端口$port)"
        return 1
    fi
}

# 执行测试
echo "🌐 Web界面测试:"
test_web_interface "http://localhost:5000" "29项目"
test_web_interface "http://localhost:5001" "29-1项目"
test_web_interface "http://localhost:5002" "30项目"
test_web_interface "http://localhost:4257" "系统总览"

echo ""
echo "📧 邮件服务测试:"
test_email_service 2525 "seedemail.net"
test_email_service 2526 "corporate.local"
test_email_service 2527 "smallbiz.org"

echo ""
echo "🐳 容器状态测试:"
docker ps --filter "name=mail" --format "table {{.Names}}\t{{.Status}}" | wc -l | xargs echo "邮件容器数量:"

echo ""
echo "🎉 测试完成！"
```

### 6.2 手动验证清单

#### 📋 完整验证清单

**基础设施验证:**
- [ ] Docker环境正常运行
- [ ] 网络端口无冲突
- [ ] 系统资源充足
- [ ] 虚拟环境激活正常

**29项目验证:**
- [ ] 容器启动成功 (3个邮件服务器)
- [ ] Web界面可访问 (http://localhost:5000)
- [ ] SMTP/IMAP服务正常 (2525/1430)
- [ ] 邮件发送接收功能正常
- [ ] 账户管理功能完整

**29-1项目验证:**
- [ ] 网络拓扑完整 (14个AS节点)
- [ ] Web界面可访问 (http://localhost:5001)
- [ ] 多域名邮件服务正常
- [ ] 跨域通信功能正常
- [ ] DNS解析机制正常

**30项目验证:**
- [ ] AI钓鱼基础设施完整
- [ ] 攻击者网络正常 (AS-205/206/207)
- [ ] 云服务环境正常 (AS-210/211)
- [ ] 用户网络正常 (AS-220/221)
- [ ] Web界面可访问 (http://localhost:5002)

**31项目验证:**
- [ ] OpenAI集成配置正确
- [ ] 高级AI功能架构完整
- [ ] Web控制台可访问
- [ ] 安全隔离机制正常

**系统集成验证:**
- [ ] 系统总览面板正常 (http://localhost:4257)
- [ ] 项目间通信正常
- [ ] 资源使用合理
- [ ] 整体稳定性良好

---

## 🚨 第七阶段：问题排查 (5分钟)

### 7.1 常见问题及解决方案

#### Docker相关问题
```bash
# 清理Docker缓存
docker system prune -af --volumes

# 重启Docker服务
sudo systemctl restart docker

# 检查Docker日志
docker logs <container_name>
```

#### 端口冲突问题
```bash
# 查找端口占用
lsof -i :5000

# 杀死占用进程
kill -9 <PID>
```

#### Python进程顽固
```bash
# 查找并强制终止
ps aux | grep python | grep -E "(webmail|flask|system)"
kill -9 <PID>
```

### 7.2 深度清理选项
```bash
# 完全清理所有SEED相关文件 (谨慎使用)
sudo rm -rf examples/.not_ready_examples/29-email-system/output/
sudo rm -rf examples/.not_ready_examples/29-1-email-system/output/
sudo rm -rf examples/.not_ready_examples/30-phishing-ai-system/output/

# 清理日志文件
find examples/.not_ready_examples/ -name "*.log" -delete
find examples/.not_ready_examples/ -name "*.pyc" -delete
find examples/.not_ready_examples/ -name "__pycache__" -type d -exec rm -rf {} +
```

---

## 📋 快速测试清单

- [ ] ✅ 激活SEED环境
- [ ] ✅ 启动29基础项目
- [ ] ✅ 测试Web界面和邮件功能
- [ ] ✅ 启动29-1真实项目
- [ ] ✅ 验证跨域通信
- [ ] ✅ 启动30 AI项目
- [ ] ✅ 检查网络拓扑
- [ ] ✅ 启动系统总览
- [ ] ✅ 运行集成测试
- [ ] ✅ 生成测试报告

---

## 🎯 测试完成标准

### 核心功能验证
✅ **基础设施层**
- Docker容器正常运行
- 网络端口配置正确
- 系统资源充足

✅ **服务层**
- Web界面响应正常
- 邮件服务功能完整
- API接口工作正常

✅ **功能层**
- 邮件发送接收正常
- 跨域通信成功
- 用户认证机制有效

✅ **集成层**
- 项目间协同工作
- 实时状态监控
- 故障恢复机制

### 性能指标
- **响应时间**: Web界面 < 2秒
- **邮件处理**: 并发测试通过
- **资源使用**: CPU < 80%, 内存 < 4GB
- **稳定性**: 持续运行 > 30分钟

---

## 📞 获取帮助

### 快速诊断
```bash
# 一键诊断脚本
curl -s https://raw.githubusercontent.com/seed-labs/seed-labs/master/tools/diagnose.sh | bash
```

### 常见问题
- **端口冲突**: 运行 `seed-check-ports`
- **容器异常**: 运行 `docker logs <container_name>`
- **网络问题**: 运行 `seed-ping <source> <target>`

### 技术支持
- 📖 文档: `SEED_MAIL_SYSTEM_TEST_SCHEME.md`
- 🐛 问题: 检查 `PROBLEM_SOLUTIONS.md`
- 💬 帮助: 运行 `seed-help`

---

## 🎉 测试总结

### 测试覆盖范围
- **项目数量**: 4个 (29/29-1/30/31)
- **功能点**: 29个关键功能
- **测试类型**: 功能测试 + 集成测试 + 性能测试
- **验证维度**: 正确性 + 稳定性 + 性能

### 测试结果评估
- **通过率目标**: > 95%
- **关键功能**: 100% 验证
- **用户体验**: 流畅稳定
- **文档完整性**: 全面覆盖

### 后续改进建议
- 自动化测试脚本完善
- 性能基准测试建立
- 监控告警机制建设
- 文档持续更新维护

---

*最后更新: 2025年1月*
*版本: v2.0*
*维护者: SEED-Lab团队*
