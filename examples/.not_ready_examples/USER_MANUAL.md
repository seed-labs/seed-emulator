# SEED 邮件系统用户手册

**版本**: 1.0  
**日期**: 2025-10-02  
**适用项目**: 29-email-system, 29-1-email-system

---

## 🚀 5分钟快速上手

### 方案A: 基础邮件系统（29项目 - 推荐新手）

```bash
# 1. 环境准备（只需一次）
cd /home/parallels/seed-email-system
source development.env

# 2. 启动系统（两步）
cd examples/.not_ready_examples/29-email-system
/home/parallels/miniconda3/envs/seed-emulator/bin/python email_simple.py arm
cd output && docker-compose up -d && cd ..
./manage_roundcube.sh start && ./manage_roundcube.sh accounts

# 3. 使用系统
# 打开浏览器: http://localhost:8081
# 登录: alice@seedemail.net / password123
# 发送邮件给: bob@seedemail.net
```

### 方案B: 真实邮件系统（29-1项目 - 带DNS）

```bash
# 1. 环境准备（只需一次）
cd /home/parallels/seed-email-system
source development.env

# 2. 启动系统（两步+等待）
cd examples/.not_ready_examples/29-1-email-system
/home/parallels/miniconda3/envs/seed-emulator/bin/python email_realistic.py arm
cd output && docker-compose up -d && cd ..

# ⏰ 重要：等待DNS和BGP启动（3分钟）
sleep 180

./manage_roundcube.sh start && ./manage_roundcube.sh accounts

# 3. 测试DNS（29-1特色）
docker exec as150h-dns-cache-10.150.0.53 nslookup qq.com

# 4. 使用系统
# 打开浏览器: http://localhost:8082
# 登录: user@qq.com / password123
# 发送邮件给: user@gmail.com（跨服务商）
```

---

## 📊 项目选择指南

### 选择29项目，如果你想：
- ✅ 快速体验邮件系统
- ✅ 学习基础SMTP/IMAP协议
- ✅ 资源有限（< 4GB内存）
- ✅ 简单的网络拓扑
- ✅ 快速启动演示

### 选择29-1项目，如果你想：
- ✅ 模拟真实互联网环境
- ✅ 学习DNS系统
- ✅ 测试跨服务商邮件路由
- ✅ 研究BGP和DNS交互
- ✅ 更复杂的实验场景
- ✅ 有充足资源（> 8GB内存）

---

## 🌐 访问地址速查

### 29项目
| 服务 | URL | 说明 |
|------|-----|------|
| Roundcube | http://localhost:8081 | Web邮件客户端 |
| 网络拓扑 | http://localhost:8080/map.html | 网络可视化 |
| Web管理 | http://localhost:5000 | 系统管理（可选） |

### 29-1项目
| 服务 | URL | 说明 |
|------|-----|------|
| Roundcube | http://localhost:8082 | Web邮件客户端 |
| 网络拓扑 | http://localhost:8080/map.html | 网络可视化 |
| Web管理 | http://localhost:5001 | 系统管理（可选） |

---

## 🔐 测试账户

### 29项目账户
| 邮箱 | 密码 | 服务器 |
|------|------|--------|
| alice@seedemail.net | password123 | Public Email |
| bob@seedemail.net | password123 | Public Email |
| admin@corporate.local | password123 | Corporate |
| info@smallbiz.org | password123 | Small Business |

### 29-1项目账户  
| 邮箱 | 密码 | 服务商 |
|------|------|--------|
| user@qq.com | password123 | QQ邮箱 |
| user@163.com | password123 | 163邮箱 |
| user@gmail.com | password123 | Gmail |
| user@outlook.com | password123 | Outlook |
| admin@company.cn | password123 | 企业邮箱 |
| founder@startup.net | password123 | 自建邮箱 |

---

## 📧 使用Roundcube收发邮件

### 登录步骤
1. 打开浏览器访问对应端口
2. 输入完整邮箱地址（如 alice@seedemail.net）
3. 输入密码
4. 点击"登录"

### 发送邮件
1. 点击左上角"写邮件"按钮
2. 填写收件人邮箱
3. 填写主题和正文
4. 点击"发送"

### 查看邮件
1. 登录后自动显示收件箱
2. 点击邮件查看内容
3. 可以回复、转发、删除

### 跨域/跨服务商邮件
- 29项目: seedemail.net ↔ corporate.local ↔ smallbiz.org
- 29-1项目: qq.com ↔ gmail.com ↔ 163.com ↔ outlook.com等

---

## 🛠️ 管理命令速查

### Roundcube管理
```bash
./manage_roundcube.sh start     # 启动
./manage_roundcube.sh stop      # 停止
./manage_roundcube.sh restart   # 重启
./manage_roundcube.sh status    # 状态
./manage_roundcube.sh logs      # 日志
./manage_roundcube.sh accounts  # 创建账户
./manage_roundcube.sh help      # 帮助
```

### Docker管理
```bash
# 查看容器
cd output && docker-compose ps

# 查看邮件服务器日志
docker logs mail-150-seedemail  # 29项目
docker logs mail-qq-tencent     # 29-1项目

# 停止所有容器
docker-compose down

# 重启特定容器
docker-compose restart mail-150-seedemail
```

### 手动创建账户
```bash
# 格式: printf "密码\n密码\n" | docker exec -i 容器名 setup email add 邮箱

# 29项目
printf "mypass\nmypass\n" | docker exec -i mail-150-seedemail setup email add user@seedemail.net

# 29-1项目
printf "mypass\nmypass\n" | docker exec -i mail-qq-tencent setup email add user@qq.com
```

---

## 🔍 故障排除

### 问题1: Roundcube无法访问

```bash
# 检查容器
docker ps | grep roundcube

# 查看日志
docker logs roundcube-webmail        # 29项目
docker logs roundcube-webmail-29-1   # 29-1项目

# 重启
./manage_roundcube.sh restart
```

### 问题2: 无法发送/接收邮件

```bash
# 检查邮件服务器
docker ps | grep mail

# 查看日志
docker logs mail-150-seedemail -f

# 检查账户
docker exec mail-150-seedemail setup email list
```

### 问题3: 端口被占用

```bash
# 检查端口
netstat -tlnp | grep -E "8081|8082|2525"

# 停止冲突服务
cd output && docker-compose down
```

### 问题4: DNS不工作（仅29-1）

```bash
# 等待更长时间（DNS需要时间启动）
sleep 180

# 测试DNS
docker exec as150h-dns-cache-10.150.0.53 nslookup qq.com

# 如果仍失败，查看DNS测试指南
cat DNS_TESTING_GUIDE.md
```

### 问题5: 容器启动失败

```bash
# 清理旧容器和网络
docker-compose down
docker network prune -f

# 重新启动
docker-compose up -d
```

---

## 💡 使用技巧

### 技巧1: 同时运行两个项目对比

两个项目使用不同的端口，可以同时运行进行对比：
- 29: 端口 2525-2527, 8081
- 29-1: 端口 2200-2205, 8082

### 技巧2: 使用Web拓扑图

访问 http://localhost:8080/map.html 可以看到：
- 完整的网络拓扑
- AS之间的连接
- DNS服务器分布（29-1）
- BGP路由关系

### 技巧3: 监控邮件队列

```bash
# 查看邮件队列
docker exec mail-150-seedemail postqueue -p

# 刷新队列
docker exec mail-150-seedemail postqueue -f
```

### 技巧4: 抓包分析

```bash
# 抓取SMTP流量
docker exec as150h-host_0 tcpdump -i any port 25 -w smtp.pcap

# 抓取DNS流量（29-1）
docker exec as150h-dns-cache-10.150.0.53 tcpdump -i any port 53 -w dns.pcap
```

---

## 📚 学习路径推荐

### 第1周: 基础入门（29项目）
1. 启动29项目
2. 使用Roundcube发送/接收邮件
3. 观察SMTP/IMAP协议
4. 理解邮件服务器配置

### 第2周: 进阶学习（29-1项目）
1. 启动29-1项目
2. 测试DNS解析功能
3. 观察跨服务商邮件路由
4. 分析BGP和DNS交互

### 第3周: 深入研究
1. 抓包分析协议细节
2. 自定义配置文件
3. 尝试钓鱼邮件测试
4. 开发自己的扩展

---

## ⚠️ 重要注意事项

### 资源要求
- **29项目**: 至少4GB内存，10GB磁盘
- **29-1项目**: 至少8GB内存，15GB磁盘

### 启动时间
- **29项目**: ~60秒
- **29-1项目**: ~180秒（包含DNS和BGP收敛）

### 安全提示
1. **仅供学习**: 不要用于生产环境
2. **网络隔离**: 系统运行在Docker网络中
3. **简化安全**: TLS证书为自签名
4. **测试密码**: 修改密码后请更新

### 性能优化
1. **减少容器**: 如资源不足，可减少客户端AS数量
2. **关闭不用的服务**: 可以选择性启动某些邮件服务器
3. **定期清理**: 清理Docker镜像和volume

---

## 📖 详细文档索引

### 项目文档
- **29项目**: `29-email-system/README.md`
- **29-1项目**: `29-1-email-system/README.md`

### 专题文档
- **DNS测试**: `29-1-email-system/DNS_TESTING_GUIDE.md`
- **项目总结**: `FINAL_PROJECT_SUMMARY.md`
- **项目规划**: `PROJECT_STATUS_AND_PLAN.md`

### 在线帮助
```bash
./manage_roundcube.sh help     # Roundcube管理帮助
python email_simple.py         # 查看使用方法
python email_realistic.py      # 查看使用方法
```

---

## 🎓 教学应用示例

### 实验1: 邮件协议分析
```bash
# 启动29项目
# 使用Roundcube发送邮件
# 同时抓包观察SMTP协议
docker exec as150h-host_0 tcpdump -i any port 25 -A
```

### 实验2: DNS层次结构（29-1）
```bash
# 启动29-1项目
# 测试DNS解析路径
docker exec as150h-dns-cache-10.150.0.53 dig @10.150.0.53 qq.com +trace
```

### 实验3: 跨域邮件路由
```bash
# 使用Roundcube发送跨域邮件
# 观察邮件在不同AS间的传输
# 查看邮件头部信息理解路由过程
```

### 实验4: 钓鱼邮件测试
```bash
# 使用Roundcube创建钓鱼邮件模板
# 观察用户反应
# 练习识别钓鱼特征
```

---

## 🐛 常见问题FAQ

### Q1: 容器启动很慢？
**A**: 正常现象。29-1项目有65+容器，需要2-3分钟。请耐心等待。

### Q2: DNS查询失败？
**A**: 等待3分钟让DNS服务器完全启动，然后重试。

### Q3: 端口8081/8082被占用？
**A**: 停止其他服务或修改docker-compose-roundcube.yml中的端口映射。

### Q4: 忘记密码？
**A**: 默认测试密码都是 `password123`

### Q5: 如何停止系统？
**A**: 
```bash
./manage_roundcube.sh stop
cd output && docker-compose down
```

### Q6: 如何清理所有数据？
**A**:
```bash
docker-compose down -v  # 删除volumes
docker network prune -f  # 清理网络
```

---

## 🎯 下一步学习

### 完成基础后
1. 查看`FINAL_PROJECT_SUMMARY.md`了解完整架构
2. 阅读`DNS_TESTING_GUIDE.md`（29-1）深入DNS
3. 尝试自定义配置文件
4. 开发自己的邮件应用

### 扩展阅读
- SEED Emulator官方文档
- Docker Mailserver文档
- Roundcube开发文档
- RFC 5321 (SMTP), RFC 3501 (IMAP)

---

**帮助**: 遇到问题请查看各项目的README.md  
**反馈**: 欢迎提交问题和改进建议

---

*祝学习愉快！* 🎉

