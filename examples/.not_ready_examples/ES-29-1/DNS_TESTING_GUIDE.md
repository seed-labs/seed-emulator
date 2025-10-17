# 29-1项目 DNS功能测试指南

**项目**: SEED 邮件系统 - 真实版 (29-1-email-system)  
**核心特性**: 完整的DNS层次结构与MX记录  
**日期**: 2025-10-02

---

## 📋 DNS架构概览

### DNS层次结构

```
Root DNS (.)
    ├── a-root-server (10.150.0.71)  AS-150 host_0
    └── b-root-server (10.150.0.72)  AS-150 host_1

TLD DNS
    ├── .com (10.150.0.73)  AS-150 host_2
    ├── .net (10.150.0.75)  AS-150 host_4
    └── .cn  (10.150.0.76)  AS-150 host_5

邮件域DNS
    ├── qq.com      (10.200.0.71)  AS-200 host_0
    ├── 163.com     (10.201.0.71)  AS-201 host_0
    ├── gmail.com   (10.202.0.71)  AS-202 host_0
    ├── outlook.com (10.203.0.71)  AS-203 host_0
    ├── company.cn  (10.150.0.74)  AS-150 host_3
    └── startup.net (10.205.0.71)  AS-205 host_0

DNS Cache
    └── Local DNS Cache (10.150.0.53)  AS-150 dns-cache
```

### MX记录配置

| 域名 | MX记录 | 邮件服务器IP |
|------|--------|-------------|
| qq.com | mail.qq.com | 10.200.0.10 |
| 163.com | mail.163.com | 10.201.0.10 |
| gmail.com | mail.gmail.com | 10.202.0.10 |
| outlook.com | mail.outlook.com | 10.203.0.10 |
| company.cn | mail.company.cn | 10.204.0.10 |
| startup.net | mail.startup.net | 10.205.0.10 |

---

## 🧪 DNS测试步骤

### 测试1: DNS缓存服务器连通性

```bash
# 进入DNS缓存服务器容器
docker exec -it as150h-dns-cache-10.150.0.53 /bin/bash

# 测试本地DNS服务
nslookup localhost
```

**预期结果**: 应该返回127.0.0.1

### 测试2: 测试域名A记录解析

```bash
# 在DNS缓存服务器中测试
docker exec as150h-dns-cache-10.150.0.53 nslookup qq.com

# 在其他容器中测试（所有容器都配置了DNS）
docker exec as151h-host_0-10.151.0.71 nslookup gmail.com
docker exec as152h-host_0-10.152.0.71 nslookup 163.com
```

**预期结果**:
```
Server:         10.150.0.53
Address:        10.150.0.53#53

Name:   qq.com
Address: 10.200.0.10
```

### 测试3: 测试MX记录

```bash
# 测试QQ邮箱MX记录
docker exec as150h-dns-cache-10.150.0.53 nslookup -type=mx qq.com

# 测试Gmail MX记录
docker exec as150h-dns-cache-10.150.0.53 nslookup -type=mx gmail.com

# 测试163邮箱MX记录
docker exec as150h-dns-cache-10.150.0.53 nslookup -type=mx 163.com
```

**预期结果**:
```
qq.com  mail exchanger = 10 mail.qq.com.
mail.qq.com     internet address = 10.200.0.10
```

### 测试4: 使用dig命令详细查询

```bash
# 安装dig工具（如果没有）
docker exec as150h-dns-cache-10.150.0.53 apt-get update -qq && apt-get install -y dnsutils >/dev/null 2>&1

# 查询qq.com的所有记录
docker exec as150h-dns-cache-10.150.0.53 dig @10.150.0.53 qq.com ANY

# 查询MX记录
docker exec as150h-dns-cache-10.150.0.53 dig @10.150.0.53 qq.com MX

# 跟踪DNS解析路径
docker exec as150h-dns-cache-10.150.0.53 dig @10.150.0.53 qq.com +trace
```

### 测试5: 从邮件服务器测试DNS

```bash
# 从QQ邮件服务器测试
docker exec mail-qq-tencent nslookup gmail.com

# 从Gmail服务器测试  
docker exec mail-gmail-google nslookup qq.com

# 测试跨域解析
docker exec mail-163-netease nslookup outlook.com
```

---

## 🔍 故障排除

### 问题1: DNS查询返回SERVFAIL

**可能原因**:
- DNS服务器尚未完全启动
- Root DNS服务器未运行
- 网络路由未完全收敛

**解决方案**:
```bash
# 等待2-3分钟让所有服务启动
sleep 180

# 检查Root DNS服务器
docker exec as150h-host_0-10.150.0.71 ps aux | grep named

# 检查DNS缓存服务器
docker exec as150h-dns-cache-10.150.0.53 ps aux | grep named

# 重启DNS服务（如果需要）
docker restart as150h-dns-cache-10.150.0.53
```

### 问题2: DNS服务器进程未运行

**检查方法**:
```bash
# 检查容器启动日志
docker logs as150h-host_0-10.150.0.71 | grep -i error
docker logs as150h-dns-cache-10.150.0.53 | grep -i error

# 手动启动named服务
docker exec as150h-host_0-10.150.0.71 service named start
```

### 问题3: 网络不通

**检查连通性**:
```bash
# 从dns-cache ping Root DNS
docker exec as150h-dns-cache-10.150.0.53 ping -c 2 10.150.0.71

# 从dns-cache ping .com TLD
docker exec as150h-dns-cache-10.150.0.53 ping -c 2 10.150.0.73

# 检查路由
docker exec as150h-dns-cache-10.150.0.53 ip route
```

---

## 📝 Web界面DNS测试

访问 http://localhost:8080/map.html 可以看到网络拓扑，包括DNS服务器的分布。

也可以通过Web管理界面（如果启动了）：
```bash
cd /home/parallels/seed-email-system/examples/.not_ready_examples/29-1-email-system
./start_webmail.sh  # 如果有这个脚本
# 访问 http://localhost:5001
```

---

## 🎯 完整测试流程（推荐）

```bash
# 步骤1: 等待系统完全启动（重要！）
echo "等待DNS和BGP收敛..."
sleep 180

# 步骤2: 测试DNS基本功能
echo "=== 测试DNS A记录 ==="
docker exec as150h-dns-cache-10.150.0.53 nslookup qq.com
docker exec as150h-dns-cache-10.150.0.53 nslookup gmail.com
docker exec as150h-dns-cache-10.150.0.53 nslookup 163.com

# 步骤3: 测试MX记录
echo -e "\n=== 测试MX记录 ==="
docker exec as150h-dns-cache-10.150.0.53 nslookup -type=mx qq.com
docker exec as150h-dns-cache-10.150.0.53 nslookup -type=mx gmail.com

# 步骤4: 从不同节点测试DNS
echo -e "\n=== 从不同AS测试DNS ==="
docker exec as151h-host_0-10.151.0.71 nslookup qq.com
docker exec as152h-host_0-10.152.0.71 nslookup gmail.com

# 步骤5: 测试邮件服务器的DNS解析
echo -e "\n=== 邮件服务器DNS测试 ==="
docker exec mail-qq-tencent nslookup gmail.com
docker exec mail-gmail-google nslookup qq.com
```

---

## 📧 结合邮件功能测试

### 测试跨域邮件（依赖DNS）

```bash
# 创建测试账户
printf "password123\npassword123\n" | docker exec -i mail-qq-tencent setup email add user@qq.com
printf "password123\npassword123\n" | docker exec -i mail-gmail-google setup email add user@gmail.com

# 发送跨域邮件（QQ → Gmail）
echo "Subject: DNS Test Email
From: user@qq.com
To: user@gmail.com

This is a test email to verify DNS-based mail routing." | docker exec -i mail-qq-tencent sendmail user@gmail.com

# 等待邮件送达
sleep 10

# 检查Gmail是否收到
docker exec mail-gmail-google ls -lh /var/mail/gmail.com/user/new/
```

---

## 💡 DNS知识点

### DNS解析过程

1. **本地查询**: 客户端 → Local DNS Cache (10.150.0.53)
2. **Root查询**: DNS Cache → Root DNS (10.150.0.71/72)
3. **TLD查询**: Root → TLD DNS (.com: 10.150.0.73)
4. **权威查询**: TLD → 权威DNS (qq.com: 10.200.0.71)
5. **返回结果**: 权威DNS → TLD → Root → Cache → 客户端

### MX记录作用

MX记录告诉发件服务器应该将邮件发送到哪个服务器：
- `qq.com MX 10 mail.qq.com.`
- `mail.qq.com A 10.200.0.10`

邮件服务器会：
1. 查询收件人域名的MX记录
2. 解析MX记录指向的主机名
3. 连接到该IP地址发送邮件

---

## 🚨 已知问题

### DNS启动延迟

DNS服务器需要较长时间启动（2-3分钟）。请耐心等待并多次重试。

### DNS缓存问题

如果DNS查询失败，尝试：
```bash
# 重启DNS缓存服务器
docker restart as150h-dns-cache-10.150.0.53

# 等待30秒
sleep 30

# 重新测试
docker exec as150h-dns-cache-10.150.0.53 nslookup qq.com
```

---

## 📊 验收标准

### DNS功能验收

- ✅ A记录解析成功（qq.com → 10.200.0.10）
- ✅ MX记录查询成功
- ✅ 所有6个邮件域都可解析
- ✅ 跨AS的DNS查询正常
- ✅ 邮件服务器可通过DNS互相找到对方

### 邮件功能验收（依赖DNS）

- ✅ 跨域邮件发送成功
- ✅ MX记录路由正确
- ✅ 邮件送达正确的服务器

---

**更新**: 2025-10-02  
**状态**: DNS已配置，等待服务启动和测试验证

