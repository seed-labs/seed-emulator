# 29项目演示教学指南

**项目**: SEED 基础邮件系统  
**适用**: 课堂演示、实验教学、自学实践

---

## 📋 教学流程总览

1. 用户创建与管理
2. 邮件发送测试
3. 邮件接收验证
4. Debug调试方法
5. 容器内部操作
6. 网络连通性测试
7. 端口服务测试

---

## 1️⃣ 用户创建与管理

### 方法1: 使用管理脚本（推荐）

```bash
cd /home/parallels/seed-email-system/examples/.not_ready_examples/29-email-system
./manage_roundcube.sh accounts
```

**输出示例**:
```
[SUCCESS] 创建 alice@seedemail.net
[SUCCESS] 创建 bob@seedemail.net
[SUCCESS] 创建 admin@corporate.local
[SUCCESS] 创建 info@smallbiz.org
```

### 方法2: 手动创建用户

```bash
# 格式: printf "密码\n密码\n" | docker exec -i 容器名 setup email add 邮箱

# 在seedemail.net创建用户
printf "password123\npassword123\n" | docker exec -i mail-150-seedemail setup email add alice@seedemail.net
printf "password123\npassword123\n" | docker exec -i mail-150-seedemail setup email add bob@seedemail.net

# 在corporate.local创建用户
printf "password123\npassword123\n" | docker exec -i mail-151-corporate setup email add admin@corporate.local
printf "password123\npassword123\n" | docker exec -i mail-151-corporate setup email add manager@corporate.local

# 在smallbiz.org创建用户
printf "password123\npassword123\n" | docker exec -i mail-152-smallbiz setup email add info@smallbiz.org
printf "password123\npassword123\n" | docker exec -i mail-152-smallbiz setup email add support@smallbiz.org
```

### 查看用户列表

```bash
# 查看seedemail.net的所有用户
docker exec mail-150-seedemail setup email list

# 查看corporate.local的所有用户
docker exec mail-151-corporate setup email list

# 查看smallbiz.org的所有用户
docker exec mail-152-smallbiz setup email list
```

**输出示例**:
```
* alice@seedemail.net ( 0 / ~ ) [0%]
* bob@seedemail.net ( 0 / ~ ) [0%]
```

### 删除用户

```bash
docker exec mail-150-seedemail setup email del alice@seedemail.net
```

---

## 2️⃣ 邮件发送测试

### 方法1: 使用sendmail命令

```bash
# 同域发送（seedemail.net内部）
echo "Subject: Test Email 1
From: alice@seedemail.net
To: bob@seedemail.net

This is a test email from alice to bob." | docker exec -i mail-150-seedemail sendmail bob@seedemail.net

# 跨域发送（seedemail.net → corporate.local）
echo "Subject: Cross-Domain Test
From: alice@seedemail.net
To: admin@corporate.local

This is a cross-domain email test." | docker exec -i mail-150-seedemail sendmail admin@corporate.local
```

### 方法2: 使用Roundcube Web界面

1. 访问 http://localhost:8081
2. 登录: alice@seedemail.net / password123
3. 点击"写邮件"
4. 填写收件人、主题、内容
5. 点击"发送"

---

## 3️⃣ 邮件接收验证

### 检查新邮件

```bash
# 查看bob的新邮件
docker exec mail-150-seedemail ls -lh /var/mail/seedemail.net/bob/new/

# 如果邮件已读，在cur目录
docker exec mail-150-seedemail ls -lh /var/mail/seedemail.net/bob/cur/
```

**输出示例**:
```
total 4.0K
-rw-r--r-- 1 docker docker 596 Oct  2 09:45 1759369529.M854067P1151.mail,S=596,W=612
```

### 读取邮件内容

```bash
# 读取邮件（替换文件名）
docker exec mail-150-seedemail cat /var/mail/seedemail.net/bob/new/1759369529.M854067P1151.mail,S=596,W=612
```

**输出示例**:
```
Return-Path: <root@mail.seedemail.net>
Delivered-To: bob@seedemail.net
From: alice@seedemail.net
To: bob@seedemail.net
Subject: Test Email

This is a test email from alice to bob.
```

### 使用Roundcube查看

1. 登录 http://localhost:8081
2. 使用 bob@seedemail.net / password123
3. 在收件箱中查看邮件

---

## 4️⃣ Debug调试方法

### 查看邮件队列

```bash
# 查看待发送邮件
docker exec mail-150-seedemail postqueue -p
```

**正常输出**: `Mail queue is empty`  
**有问题输出**: 显示卡在队列中的邮件

### 强制发送队列邮件

```bash
docker exec mail-150-seedemail postqueue -f
```

### 查看邮件服务器日志

```bash
# 实时查看日志
docker logs mail-150-seedemail -f

# 查看最近日志
docker exec mail-150-seedemail tail -50 /var/log/mail/mail.log

# 搜索特定内容
docker exec mail-150-seedemail grep "alice@seedemail.net" /var/log/mail/mail.log
```

### 检查服务状态

```bash
# 进入容器
docker exec -it mail-150-seedemail /bin/bash

# 检查Postfix状态
postfix status

# 检查Dovecot状态
doveadm service status

# 退出容器
exit
```

---

## 5️⃣ 进入容器操作

### 进入邮件服务器容器

```bash
# 进入seedemail服务器
docker exec -it mail-150-seedemail /bin/bash

# 进入corporate服务器
docker exec -it mail-151-corporate /bin/bash

# 进入smallbiz服务器
docker exec -it mail-152-smallbiz /bin/bash
```

### 容器内常用命令

```bash
# 查看邮件目录
ls -la /var/mail/seedemail.net/

# 查看配置文件
cat /etc/postfix/main.cf

# 查看日志
tail -f /var/log/mail/mail.log

# 测试SMTP端口
telnet localhost 25

# 测试IMAP端口
telnet localhost 143
```

### 进入客户端容器

```bash
# 进入AS-160的host_0
docker exec -it as160h-host_0-10.160.0.71 /bin/bash

# 安装邮件测试工具
apt update && apt install -y swaks telnet dnsutils

# 测试发送邮件
swaks --to bob@seedemail.net \
      --from alice@seedemail.net \
      --server 10.150.0.10:25 \
      --body "Test from client container"
```

---

## 6️⃣ 网络连通性测试

### 测试邮件服务器之间的连通性

```bash
# 从AS-150网络ping AS-151邮件服务器
docker exec as150h-host_0-10.150.0.71 ping -c 3 10.151.0.10

# 从AS-160客户端ping seedemail服务器
docker exec as160h-host_0-10.160.0.71 ping -c 3 10.150.0.10
```

**预期结果**: 
```
64 bytes from 10.150.0.10: icmp_seq=1 ttl=63 time=0.123 ms
3 packets transmitted, 3 received, 0% packet loss
```

### 跟踪路由路径

```bash
# 查看从AS-160到AS-151的路由路径
docker exec as160h-host_0-10.160.0.71 traceroute 10.151.0.10
```

**输出示例**:
```
1  10.160.0.254 (10.160.0.254)  0.123 ms
2  10.100.0.2 (10.100.0.2)  0.234 ms
3  10.151.0.10 (10.151.0.10)  0.345 ms
```

### 检查路由表

```bash
# 查看AS-150路由器的路由表
docker exec as150brd-router0-10.150.0.254 ip route

# 查看BGP路由
docker exec as150brd-router0-10.150.0.254 birdc show route
```

---

## 7️⃣ 端口服务测试

### 测试SMTP端口（25）

```bash
# 从宿主机测试
telnet localhost 2525

# 从容器内测试
docker exec as160h-host_0-10.160.0.71 telnet 10.150.0.10 25
```

**预期输出**:
```
220 mail.seedemail.net ESMTP Postfix
```

**手动SMTP对话**:
```
EHLO test.com
MAIL FROM:<alice@seedemail.net>
RCPT TO:<bob@seedemail.net>
DATA
Subject: Manual SMTP Test

Test email body.
.
QUIT
```

### 测试IMAP端口（143）

```bash
# 从宿主机测试
telnet localhost 1430

# 从容器内测试
docker exec as160h-host_0-10.160.0.71 telnet 10.150.0.10 143
```

**预期输出**:
```
* OK [CAPABILITY IMAP4rev1...] Dovecot ready.
```

**手动IMAP对话**:
```
a1 LOGIN alice@seedemail.net password123
a2 LIST "" "*"
a3 SELECT INBOX
a4 FETCH 1 BODY[]
a5 LOGOUT
```

### 端口扫描

```bash
# 安装nmap
docker exec as160h-host_0-10.160.0.71 apt update && apt install -y nmap

# 扫描邮件服务器端口
docker exec as160h-host_0-10.160.0.71 nmap -p 25,143,587,993 10.150.0.10
```

**输出示例**:
```
PORT    STATE SERVICE
25/tcp  open  smtp
143/tcp open  imap
587/tcp open  submission
993/tcp open  imaps
```

---

## 🎓 教学场景示例

### 场景1: 演示基本邮件收发

```bash
# 1. 创建两个用户
printf "demo123\ndemo123\n" | docker exec -i mail-150-seedemail setup email add teacher@seedemail.net
printf "demo123\ndemo123\n" | docker exec -i mail-150-seedemail setup email add student@seedemail.net

# 2. 发送邮件
echo "Subject: Welcome to Class
From: teacher@seedemail.net
To: student@seedemail.net

Welcome to the email system lab!" | docker exec -i mail-150-seedemail sendmail student@seedemail.net

# 3. 验证接收
docker exec mail-150-seedemail ls /var/mail/seedemail.net/student/new/

# 4. 读取邮件
docker exec mail-150-seedemail cat /var/mail/seedemail.net/student/new/*
```

### 场景2: 演示跨域邮件

```bash
# 1. 从seedemail发送到corporate
echo "Subject: Inter-domain Test
From: alice@seedemail.net
To: admin@corporate.local

Cross-domain email routing test." | docker exec -i mail-150-seedemail sendmail admin@corporate.local

# 2. 检查邮件队列
docker exec mail-150-seedemail postqueue -p

# 3. 验证送达
docker exec mail-151-corporate ls /var/mail/corporate.local/admin/new/
```

### 场景3: 演示SMTP协议

```bash
# 进入客户端容器
docker exec -it as160h-host_0-10.160.0.71 /bin/bash

# 手动SMTP会话
telnet 10.150.0.10 25
# 输入:
EHLO client.test
MAIL FROM:<test@test.com>
RCPT TO:<alice@seedemail.net>
DATA
Subject: Protocol Demo

This demonstrates SMTP protocol.
.
QUIT
```

---

## 🔍 常见问题排查

### 问题1: 邮件未送达

**排查步骤**:
```bash
# 1. 检查发件人邮件队列
docker exec mail-150-seedemail postqueue -p

# 2. 查看日志
docker exec mail-150-seedemail tail -50 /var/log/mail/mail.log

# 3. 检查收件人账户是否存在
docker exec mail-150-seedemail setup email list | grep bob

# 4. 检查网络连通性
docker exec mail-150-seedemail ping -c 2 10.151.0.10
```

### 问题2: 容器无法访问

```bash
# 查看所有容器
docker ps -a | grep mail

# 查看容器日志
docker logs mail-150-seedemail

# 重启容器
cd output && docker-compose restart mail-150-seedemail
```

### 问题3: 端口连接失败

```bash
# 检查端口映射
docker port mail-150-seedemail

# 从宿主机测试
telnet localhost 2525
telnet localhost 1430

# 检查防火墙
sudo ufw status
```

---

## 📊 实验数据记录表

### 邮件发送测试记录

| 发件人 | 收件人 | 服务器 | 结果 | 时间 | 备注 |
|--------|--------|--------|------|------|------|
| alice@seedemail.net | bob@seedemail.net | mail-150 | ✅ | <1秒 | 同域 |
| alice@seedemail.net | admin@corporate.local | mail-150→151 | ✅ | <5秒 | 跨域 |
| bob@seedemail.net | info@smallbiz.org | mail-150→152 | ✅ | <5秒 | 跨域 |

### 端口测试记录

| 服务器 | 端口 | 服务 | 状态 | 测试命令 |
|--------|------|------|------|---------|
| mail-150-seedemail | 2525 | SMTP | ✅ | `telnet localhost 2525` |
| mail-150-seedemail | 1430 | IMAP | ✅ | `telnet localhost 1430` |
| mail-151-corporate | 2526 | SMTP | ✅ | `telnet localhost 2526` |
| mail-151-corporate | 1431 | IMAP | ✅ | `telnet localhost 1431` |

---

## 💡 教学Tips

### Tip 1: 使用tmux分屏演示

```bash
# 安装tmux
sudo apt install tmux

# 左侧：实时日志
docker logs mail-150-seedemail -f

# 右侧：执行命令
docker exec -it mail-150-seedemail /bin/bash
```

### Tip 2: 保存抓包供分析

```bash
# 抓取SMTP流量
docker exec as150h-host_0-10.150.0.71 tcpdump -i any port 25 -w /tmp/smtp.pcap

# 下载到宿主机
docker cp as150h-host_0-10.150.0.71:/tmp/smtp.pcap ./smtp.pcap

# 用Wireshark分析
wireshark smtp.pcap
```

### Tip 3: 批量创建测试用户

```bash
for user in user1 user2 user3 user4 user5; do
    printf "password123\npassword123\n" | docker exec -i mail-150-seedemail setup email add ${user}@seedemail.net
done
```

---

## 📝 完整演示脚本

```bash
#!/bin/bash
# 29项目完整演示脚本

echo "=== SEED邮件系统演示开始 ==="

echo -e "\n1. 创建测试用户"
printf "demo123\ndemo123\n" | docker exec -i mail-150-seedemail setup email add demo1@seedemail.net
printf "demo123\ndemo123\n" | docker exec -i mail-150-seedemail setup email add demo2@seedemail.net

echo -e "\n2. 查看用户列表"
docker exec mail-150-seedemail setup email list

echo -e "\n3. 发送测试邮件"
echo "Subject: Demo Email
From: demo1@seedemail.net
To: demo2@seedemail.net

This is a demonstration email." | docker exec -i mail-150-seedemail sendmail demo2@seedemail.net

echo -e "\n4. 等待邮件送达"
sleep 5

echo -e "\n5. 检查收件箱"
docker exec mail-150-seedemail ls -lh /var/mail/seedemail.net/demo2/new/

echo -e "\n6. 读取邮件内容"
docker exec mail-150-seedemail cat /var/mail/seedemail.net/demo2/new/*

echo -e "\n=== 演示完成 ==="
```

---

## 🎯 学习目标检查清单

完成本实验后，学生应该能够：

- [ ] 使用docker exec创建邮件账户
- [ ] 使用sendmail命令发送邮件
- [ ] 查看邮件队列和日志
- [ ] 理解SMTP/IMAP协议基础
- [ ] 使用Roundcube收发邮件
- [ ] 进入容器进行调试
- [ ] 测试网络连通性
- [ ] 测试端口服务
- [ ] 分析邮件头部信息
- [ ] 理解跨域邮件路由

---

**编写**: SEED Lab Team  
**更新**: 2025-10-02  
**用途**: 教学演示、实验指导

