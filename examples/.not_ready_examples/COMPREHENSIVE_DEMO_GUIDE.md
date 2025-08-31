# SEED邮件系统 - 完整演示指南

## 🎯 系统概述

SEED邮件系统是基于SEED-Emulator的完整邮件安全实验平台，包含三个渐进式项目：

- **29-email-system (基础版)**：基础邮件系统，快速入门
- **29-1-email-system (真实版)**：真实邮件服务商仿真，复杂网络拓扑
- **30-phishing-ai-system (AI版)**：AI驱动的钓鱼攻防系统

## 🚀 快速启动

### 环境准备
```bash
# 激活环境
source development.env
conda activate seed-emulator

# 加载别名
source docker_aliases.sh
```

### 项目启动命令
```bash
# 启动29基础版
seed-29

# 启动29-1真实版  
seed-29-1

# 启动30 AI版
seed-30

# 停止所有项目
seed-stop

# 检查系统状态
seed-status
```

## 📊 系统端口分配

| 服务 | 端口 | 用途 | 项目 |
|------|------|------|------|
| Web界面(29) | 5000 | 基础版管理界面 | 29-email-system |
| Web界面(29-1) | 5001 | 真实版管理界面 | 29-1-email-system |
| Web界面(30) | 5002 | AI版控制台 | 30-phishing-ai-system |
| 网络地图 | 8080 | SEED网络可视化 | 所有项目 |
| Roundcube | 8081 | Webmail客户端 | 29-email-system |
| Gophish | 3333 | 钓鱼平台管理 | 30-phishing-ai-system |
| Ollama AI | 11434 | AI模型服务 | 30-phishing-ai-system |

## 🌐 Web界面功能

### 29-email-system (http://localhost:5000)
- **基础邮件管理**：创建账户、发送测试邮件
- **网络连通测试**：ping、traceroute、DNS解析
- **Roundcube集成**：完整的webmail客户端
- **项目概述**：技术架构、代码结构、测试方案

### 29-1-email-system (http://localhost:5001)
- **真实服务商管理**：QQ、163、Gmail、Outlook等
- **网络拓扑监控**：4个IX、3个ISP、6个邮件服务商
- **DNS系统测试**：完整的域名解析验证
- **跨服务商测试**：模拟真实的邮件路由

### 30-phishing-ai-system (http://localhost:5002)
- **钓鱼活动管理**：创建、监控、分析钓鱼攻击
- **AI控制台**：Ollama模型、多模态检测
- **目标管理**：用户导入、分组、行为分析
- **安全分析**：攻击效果、防护建议、威胁情报

## 🎭 演示流程

### 第一部分：基础邮件系统 (29项目)
1. **启动系统**
   ```bash
   seed-29
   ```

2. **访问Web界面**
   - 主界面：http://localhost:5000
   - 项目概述：http://localhost:5000/project_overview
   - 网络地图：http://localhost:8080/map.html

3. **核心功能演示**
   - 查看邮件服务器状态
   - 创建测试邮件账户
   - 发送测试邮件
   - 启动Roundcube webmail
   - 进行网络连通性测试

4. **技术亮点**
   - Docker-mailserver集成
   - SEED网络仿真
   - Bootstrap现代界面
   - Roundcube专业邮件客户端

### 第二部分：真实网络仿真 (29-1项目)
1. **切换到真实版**
   ```bash
   seed-stop     # 停止29项目
   seed-29-1     # 启动29-1项目
   ```

2. **访问真实版界面**
   - 主界面：http://localhost:5001
   - 项目概述：http://localhost:5001/project_overview

3. **核心功能演示**
   - 查看真实邮件服务商(QQ/163/Gmail等)
   - 检查Internet Exchange状态
   - 测试DNS系统解析
   - 验证跨ISP邮件路由
   - 模拟国际邮件传输

4. **技术亮点**
   - 4个Internet Exchange(北京/上海/广州/国际)
   - 3大ISP运营商(电信/联通/移动)
   - 完整DNS系统
   - 真实服务商模拟

### 第三部分：AI钓鱼系统 (30项目)
1. **切换到AI版**
   ```bash
   seed-stop     # 停止29-1项目
   seed-30       # 启动30项目
   ```

2. **访问AI控制台**
   - 主界面：http://localhost:5002
   - 项目概述：http://localhost:5002/project_overview
   - Gophish管理：http://localhost:3333

3. **核心功能演示**
   - AI服务状态监控
   - 创建钓鱼活动
   - AI内容生成测试
   - 多模态威胁检测
   - 实时攻击分析

4. **技术亮点**
   - Ollama + Qwen2-7B大语言模型
   - Gophish钓鱼平台集成
   - 多模态AI检测(文本+图像+行为)
   - 实时攻防对抗演示

## 🔧 故障排除

### 常见问题

1. **端口冲突**
   ```bash
   # 检查端口占用
   netstat -tlnp | grep -E "5000|5001|5002|8080|8081"
   
   # 强制清理
   ./force_cleanup.sh force
   ```

2. **Docker权限问题**
   ```bash
   # 使用预设密码清理
   echo "200505071210" | sudo -S docker system prune -f
   ```

3. **环境变量问题**
   ```bash
   # 重新激活环境
   source development.env
   conda activate seed-emulator
   ```

4. **Web界面无法访问**
   ```bash
   # 检查进程
   ps aux | grep -E "webmail_server|app.py"
   
   # 重启Web服务
   pkill -f "webmail_server"
   cd 29-email-system && python3 webmail_server.py
   ```

### 日志查看
```bash
# 查看Web服务日志
tail -f 29-email-system/webmail.log
tail -f 29-1-email-system/webmail.log

# 查看Docker容器日志
seed-logs <容器名称>

# 查看系统状态
seed-status
```

## 📈 演示重点

### 技术创新
1. **渐进式复杂度**：从简单到复杂，层层递进
2. **真实性仿真**：精确模拟真实互联网基础设施
3. **AI技术集成**：攻击生成与防护检测的AI对抗
4. **教育友好**：完整的Web界面和文档系统

### 教育价值
1. **网络协议理解**：BGP、OSPF、DNS、SMTP/IMAP
2. **安全意识提升**：通过实际攻击提高防范意识
3. **AI安全研究**：探索AI在网络安全中的应用
4. **系统架构学习**：大型分布式系统设计

### 实用性
1. **企业培训**：员工安全意识培训
2. **学术研究**：网络安全课程实验
3. **技能提升**：安全专业人员实战训练
4. **威胁分析**：最新攻击手段研究

## 🛡️ 安全注意事项

### 使用原则
- ✅ 仅限教育和研究用途
- ✅ 在隔离的实验环境中使用
- ✅ 获得明确的授权许可
- ✅ 保护参与者隐私数据
- ❌ 禁止用于非法用途
- ❌ 禁止在生产环境中使用

### 数据保护
- 所有数据在本地处理，不上传云端
- 实验结束后及时清理敏感数据
- 使用加密存储重要配置信息
- 定期备份实验数据和配置

## 📚 扩展阅读

### 技术文档
- [SEED-Emulator官方文档](https://github.com/seed-labs/seed-emulator)
- [Docker-mailserver配置指南](https://docker-mailserver.github.io/docker-mailserver/)
- [Gophish用户手册](https://docs.getgophish.com/)
- [Ollama模型部署](https://ollama.ai/docs)

### 学术论文
- "Internet-Scale Security Simulation with SEED"
- "AI-Driven Phishing Attack Detection and Prevention"
- "Multi-modal Threat Intelligence in Email Security"
- "Social Engineering in Cybersecurity Education"

## 🎯 总结

SEED邮件系统提供了从基础到高级的完整邮件安全学习路径：

1. **29项目**：掌握邮件系统基础和SEED框架使用
2. **29-1项目**：理解真实网络架构和服务商运营
3. **30项目**：探索AI技术在安全攻防中的应用

通过这套系统，用户可以：
- 深入理解邮件系统的技术原理
- 体验真实的网络安全威胁
- 学习最新的AI安全技术
- 提升实际的安全防护能力

系统采用模块化设计，支持独立使用或组合使用，为不同层次的用户提供了灵活的学习方案。

---

**🎓 教育声明**：本系统专为教育和研究目的而设计，请在符合法律法规和伦理要求的前提下使用。
