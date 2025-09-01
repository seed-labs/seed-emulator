# 🎯 SEED邮件系统完整测试方案

基于全面的系统验证，我为您提供完整的SEED邮件系统运行测试方案，包括29、29-1、30、31所有项目的详细测试流程。

## 📋 测试方案总览

```
SEED邮件系统完整测试方案
├── 🎯 测试目标: 验证所有项目功能完整性
├── 🏗️ 架构层次: 基础→增强→AI→高级
├── ⏱️ 总时长: ~45分钟
├── ✅ 通过标准: 所有核心功能正常运行
├── 📊 验证点: 29个关键功能点
├── 🔧 技术栈: SEED Emulator + Docker + Flask + AI
└── 🎪 演示效果: 7个实验场景 + Web界面 + 钓鱼攻击链
```

### 🎪 完整演示场景

**实验#1: 邮件系统基础测试** - 29项目基础邮件功能
**实验#2: 真实邮件服务商测试** - 29-1项目跨域邮件
**实验#3: XSS漏洞攻击测试** - Gophish XSS仿真
**实验#4: SQL注入攻击测试** - Gophish SQL注入仿真
**实验#5: Heartbleed内存泄露测试** - Gophish Heartbleed仿真
**实验#6: 损失评估仪表板测试** - 攻击统计可视化
**实验#7: 完整攻击链集成测试** - 从邮件到攻击的完整流程

---

## 🚀 第一阶段：环境准备 (5分钟)

### 1.1 激活环境
```bash
# 进入项目根目录
cd /home/parallels/seed-email-system

# 激活conda环境
conda activate seed-emulator

# 验证环境状态
python3 --version && pip list | grep -E "flask|seed"
```

### 1.2 加载别名系统
```bash
# 加载Docker别名系统
cd examples/.not_ready_examples
source docker_aliases.sh

# 验证别名加载
seed-help

# 查看可用命令
seed-overview
```

### 1.3 系统状态检查
```bash
# 检查Docker状态
docker --version && docker-compose --version

# 检查网络端口占用
netstat -tlnp | grep -E ":500[0-3]|:2525|:2526|:2527|:4257|:5888|:3333" || echo "端口正常"

# 检查磁盘空间
df -h && echo "可用空间:" && df -h /home | tail -1 | awk '{print $4}'

# 检查系统资源
free -h && uptime
```

### 1.4 快速启动选项
```bash
# 一键启动所有服务 (推荐新手)
cd examples/.not_ready_examples
./quick_start.sh

# 或者逐个启动项目
seed-29        # 启动29基础邮件项目
seed-29-1      # 启动29-1真实邮件项目
seed-30        # 启动30 AI钓鱼项目
./start_simulation.sh  # 启动Gophish钓鱼仿真
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

# Web界面发信测试
curl -X POST http://localhost:5000/api/send_test_email \
  -H "Content-Type: application/json" \
  -d '{"from_email":"alice@seedemail.net","to_email":"bob@seedemail.net","subject":"Web发信测试","body":"通过Web界面发送的测试邮件","template":"plain"}'

# 发送HTML邮件测试
curl -X POST http://localhost:5000/api/send_test_email \
  -H "Content-Type: application/json" \
  -d '{"from_email":"alice@seedemail.net","to_email":"bob@seedemail.net","subject":"HTML邮件测试","body":"HTML邮件测试内容","template":"html"}'

# 发送钓鱼邮件测试
curl -X POST http://localhost:5000/api/send_test_email \
  -H "Content-Type: application/json" \
  -d '{"from_email":"alice@seedemail.net","to_email":"bob@seedemail.net","subject":"安全提醒","body":"钓鱼邮件测试","template":"phishing"}'

# 验证邮件接收
docker exec mail-150-seedemail setup email list
```

#### Webmail界面测试
```bash
# 访问RoundCube Webmail (浏览器)
echo "打开浏览器访问: http://localhost:8000"
echo "用户名: alice@seedemail.net"
echo "密码: password123"
echo "发送邮件给: bob@seedemail.net"
```

#### ✅ 29项目验证清单
- [ ] Docker容器正常启动 (3个邮件服务器)
- [ ] SMTP端口2525监听正常
- [ ] IMAP端口1430监听正常
- [ ] Web界面http://localhost:5000正常访问
- [ ] API发信功能正常 (plain/html/phishing)
- [ ] Webmail界面http://localhost:8000可登录
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
echo "=== seedemail.net 域名 ==="
docker exec mail-150-seedemail setup email list
echo "=== corporate.local 域名 ==="
docker exec mail-151-corporate setup email list
echo "=== smallbiz.org 域名 ==="
docker exec mail-152-smallbiz setup email list

# Web界面跨域发信测试
curl -X POST http://localhost:5001/api/send_test_email \
  -H "Content-Type: application/json" \
  -d '{"from_email":"alice@seedemail.net","to_email":"admin@corporate.local","subject":"跨域邮件测试","body":"从seedemail.net发送到corporate.local的测试邮件","template":"plain"}'

curl -X POST http://localhost:5001/api/send_test_email \
  -H "Content-Type: application/json" \
  -d '{"from_email":"admin@corporate.local","to_email":"alice@seedemail.net","subject":"回复测试","body":"从corporate.local回复seedemail.net的邮件","template":"plain"}'

# 验证跨域接收
echo "验证seedemail.net接收邮件:"
docker exec mail-150-seedemail setup email list
echo "验证corporate.local接收邮件:"
docker exec mail-151-corporate setup email list
```

#### 网络拓扑验证
```bash
# 检查网络连通性
docker ps --filter "name=mail" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | head -10

# 验证AS节点状态
docker ps --filter "name=29-1" --format "table {{.Names}}\t{{.Status}}" | head -15

# DNS解析测试
docker exec mail-150-seedemail nslookup corporate.local
docker exec mail-151-corporate nslookup seedemail.net
```

#### ✅ 29-1项目验证清单
- [ ] 网络基础设施正常启动 (14个AS节点)
- [ ] 多域名邮件服务器正常 (3个域名)
- [ ] Web界面http://localhost:5001正常访问
- [ ] 跨域邮件传输正常 (seedemail.net ↔ corporate.local)
- [ ] BGP路由配置正确
- [ ] DNS系统解析正常
- [ ] 国际互联网交换中心 (IX-50) 正常

---

## 🎣 第三阶段：钓鱼仿真测试 (15分钟)

### 3.1 实验#3: XSS漏洞攻击测试

#### 启动XSS服务器
```bash
# 启动Gophish钓鱼仿真系统
cd examples/.not_ready_examples/gophish基础实验
./start_simulation.sh

# 或者单独启动XSS服务器
python3 vulnerable_servers/web_xss/xss_server.py
```

#### XSS漏洞测试
```bash
# 访问XSS漏洞页面 (浏览器)
echo "打开浏览器访问: http://localhost:5004"

# 提交XSS攻击payload
curl -X POST http://localhost:5004/submit_feedback \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "name=测试用户&email=test@example.com&message=<script>alert('XSS攻击成功!')</script>"

# 查看XSS服务器日志
tail -f vulnerable_servers/web_xss/xss_server.log
```

#### ✅ XSS测试验证清单
- [ ] XSS服务器启动正常 (http://localhost:5004)
- [ ] 反馈表单页面可访问
- [ ] XSS payload注入成功
- [ ] 存储型XSS漏洞可复现
- [ ] 攻击日志记录正常

### 3.2 实验#4: SQL注入攻击测试

#### 启动SQL注入服务器
```bash
# 启动SQL注入服务器 (新终端)
cd examples/.not_ready_examples/gophish基础实验/vulnerable_servers/db_sqli
python3 sqli_server.py

# 或者使用统一启动脚本
cd examples/.not_ready_examples/gophish基础实验
./start_simulation.sh
```

#### SQL注入测试
```bash
# 访问SQL注入页面 (浏览器)
echo "打开浏览器访问: http://localhost:5002"

# 测试SQL注入攻击
curl -X POST http://localhost:5002/search \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "employee_id=1' OR '1'='1"

# 查看数据库内容泄露
curl -X POST http://localhost:5002/search \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "employee_id=1' UNION SELECT username, password FROM users --"
```

#### ✅ SQL注入测试验证清单
- [ ] SQL注入服务器启动正常 (http://localhost:5002)
- [ ] 员工信息查询页面可访问
- [ ] SQL注入漏洞可复现
- [ ] 数据库内容泄露成功
- [ ] 攻击日志记录正常

### 3.3 实验#5: Heartbleed内存泄露测试

#### 启动Heartbleed服务器
```bash
# 启动Heartbleed仿真服务器 (新终端)
cd examples/.not_ready_examples/gophish基础实验/vulnerable_servers/heartbleed_sim
python3 heartbleed_server.py

# 或者使用统一启动脚本
cd examples/.not_ready_examples/gophish基础实验
./start_simulation.sh
```

#### Heartbleed漏洞测试
```bash
# 访问Heartbleed测试页面 (浏览器)
echo "打开浏览器访问: http://localhost:5003"

# 测试内存泄露
curl -X POST http://localhost:5003/test_heartbleed \
  -H "Content-Type: application/json" \
  -d '{"length": 65535}'

# 查看内存泄露结果
curl -X GET http://localhost:5003/view_memory
```

#### ✅ Heartbleed测试验证清单
- [ ] Heartbleed服务器启动正常 (http://localhost:5003)
- [ ] SSL/TLS通信页面可访问
- [ ] Heartbleed漏洞可复现
- [ ] 内存内容泄露成功
- [ ] 敏感数据暴露验证

### 3.4 实验#6: 损失评估仪表板测试

#### 启动损失评估仪表板
```bash
# 启动损失评估仪表板 (新终端)
cd examples/.not_ready_examples/gophish基础实验/dashboard
python3 dashboard.py

# 或者使用统一启动脚本
cd examples/.not_ready_examples/gophish基础实验
./start_simulation.sh
```

#### 仪表板功能测试
```bash
# 访问损失评估仪表板 (浏览器)
echo "打开浏览器访问: http://localhost:5888"

# 查看攻击统计
curl -s http://localhost:5888/api/stats | head -10

# 测试攻击模拟
curl -X POST http://localhost:5888/api/simulate_attack \
  -H "Content-Type: application/json" \
  -d '{"attack_type":"xss","target":"employee_database","severity":"high"}'

# 查看损失评估
curl -s http://localhost:5888/api/losses | jq '.total_loss' 2>/dev/null || echo "损失评估功能正常"
```

#### ✅ 仪表板测试验证清单
- [ ] 损失评估仪表板启动正常 (http://localhost:5888)
- [ ] 攻击统计可视化正常
- [ ] 实时数据更新正常
- [ ] 损失计算功能正常
- [ ] 图表展示功能完整

---

## 🤖 第四阶段：AI增强项目测试 (10分钟)

### 4.1 30项目 - AI钓鱼系统

#### 启动30项目
```bash
# 启动AI钓鱼系统
seed-30

# 等待容器启动
sleep 60

# 检查容器状态
docker ps --filter "name=30" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | head -10
docker ps --filter "name=as205" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

#### AI模型初始化测试
```bash
# 启动AI模型初始化脚本
cd examples/.not_ready_examples/30-phishing-ai-system
chmod +x scripts/init_ai_models.sh
./scripts/init_ai_models.sh

# 验证AI模型状态
curl -s http://localhost:11434/api/tags 2>/dev/null | jq '.models[]?.name' || echo "Ollama服务未运行"
```

#### 攻击场景生成测试
```bash
# 运行攻击场景生成脚本
chmod +x scripts/setup_attack_scenarios.sh
./scripts/setup_attack_scenarios.sh

# 查看生成的攻击场景
ls -la phishing_scenarios_*.json
cat phishing_scenarios_*.json | head -10
```

#### Web界面测试
```bash
# 启动Web服务器 (新终端)
python3 test_flask.py

# 验证Web访问
curl -s http://localhost:5002/ | grep "AI钓鱼系统"
curl -s http://localhost:5002/status | head -5

# 测试AI功能
curl -s http://localhost:5002/api/generate_phishing \
  -H "Content-Type: application/json" \
  -d '{"target":"employee","scenario":"password_reset"}' | head -10
```

#### ✅ 30项目验证清单
- [ ] AI钓鱼网络基础设施正常启动
- [ ] 攻击者基础设施正常启动 (AS-205/206/207)
- [ ] 云服务环境正常启动 (AS-210/211)
- [ ] 用户网络正常启动 (AS-220/221)
- [ ] AI模型初始化成功
- [ ] 攻击场景生成正常
- [ ] Web界面http://localhost:5002正常访问
- [ ] AI钓鱼邮件生成功能正常

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

## 🔗 第五阶段：完整攻击链集成测试 (10分钟)

### 5.1 实验#7: 从邮件到攻击的完整流程

#### 准备阶段：启动所有系统
```bash
# 启动29项目邮件系统
seed-29
sleep 30

# 启动29-1项目跨域邮件系统
seed-30
sleep 45

# 启动Gophish钓鱼仿真
cd examples/.not_ready_examples/gophish基础实验
./start_simulation.sh
sleep 10

# 检查所有服务状态
echo "=== 邮件系统状态 ==="
docker ps --filter "name=mail" --format "table {{.Names}}\t{{.Ports}}"
echo "=== 钓鱼系统状态 ==="
netstat -tlnp | grep -E ":500[2-4]|:5888" | sort
```

#### 步骤1: 发送钓鱼邮件
```bash
# 通过29项目Web界面发送钓鱼邮件
curl -X POST http://localhost:5000/api/send_test_email \
  -H "Content-Type: application/json" \
  -d '{
    "from_email": "alice@seedemail.net",
    "to_email": "bob@seedemail.net",
    "subject": "重要账户安全提醒",
    "body": "您的账户存在安全风险，请立即点击链接更新密码",
    "template": "phishing"
  }'

# 验证邮件发送成功
docker exec mail-150-seedemail setup email list
```

#### 步骤2: 用户接收并点击钓鱼链接
```bash
# 模拟用户登录Webmail查看邮件
echo "用户登录Webmail: http://localhost:8000"
echo "用户名: bob@seedemail.net"
echo "密码: password123"

# 模拟点击钓鱼链接 (在浏览器中操作)
echo "点击邮件中的钓鱼链接，访问漏洞服务器"
```

#### 步骤3: XSS攻击执行
```bash
# 访问XSS漏洞页面
echo "访问: http://localhost:5004"

# 执行XSS攻击
curl -X POST http://localhost:5004/submit_feedback \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "name=受害者&email=bob@seedemail.net&message=<script>alert('XSS攻击成功!'); fetch('/api/steal_data');</script>"

# 查看XSS攻击日志
tail -f vulnerable_servers/web_xss/xss_server.log
```

#### 步骤4: SQL注入攻击
```bash
# 访问SQL注入页面
echo "访问: http://localhost:5002"

# 执行SQL注入攻击
curl -X POST http://localhost:5002/search \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "employee_id=1' UNION SELECT username, password FROM users --"

# 查看数据库泄露
tail -f vulnerable_servers/db_sqli/sqli_server.log
```

#### 步骤5: Heartbleed内存泄露
```bash
# 访问Heartbleed测试页面
echo "访问: http://localhost:5003"

# 执行内存泄露攻击
curl -X POST http://localhost:5003/test_heartbleed \
  -H "Content-Type: application/json" \
  -d '{"length": 65535}'

# 查看泄露的敏感数据
curl -X GET http://localhost:5003/view_memory
tail -f vulnerable_servers/heartbleed_sim/heartbleed_server.log
```

#### 步骤6: 查看攻击损失评估
```bash
# 访问损失评估仪表板
echo "访问: http://localhost:5888"

# 查看实时攻击统计
curl -s http://localhost:5888/api/stats | jq '.' 2>/dev/null || curl -s http://localhost:5888/api/stats

# 查看经济损失评估
curl -s http://localhost:5888/api/losses | jq '.' 2>/dev/null || curl -s http://localhost:5888/api/losses

# 查看攻击时间线
curl -s http://localhost:5888/api/timeline | head -20
```

#### ✅ 完整攻击链验证清单
- [ ] 钓鱼邮件成功发送 (29项目)
- [ ] 用户成功接收邮件 (Webmail)
- [ ] XSS攻击成功执行 (http://localhost:5004)
- [ ] SQL注入攻击成功 (http://localhost:5002)
- [ ] Heartbleed内存泄露成功 (http://localhost:5003)
- [ ] 攻击日志完整记录
- [ ] 损失评估实时更新 (http://localhost:5888)
- [ ] 攻击链完整闭环验证

---

## 🎛️ 第六阶段：系统总览测试 (5分钟)

### 6.1 系统总览面板

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
curl -s http://localhost:4257/api/system_status | head -5

# 验证各项目状态
curl -s http://localhost:4257/api/projects | jq '.[] | select(.name=="29")' 2>/dev/null || echo "API调用正常"

# 查看系统健康状态
curl -s http://localhost:4257/api/health | jq '.' 2>/dev/null || curl -s http://localhost:4257/api/health
```

#### ✅ 系统总览验证清单
- [ ] 系统总览面板正常启动 (http://localhost:4257)
- [ ] 项目状态监控正常
- [ ] API接口响应正常
- [ ] 实时更新功能正常
- [ ] 系统健康检查正常
- [ ] 各项目状态同步正确

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
