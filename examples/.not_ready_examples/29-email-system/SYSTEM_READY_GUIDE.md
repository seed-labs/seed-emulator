# 🎉 SEED邮件系统 - 完全就绪指南

## 📋 系统状态

**✅ 系统已完全修复和增强，可以开始实验！**

### 解决的问题
- ✅ **Jinja2模板错误**: 修复了`moment()`未定义的问题
- ✅ **Docker TTY问题**: 解决了非交互式环境的连接问题
- ✅ **账户管理**: 预设了9个测试账户，包含密码
- ✅ **Web界面增强**: 集成了Roundcube完整webmail功能
- ✅ **身份验证**: 提供了真实的邮件登录和发送体验

## 🎯 访问地址

| 服务 | 地址 | 说明 |
|------|------|------|
| **SEED管理界面** | http://localhost:5000 | 系统管理、账户创建、网络测试 |
| **Roundcube Webmail** | http://localhost:8080/webmail/ | 完整的邮件收发客户端 |
| **网络拓扑图** | http://localhost:8080/map.html | SEED网络可视化 |
| **统一入口** | http://localhost:8080/ | Nginx代理的统一访问 |

## 🔐 预设测试账户

### seedemail.net 域名
- 📧 **alice@seedemail.net** (密码: password123)
- 📧 **bob@seedemail.net** (密码: password123)  
- 📧 **test@seedemail.net** (密码: test123)

### corporate.local 域名
- 📧 **admin@corporate.local** (密码: admin123)
- 📧 **manager@corporate.local** (密码: manager123)
- 📧 **user@corporate.local** (密码: user123)

### smallbiz.org 域名
- 📧 **info@smallbiz.org** (密码: info123)
- 📧 **support@smallbiz.org** (密码: support123)
- 📧 **sales@smallbiz.org** (密码: sales123)

## 🚀 快速开始

### 1. 启动Roundcube Webmail
```bash
# 方法1: 通过Web界面 (推荐)
# 访问 http://localhost:5000 → 点击"启动 Roundcube"按钮

# 方法2: 命令行启动
docker-compose -f docker-compose-roundcube.yml up -d
```

### 2. 登录Webmail测试
1. 访问 http://localhost:8080/webmail/
2. 使用任意预设账户登录，如:
   - 用户名: `alice@seedemail.net`
   - 密码: `password123`
3. 发送测试邮件到其他账户

### 3. 网络测试
1. 访问 http://localhost:5000
2. 在各个邮件服务器页面测试网络连通性
3. 创建新账户或管理现有账户

## 📧 邮件客户端配置

如果要使用外部邮件客户端(如Thunderbird、Outlook):

### seedemail.net
- **IMAP服务器**: localhost
- **IMAP端口**: 1430 (SSL/TLS)
- **SMTP服务器**: localhost  
- **SMTP端口**: 2525 (STARTTLS) 或 5870 (SSL/TLS)

### corporate.local
- **IMAP服务器**: localhost
- **IMAP端口**: 1431 (SSL/TLS)
- **SMTP服务器**: localhost
- **SMTP端口**: 2526 (STARTTLS) 或 5871 (SSL/TLS)

### smallbiz.org
- **IMAP服务器**: localhost
- **IMAP端口**: 1432 (SSL/TLS)
- **SMTP服务器**: localhost
- **SMTP端口**: 2527 (STARTTLS) 或 5872 (SSL/TLS)

## 🧪 实验场景

### 基础邮件实验
1. **账户创建**: 在Web界面创建新邮件账户
2. **邮件发送**: 使用Roundcube发送测试邮件
3. **跨域通信**: 测试不同域名间的邮件传递
4. **网络诊断**: 使用内置工具测试网络连通性

### 进阶安全实验
1. **邮件路由分析**: 查看邮件在不同AS间的路由路径
2. **协议分析**: 观察SMTP/IMAP协议交互
3. **网络拓扑**: 理解邮件系统的网络架构
4. **故障模拟**: 模拟网络中断对邮件传递的影响

## 🔧 管理操作

### 系统管理
```bash
# 查看系统状态
./test_integration.sh 29

# 重启Web服务
pkill -f webmail_server && python3 webmail_server.py

# 清理环境
./force_cleanup.sh force

# 快速启动
./quick_start.sh 29
```

### 账户管理
```bash
# 批量创建预设账户
python3 setup_accounts.py

# 手动创建账户
docker exec -i mail-150-seedemail setup email add newuser@seedemail.net

# 查看账户列表
docker exec mail-150-seedemail setup email list
```

### 服务管理
```bash
# 启动Roundcube
docker-compose -f docker-compose-roundcube.yml up -d

# 停止Roundcube
docker-compose -f docker-compose-roundcube.yml down

# 查看容器状态
docker-compose ps
```

## 🎓 教学应用

### 适用课程
- **网络安全基础**: 邮件协议和安全机制
- **网络管理**: 邮件服务器配置和维护
- **系统集成**: 多服务协同工作原理
- **Web开发**: 邮件系统的Web界面设计

### 实验设计
1. **基础实验**: 邮件系统搭建和配置 (1-2课时)
2. **网络实验**: 邮件路由和协议分析 (2-3课时)  
3. **安全实验**: 邮件安全机制研究 (2-3课时)
4. **综合实验**: 完整邮件系统评估 (3-4课时)

## 🔍 故障排除

### 常见问题

#### Web界面无法访问
```bash
# 检查服务状态
ps aux | grep webmail_server

# 重启服务
pkill -f webmail_server && python3 webmail_server.py

# 检查端口
lsof -i :5000
```

#### Roundcube无法启动
```bash
# 检查Docker网络
docker network ls | grep output

# 重新创建配置
python3 roundcube_integration.py

# 手动启动
docker-compose -f docker-compose-roundcube.yml up -d
```

#### 邮件发送失败
```bash
# 检查邮件服务器日志
docker logs mail-150-seedemail

# 验证账户存在
docker exec mail-150-seedemail setup email list

# 测试网络连通性
docker exec as160h-host_0-10.160.0.71 ping 10.150.0.10
```

## 📈 系统扩展

### 添加新邮件服务器
1. 修改 `email_simple.py` 中的AS配置
2. 添加新的邮件服务器定义
3. 更新 `webmail_server.py` 中的MAIL_SERVERS列表
4. 重新生成配置: `python3 email_simple.py arm`

### 集成其他服务
1. **DNS服务器**: 添加自定义DNS解析
2. **代理服务器**: 集成HTTP/SOCKS代理
3. **监控系统**: 添加性能监控和报警
4. **日志分析**: 集成ELK日志分析栈

## 🎯 最佳实践

### 实验前准备
1. 确保Docker服务正常运行
2. 检查端口占用情况 (5000, 8080, 2525-2527)
3. 预留足够的系统资源 (4GB+ RAM)
4. 备份重要的实验数据

### 实验过程中
1. 使用预设账户进行初始测试
2. 逐步增加复杂度，先简单后复杂
3. 记录实验步骤和观察结果
4. 遇到问题及时查看日志和错误信息

### 实验结束后
1. 导出重要的邮件和日志数据
2. 清理实验环境释放资源
3. 总结实验结果和学习收获
4. 为下次实验做好准备

---

## 🎊 恭喜！

您现在拥有了一个功能完整、用户友好的SEED邮件系统实验平台！

- **完善的功能**: 从基础管理到完整webmail
- **真实的体验**: 预设账户和真实邮件收发  
- **教学友好**: 清晰的界面和详细的文档
- **扩展性强**: 易于定制和功能扩展

**🚀 现在就开始您的邮件安全实验之旅吧！**
