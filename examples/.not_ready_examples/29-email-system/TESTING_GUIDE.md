# 邮件系统测试指南

## 🎉 当前状态
✅ **MVP邮件系统已成功搭建并运行！**

## 📊 系统概览

### 已部署的邮件服务器
| 域名 | 容器名 | 内网IP | SMTP端口 | IMAP端口 | 状态 |
|-----|-------|--------|---------|---------|------|
| seedemail.net | mail-150-seedemail | 10.150.0.10 | :2525 | :1430 | ✅ 运行中 |
| corporate.local | mail-151-corporate | 10.151.0.10 | :2526 | :1431 | ✅ 运行中 |
| smallbiz.org | mail-152-smallbiz | 10.152.0.10 | :2527 | :1432 | ✅ 运行中 |

### 已创建的邮件账户
- 📧 **alice@seedemail.net** (密码: password123)
- 📧 **bob@seedemail.net** (密码: password123)  
- 📧 **admin@corporate.local** (密码: admin123)
- 📧 **info@smallbiz.org** (密码: info123)

### 网络拓扑
```
Internet Exchange (IX-100)
           |
    Transit AS-2 (ISP)
           |
  ┌────────┼────────┐
AS-150   AS-151   AS-152   AS-160   AS-161
Email    Corp     Small    Client   Client
```

## 🧪 测试方法

### 1. 检查服务状态
```bash
# 查看所有容器状态
docker-compose ps

# 查看邮件服务器日志
docker logs mail-150-seedemail -f
docker logs mail-151-corporate -f 
docker logs mail-152-smallbiz -f
```

### 2. 网络可视化
访问 **http://localhost:8080/map.html** 查看网络拓扑图

### 3. 端口连通性测试
```bash
# 测试SMTP端口
telnet localhost 2525  # seedemail.net
telnet localhost 2526  # corporate.local
telnet localhost 2527  # smallbiz.org

# 测试IMAP端口
telnet localhost 1430  # seedemail.net IMAP
telnet localhost 1431  # corporate.local IMAP
telnet localhost 1432  # smallbiz.org IMAP
```

### 4. 邮件账户管理
```bash
# 创建新账户
printf "newpassword\nnewpassword\n" | docker exec -i mail-150-seedemail setup email add user@seedemail.net

# 列出账户
docker exec -it mail-150-seedemail setup email list

# 删除账户
docker exec -it mail-150-seedemail setup email del user@seedemail.net
```

### 5. 内网邮件测试
```bash
# 进入客户端容器
docker exec -it as160h-host_0-10.160.0.71 bash

# 安装邮件测试工具
apt update && apt install -y swaks telnet

# 测试SMTP连接（可能需要等待路由收敛）
telnet 10.150.0.10 25
```

## 🔧 故障排除

### 常见问题及解决方案

#### 1. 容器启动失败
```bash
# 清理并重启
docker-compose down --remove-orphans
docker system prune -f
docker network prune -f
docker-compose up -d
```

#### 2. 端口冲突
如果端口被占用，可以修改 `email_simple.py` 中的端口配置：
```python
'ports': {'smtp': '2525', 'submission': '5870', 'imap': '1430', 'imaps': '9930'}
```

#### 3. 网络连通性问题
- **症状**: AS之间无法ping通
- **原因**: BGP路由收敛需要时间（1-2分钟）
- **解决**: 等待路由收敛，或重启相关路由器容器

#### 4. 邮件服务器配置问题
```bash
# 查看详细日志
docker logs mail-150-seedemail --follow

# 重启特定邮件服务器
docker-compose restart mail-150-seedemail
```

#### 5. dovecot认证错误
这是正常的初始化过程，服务完全启动后会自动解决。

## 📬 邮件客户端配置

### 使用外部邮件客户端

#### IMAP接收配置
- **服务器**: localhost
- **端口**: 1430/1431/1432 
- **加密**: 无 (测试环境)
- **用户名**: 完整邮箱地址
- **密码**: 对应账户密码

#### SMTP发送配置  
- **服务器**: localhost
- **端口**: 2525/2526/2527
- **加密**: 无 (测试环境)
- **用户名**: 完整邮箱地址
- **密码**: 对应账户密码

### 推荐的邮件客户端
1. **Thunderbird** (跨平台)
2. **Evolution** (Linux)
3. **Mail.app** (macOS)
4. **Outlook** (Windows)

## 🚀 高级测试

### 1. 跨域邮件测试
```bash
# 从seedemail.net向corporate.local发送邮件
docker exec -it as150h-host_0-10.150.0.71 bash
swaks --to admin@corporate.local \
      --from alice@seedemail.net \
      --server 10.151.0.10:25 \
      --auth-user alice@seedemail.net \
      --auth-password password123
```

### 2. 大量用户测试
```bash
# 批量创建用户
for i in {1..10}; do
    printf "test123\ntest123\n" | docker exec -i mail-150-seedemail setup email add user$i@seedemail.net
done
```

### 3. 性能测试
```bash
# 监控资源使用
docker stats mail-150-seedemail mail-151-corporate mail-152-smallbiz
```

## 📝 下一步发展

### 计划中的功能扩展
1. **DNS系统集成** - 自动域名解析
2. **SSL/TLS加密** - 安全连接支持  
3. **Webmail界面** - 浏览器邮件客户端
4. **防垃圾邮件** - SpamAssassin集成
5. **邮件备份** - 自动备份策略

### 钓鱼攻击实验扩展
1. **伪造邮件发送** - SPF/DKIM测试
2. **钓鱼网站托管** - 社会工程学实验
3. **邮件安全检测** - 恶意附件检测

## 🏆 成果总结

✅ **已完成的功能**:
- 基础网络拓扑搭建
- 3个独立域名的邮件服务器
- ARM64/AMD64平台兼容
- 邮件账户管理
- 端口映射和网络隔离
- 可视化网络监控

🎯 **技术亮点**:
- docker-mailserver完整集成
- SEED Emulator网络仿真
- 多AS邮件通信架构
- 可扩展的模块化设计

这个MVP版本为后续的安全实验和功能扩展奠定了坚实的基础！🎉
