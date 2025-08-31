# 🎯 SEED邮件系统 - 完整集成指南

## 📋 项目概述

SEED邮件系统是基于SEED-Emulator框架开发的完整邮件网络仿真平台，包含三个递进版本：

- **29-email-system**: 基础版，带Web管理界面
- **29-1-email-system**: 真实版，模拟真实ISP和邮件服务商  
- **30-phishing-ai-system**: AI钓鱼版，集成AI驱动的攻防平台

## 🚀 快速开始

### 环境准备

```bash
# 1. 进入项目目录
cd /home/parallels/seed-email-system

# 2. 设置环境变量
source development.env

# 3. 激活虚拟环境
conda activate seed-emulator

# 4. 进入实验目录
cd examples/.not_ready_examples
```

### 加载管理别名

```bash
# 方式1: 临时加载 (推荐)
source docker_aliases.sh

# 方式2: 永久加载到bashrc
./setup_aliases.sh
```

## 📧 29-email-system (基础版)

### 特色功能
- ✅ **Web管理界面**: 简洁直观的邮件系统管理
- ✅ **三个邮件域**: seedemail.net, corporate.local, smallbiz.org  
- ✅ **完整网络**: BGP路由、AS互联、Internet Map可视化
- ✅ **测试友好**: 明确标识"29测试网络"环境

### 启动方式

#### 方法1: 使用别名 (推荐)
```bash
seed-29
```

#### 方法2: 手动启动
```bash
cd 29-email-system

# 生成配置
python3 email_simple.py arm

# 启动Docker容器
cd output && docker-compose up -d

# 启动Web界面
cd .. && nohup python3 webmail_server.py > webmail.log 2>&1 &
```

### 访问地址
- **Web管理界面**: http://localhost:5000
- **网络拓扑图**: http://localhost:8080/map.html
- **邮件服务端口**:
  - seedemail.net: SMTP: localhost:2525, IMAP: localhost:1430
  - corporate.local: SMTP: localhost:2526, IMAP: localhost:1431  
  - smallbiz.org: SMTP: localhost:2527, IMAP: localhost:1432

### 创建邮件账户
```bash
# 方式1: 通过Web界面 (推荐)
# 访问 http://localhost:5000 → 邮件管理 → 创建账户

# 方式2: 命令行
docker exec -it mail-150-seedemail setup email add user@seedemail.net
docker exec -it mail-151-corporate setup email add admin@corporate.local
docker exec -it mail-152-smallbiz setup email add info@smallbiz.org
```

## 🌐 29-1-email-system (真实版)

### 特色功能
- ✅ **真实ISP**: 中国电信、联通、移动三大运营商
- ✅ **地理分布**: 北京、上海、广州、海外四地
- ✅ **真实服务商**: QQ、163、Gmail、Outlook、企业、自建
- ✅ **DNS系统**: 完整的DNS层次结构

### 启动方式

#### 方法1: 使用别名 (推荐)
```bash
seed-29-1
```

#### 方法2: 手动启动
```bash
cd 29-1-email-system
python3 email_realistic.py arm
cd output && docker-compose up -d
```

### 访问地址
- **网络拓扑图**: http://localhost:8080/map.html
- **真实邮件服务商端口**:
  - QQ邮箱: localhost:2200
  - 163邮箱: localhost:2201
  - Gmail: localhost:2202
  - Outlook: localhost:2203
  - 企业邮箱: localhost:2204
  - 自建邮箱: localhost:2205

### 网络测试
```bash
# 使用集成的测试脚本
python3 test_network.py

# 手动测试连通性
docker exec -it mail-qq-tencent ping mail-gmail-google
```

## 🤖 30-phishing-ai-system (AI钓鱼版)

### 特色功能
- ✅ **AI邮件生成**: 基于Qwen2-7B的智能钓鱼邮件
- ✅ **AI防护检测**: 多模态检测系统
- ✅ **Gophish集成**: 完整的钓鱼活动管理
- ✅ **6种攻击场景**: 从基础到高级的钓鱼实验

### 启动方式
```bash
seed-30
# 或
cd 30-phishing-ai-system && ./start_phishing_ai.sh
```

### 访问地址
- **AI控制台**: http://localhost:5000
- **Gophish平台**: https://localhost:3333
- **Ollama AI**: http://localhost:11434

## 🛠️ 管理工具

### 系统状态检查
```bash
# 检查整体状态
seed-status

# 检查AI服务状态 (30项目)
seed-ai-status

# 检查端口占用
seed-check-ports

# 集成测试
./test_integration.sh 29      # 测试29项目
./test_integration.sh 29-1    # 测试29-1项目
./test_integration.sh 30      # 测试30项目
```

### 容器管理
```bash
# 查看运行中的容器
dockps

# 进入容器
seed-shell <容器名>

# 查看容器日志
seed-logs <容器名>
```

### 邮件测试
```bash
# 发送测试邮件
seed-mail-send admin@seedemail.net user@corporate.local "测试" "这是测试邮件"

# 网络连通性测试
seed-ping <源容器> <目标IP>
```

## 🧹 清理和维护

### 标准清理
```bash
# 停止所有项目
seed-stop

# 或使用强力清理
./force_cleanup.sh
```

### 强制清理 (解决权限问题)
```bash
# 强制模式，自动处理sudo权限
./force_cleanup.sh force

# 紧急停止所有服务
seed-emergency-stop
```

### 清理特定项目
```bash
# 清理29项目
cd 29-email-system/output && docker-compose down --remove-orphans

# 清理权限问题
sudo rm -rf output/mail-*-data
sudo chown -R $(whoami):$(whoami) output/
```

## 🔧 故障排除

### 常见问题

#### 1. 端口被占用
```bash
# 检查端口占用
lsof -i :5000
lsof -i :8080

# 释放端口
./force_cleanup.sh force
```

#### 2. 权限问题
```bash
# Docker创建的目录权限问题
sudo chown -R $(whoami):$(whoami) output/
sudo rm -rf output/mail-*-data
```

#### 3. 容器启动失败
```bash
# 检查容器状态
docker-compose ps

# 查看容器日志
docker logs <容器名>

# 重新生成配置
rm -rf output && python3 email_simple.py arm
```

#### 4. Web界面无法访问
```bash
# 检查Web服务进程
ps aux | grep webmail_server

# 重启Web服务
pkill -f webmail_server
cd 29-email-system && python3 webmail_server.py
```

#### 5. 网络连通性问题
```bash
# 检查Docker网络
docker network ls

# 测试容器间连通性
docker exec -it <容器1> ping <容器2>

# 重启Docker服务
sudo systemctl restart docker
```

### 环境重置
```bash
# 完全重置环境
./force_cleanup.sh force
sudo systemctl restart docker
docker system prune -af

# 重新设置环境
cd /home/parallels/seed-email-system
source development.env
conda activate seed-emulator
```

## 📊 性能和扩展

### 系统要求
- **最低配置**: 2核CPU, 4GB RAM, 10GB磁盘
- **推荐配置**: 4核CPU, 8GB RAM, 20GB磁盘
- **大规模实验**: 8核CPU, 16GB RAM, 50GB磁盘

### 扩展建议
- **增加邮件服务器**: 修改Python脚本中的AS和邮件服务器配置
- **自定义域名**: 在邮件服务器配置中添加新域名
- **网络拓扑扩展**: 增加新的AS和IX连接
- **AI模型替换**: 在30项目中替换不同的LLM模型

## 🎓 教学应用

### 课程集成
- **网络安全基础**: 使用29项目理解邮件协议
- **网络架构**: 使用29-1项目学习ISP互联
- **AI安全**: 使用30项目体验AI攻防
- **社会工程学**: 通过钓鱼实验提高防范意识

### 实验设计
1. **基础实验**: 邮件系统配置和测试
2. **网络实验**: 跨AS邮件路由分析
3. **安全实验**: 钓鱼攻击检测和防护
4. **综合实验**: 完整的邮件安全评估

## 🔮 进阶使用

### 自定义配置
```python
# 修改29项目的邮件服务器
# 编辑 email_simple.py
asn = 200  # 新的AS号
domain = "custom.edu"  # 自定义域名
```

### 与其他SEED实验集成
```bash
# 集成到现有SEED实验
cp -r 29-email-system /path/to/seed-experiment/
# 修改网络配置以适配现有拓扑
```

### 数据收集和分析
```bash
# 收集邮件日志
docker logs mail-150-seedemail > email_logs.txt

# 网络流量分析
docker exec -it as150h-host_0 tcpdump -i any -w traffic.pcap
```

## 📞 支持和贡献

### 获取帮助
- **查看文档**: 各项目目录下的README.md
- **检查日志**: webmail.log, Docker容器日志
- **社区支持**: SEED-Emulator GitHub Issues

### 贡献代码
1. Fork SEED-Emulator项目
2. 在examples/.not_ready_examples下创建新实验
3. 遵循现有的文档和代码风格
4. 提交Pull Request

---

## 🎉 总结

SEED邮件系统为网络安全教学和研究提供了完整的实验平台：

- **29项目**: 快速体验和学习的理想选择
- **29-1项目**: 深入理解真实网络架构
- **30项目**: 探索AI在网络安全中的应用

通过本指南，您可以快速部署和使用这个强大的邮件安全实验平台，为网络安全教育和研究提供有力支持。

**🎓 Happy Learning & Stay Secure!**