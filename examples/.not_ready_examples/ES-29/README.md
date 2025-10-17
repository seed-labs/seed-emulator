# SEED 邮件系统 - 基础版 (29-email-system)

一个基于SEED Emulator的完整邮件系统仿真环境，集成了docker-mailserver和Roundcube Webmail，提供真实的邮件收发体验。

## ✨ 核心特性

- 🌐 **完整的网络拓扑**: 3个邮件AS + 2个客户端AS + BGP/OSPF路由
- 📧 **多域名支持**: seedemail.net、corporate.local、smallbiz.org
- 📬 **Roundcube Webmail**: 真实的Web邮件客户端（类似Gmail）
- 🚀 **即开即用**: 一键启动，自动配置
- 🎓 **教学友好**: 适合网络协议、安全测试教学

## 🚀 快速开始（TL;DR）

```bash
# 准备环境
cd /home/parallels/seed-email-system && source development.env

# 进入项目并生成
cd examples/.not_ready_examples/29-email-system
/home/parallels/miniconda3/envs/seed-emulator/bin/python email_simple.py arm

# 启动与初始化
cd output && docker-compose up -d && cd ..
./manage_roundcube.sh accounts
./manage_roundcube.sh start
```

## 🧹 快速清理/停止

```bash
# 停止 Roundcube（可选）
./manage_roundcube.sh stop

# 停止 29 邮件系统（在 output/ 下执行）
cd output && docker-compose down && cd ..
```

## 🌐 访问系统

启动后访问：

| 服务 | 地址 | 说明 |
|------|------|------|
| **Roundcube** | http://localhost:8081 | Web邮件客户端 |
| **Web管理** | http://localhost:5000 | 系统管理界面 |
| **网络拓扑** | http://localhost:8080/map.html | 网络可视化 |

**测试账户**：
- alice@seedemail.net / password123
- bob@seedemail.net / password123  
- admin@corporate.local / password123
- info@smallbiz.org / password123

## 📊 系统架构

### 网络拓扑

```
                Internet Exchange (IX-100)
                         |
                  Transit AS-2 (ISP)
                         |
      ┌──────────────────┼──────────────────┐
      │                  │                  │
 AS-150 (Public)    AS-151 (Corp)    AS-152 (Small)
 seedemail.net    corporate.local    smallbiz.org
      │                  │                  │
 Mail Server         Mail Server        Mail Server
 10.150.0.10        10.151.0.10       10.152.0.10
      
              Client Networks (AS-160, AS-161)
```

### 端口映射

| 服务器 | SMTP | IMAP | IMAPS | Submission |
|--------|------|------|-------|------------|
| seedemail.net | 2525 | 1430 | 9930 | 5870 |
| corporate.local | 2526 | 1431 | 9931 | 5871 |
| smallbiz.org | 2527 | 1432 | 9932 | 5872 |

## 🛠️ 管理命令

### Roundcube管理

```bash
./manage_roundcube.sh start     # 启动Roundcube
./manage_roundcube.sh stop      # 停止Roundcube
./manage_roundcube.sh restart   # 重启
./manage_roundcube.sh status    # 查看状态
./manage_roundcube.sh logs      # 查看日志
./manage_roundcube.sh accounts  # 创建测试账户
```

### 邮件系统管理

```bash
# 启动Web管理界面
./start_webmail.sh

# 查看容器状态
cd output && docker-compose ps

# 查看邮件服务器日志
docker logs mail-150-seedemail -f

# 停止所有容器
docker-compose down
```

### 手动创建邮件账户

```bash
# seedemail.net账户
printf "password\npassword\n" | docker exec -i mail-150-seedemail setup email add user@seedemail.net

# corporate.local账户
printf "password\npassword\n" | docker exec -i mail-151-corporate setup email add user@corporate.local

# smallbiz.org账户
printf "password\npassword\n" | docker exec -i mail-152-smallbiz setup email add user@smallbiz.org

# 查看账户列表
docker exec mail-150-seedemail setup email list
```

## 📧 使用Roundcube

### 登录

1. 打开 http://localhost:8081
2. 输入用户名和密码
3. 选择服务器（或留空自动检测）
4. 点击登录

### 发送邮件

1. 点击"写邮件"按钮
2. 填写收件人、主题和内容
3. 点击"发送"

### 跨域邮件测试

可以测试不同域之间的邮件发送：
- alice@seedemail.net → bob@seedemail.net (同域)
- alice@seedemail.net → admin@corporate.local (跨域)
- bob@seedemail.net → info@smallbiz.org (跨域)

## 🔧 项目结构

```
29-email-system/
├── email_simple.py                 # 主程序：生成邮件系统
├── webmail_server.py               # Web管理界面
├── start_webmail.sh                # Web管理界面启动脚本
├── manage_roundcube.sh             # Roundcube管理脚本
├── docker-compose-roundcube.yml    # Roundcube Docker配置
├── roundcube-config/               # Roundcube自定义配置
│   └── config.inc.php
├── templates/                      # Web界面模板
├── static/                         # 静态资源
└── output/                         # 生成的Docker配置
```

## 🎓 教学应用

### 适用课程

- **网络协议**: SMTP/IMAP协议学习
- **系统管理**: 邮件服务器配置
- **网络安全**: 钓鱼邮件测试
- **Docker技术**: 容器编排实践

### 实验场景

**1. 邮件协议分析**
```bash
# 抓包分析SMTP协议
docker exec as150h-host_0 tcpdump -i any port 25 -w smtp.pcap

# 观察邮件头部
docker exec mail-150-seedemail cat /var/mail/seedemail.net/bob/new/*
```

**2. 网络路由观察**
```bash
# 查看BGP路由
docker exec as150brd-router0 birdc show route

# 跟踪邮件路径
docker exec as150h-host_0 traceroute 10.151.0.10
```

**3. 钓鱼邮件测试**
- 使用Roundcube发送测试钓鱼邮件
- 观察用户行为和邮件过滤
- 练习识别钓鱼特征

## 🔍 故障排除

### Roundcube无法访问

```bash
# 检查容器状态
docker ps | grep roundcube

# 查看日志
docker logs roundcube-webmail

# 重启
./manage_roundcube.sh restart
```

### 无法发送/接收邮件

```bash
# 检查邮件服务器
cd output && docker-compose ps | grep mail

# 查看邮件服务器日志
docker logs mail-150-seedemail -f

# 检查账户是否存在
docker exec mail-150-seedemail setup email list
```

### 端口被占用

```bash
# 检查端口
netstat -tlnp | grep -E "8081|2525|5000"

# 停止占用的服务
docker-compose down
```

## 💡 高级配置

### 自定义Roundcube配置

编辑 `roundcube-config/config.inc.php` 可以自定义：
- 界面语言和主题
- 邮件发送设置
- 插件配置
- 安全选项

修改后重启Roundcube：
```bash
./manage_roundcube.sh restart
```

### 使用外部邮件客户端

可以使用Thunderbird、Outlook等客户端：

**IMAP设置**：
- 服务器: localhost
- 端口: 1430 / 1431 / 1432
- 加密: 无

**SMTP设置**：
- 服务器: localhost
- 端口: 2525 / 2526 / 2527
- 加密: 无

## 📚 详细文档

- **[DEMO-TEACH.md](./DEMO-TEACH.md)** - 演示教学指南（推荐）⭐
- `manage_roundcube.sh --help` - Roundcube管理帮助
- `FINAL_STATUS.md` - 项目状态

## ⚠️ 注意事项

1. **仅供学习使用**: 这是实验环境，不要用于生产
2. **安全设置简化**: TLS证书为自签名，密码为测试密码
3. **资源占用**: 约需2-3GB内存，建议至少4GB内存
4. **网络隔离**: 系统运行在Docker网络中，与宿主机网络隔离

## 📊 系统资源

- **容器数量**: ~20个
- **内存占用**: ~500MB
- **启动时间**: ~60秒
- **存储空间**: ~2GB

## 🐛 问题反馈

如遇问题：
1. 查看容器日志
2. 检查网络连接
3. 参考故障排除章节
4. 查看详细文档

## 🔄 更新日志

### v1.0 (2025-10-02)
- ✅ 基础邮件系统完成
- ✅ Roundcube Webmail集成
- ✅ 管理脚本开发
- ✅ 文档体系建立

---

**版本**: 1.0  
**状态**: ✅ 可用  
**维护**: SEED Lab Team  
**推荐**: ⭐⭐⭐⭐⭐
