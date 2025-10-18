# B29 项目演示教学指南

**项目**: SEED 真实邮件系统 + DNS  
**核心特性**: 完整DNS层次结构、MX记录、真实服务商模拟  
**适用**: DNS教学、网络协议进阶、真实互联网模拟

---

## 范围与状态（Scope & Status）

- 本指南适用于 `examples/internet/B29_email_dns/`（B29）。
- 更早的 `29`、`29-1` 为历史草稿，不维护、不用于演示。

---

## 📋 教学流程总览

1. 用户创建与管理（6个服务商）
2. **DNS解析测试**（核心）
3. **MX记录查询**（核心）
4. 邮件发送测试（域内）
5. Debug调试方法
6. 进入容器操作
7. 网络连通性测试
8. BGP路由观察

---

## 1️⃣ 用户创建与管理

### 使用管理脚本创建（推荐）

```bash
cd /home/parallels/seed-email-system/examples/internet/B29_email_dns
./manage_roundcube.sh accounts
```

**输出**:
```
[SUCCESS] 创建 user@qq.com
[SUCCESS] 创建 user@163.com  
[SUCCESS] 创建 user@gmail.com
[SUCCESS] 创建 user@outlook.com
[SUCCESS] 创建 admin@company.cn
[SUCCESS] 创建 founder@startup.net
```

### 手动创建用户（各服务商）

```bash
# QQ邮箱
printf "password123\npassword123\n" | docker exec -i mail-qq-tencent setup email add zhangsan@qq.com
printf "password123\npassword123\n" | docker exec -i mail-qq-tencent setup email add lisi@qq.com

# 163邮箱
printf "password123\npassword123\n" | docker exec -i mail-163-netease setup email add wangwu@163.com

# Gmail
printf "password123\npassword123\n" | docker exec -i mail-gmail-google setup email add john@gmail.com

# Outlook  
printf "password123\npassword123\n" | docker exec -i mail-outlook-microsoft setup email add mike@outlook.com

# 企业邮箱
printf "password123\npassword123\n" | docker exec -i mail-company-aliyun setup email add hr@company.cn

# 自建邮箱
printf "password123\npassword123\n" | docker exec -i mail-startup-selfhosted setup email add cto@startup.net
```

### 查看用户列表

```bash
# 查看各服务商用户
docker exec mail-qq-tencent setup email list
docker exec mail-gmail-google setup email list
docker exec mail-163-netease setup email list
```

---

## 2️⃣ DNS解析测试（核心特性）

### 测试A记录解析

```bash
# 从DNS缓存服务器测试
docker exec as150h-dns-cache-10.150.0.53 nslookup qq.com
docker exec as150h-dns-cache-10.150.0.53 nslookup gmail.com
docker exec as150h-dns-cache-10.150.0.53 nslookup 163.com
docker exec as150h-dns-cache-10.150.0.53 nslookup outlook.com
docker exec as150h-dns-cache-10.150.0.53 nslookup company.cn
docker exec as150h-dns-cache-10.150.0.53 nslookup startup.net
```

**预期输出** (以qq.com为例):
```
Server:         10.150.0.53
Address:        10.150.0.53#53

Non-authoritative answer:
Name:   qq.com
Address: 10.200.0.10
```

### 从不同AS测试DNS

```bash
# 从AS-151（上海用户）测试
docker exec as151h-host_0-10.151.0.71 nslookup qq.com

# 从AS-152（广州用户）测试
docker exec as152h-host_0-10.152.0.71 nslookup gmail.com

# 从AS-153（企业用户）测试
docker exec as153h-host_0-10.153.0.71 nslookup 163.com
```

**教学要点**: 演示时优先在“各提供商所在 AS 的本地缓存（10.{ASN}.0.53）”内查询（`nslookup ... 127.0.0.1`）。中央缓存（10.150.0.53）在某些 BGP 拓扑下可能对远端权威 NS 不可达而返回 `SERVFAIL`。

---

## 3️⃣ MX记录查询（核心特性）

### 查询各域的MX记录

```bash
# QQ邮箱MX记录
docker exec as150h-dns-cache-10.150.0.53 nslookup -type=mx qq.com

# Gmail MX记录
docker exec as150h-dns-cache-10.150.0.53 nslookup -type=mx gmail.com

# 163邮箱MX记录
docker exec as150h-dns-cache-10.150.0.53 nslookup -type=mx 163.com

# Outlook MX记录
docker exec as150h-dns-cache-10.150.0.53 nslookup -type=mx outlook.com

# 企业邮箱MX记录
docker exec as150h-dns-cache-10.150.0.53 nslookup -type=mx company.cn

# 自建邮箱MX记录
docker exec as150h-dns-cache-10.150.0.53 nslookup -type=mx startup.net
```

> 提示：对 `company.cn` 与 `startup.net`，更稳妥的做法是在各自 AS 的本地缓存内查询：
> - `docker exec as204h-dns-cache-10.204.0.53 nslookup -type=mx company.cn 127.0.0.1`
> - `docker exec as205h-dns-cache-10.205.0.53 nslookup -type=mx startup.net 127.0.0.1`

**预期输出** (以qq.com为例):
```
qq.com  mail exchanger = 10 mail.qq.com.

Authoritative answers can be found from:
mail.qq.com     internet address = 10.200.0.10
```

### 使用dig命令详细查询

```bash
# 安装dig工具（如需要）
docker exec as150h-dns-cache-10.150.0.53 apt-get update -qq && apt-get install -y dnsutils >/dev/null 2>&1

# 查询MX记录
docker exec as150h-dns-cache-10.150.0.53 dig @10.150.0.53 qq.com MX

# 跟踪DNS解析路径
docker exec as150h-dns-cache-10.150.0.53 dig @10.150.0.53 qq.com +trace
```

**+trace输出解析**:
```
. → Root DNS (10.150.0.71)
com. → .com TLD (10.150.0.73)  
qq.com. → qq.com权威DNS (10.200.0.71)
最终: qq.com → 10.200.0.10
```

---

## 4️⃣ 邮件发送测试（域内）

### QQ域内邮件

```bash
# 创建QQ账户
printf "password123\npassword123\n" | docker exec -i mail-qq-tencent setup email add alice@qq.com
printf "password123\npassword123\n" | docker exec -i mail-qq-tencent setup email add bob@qq.com

# 发送域内邮件
echo "Subject: QQ Internal Email
From: alice@qq.com
To: bob@qq.com

QQ domain internal email test." | docker exec -i mail-qq-tencent sendmail bob@qq.com

# 验证送达
sleep 5
docker exec mail-qq-tencent ls -lh /var/mail/qq.com/bob/new/
```

### Gmail域内邮件

```bash
# 创建Gmail账户
printf "password123\npassword123\n" | docker exec -i mail-gmail-google setup email add alice@gmail.com
printf "password123\npassword123\n" | docker exec -i mail-gmail-google setup email add bob@gmail.com

# 发送邮件
echo "Subject: Gmail Internal
From: alice@gmail.com
To: bob@gmail.com

Gmail internal test." | docker exec -i mail-gmail-google sendmail bob@gmail.com

# 验证
docker exec mail-gmail-google ls -lh /var/mail/gmail.com/bob/new/
```

---

## 5️⃣ Debug调试方法

### 查看DNS服务器状态

```bash
# 检查DNS缓存服务器进程
docker exec as150h-dns-cache-10.150.0.53 ps aux | grep named

# 检查Root DNS服务器
docker exec as150h-host_0-10.150.0.71 ps aux | grep named

# 查看DNS日志
docker logs as150h-dns-cache-10.150.0.53
docker logs as150h-host_0-10.150.0.71
```

### 查看邮件队列和日志

```bash
# QQ邮件队列
docker exec mail-qq-tencent postqueue -p

# Gmail邮件日志
docker exec mail-gmail-google tail -50 /var/log/mail/mail.log

# 163邮件日志
docker exec mail-163-netease tail -50 /var/log/mail/mail.log
```

### 测试DNS解析问题

```bash
# 检查/etc/resolv.conf
docker exec as150h-dns-cache-10.150.0.53 cat /etc/resolv.conf

# 直接查询Root DNS
docker exec as150h-dns-cache-10.150.0.53 nslookup . 10.150.0.71

# 查询TLD DNS
docker exec as150h-dns-cache-10.150.0.53 nslookup com. 10.150.0.73

# 查询权威DNS
docker exec as150h-dns-cache-10.150.0.53 nslookup qq.com 10.200.0.71
```

---

## 6️⃣ 进入容器操作

### 进入DNS缓存服务器

```bash
docker exec -it as150h-dns-cache-10.150.0.53 /bin/bash

# 查看BIND配置
cat /etc/bind/named.conf
cat /etc/bind/named.conf.options
cat /etc/bind/db.root

# 查看DNS缓存
rndc dumpdb -cache
cat /var/cache/bind/named_dump.db | grep qq.com

# 测试递归查询
nslookup qq.com localhost
```

### 进入Root DNS服务器

```bash
docker exec -it as150h-host_0-10.150.0.71 /bin/bash

# 查看zone文件
ls /etc/bind/zones/

# 查看root zone
cat /etc/bind/zones/root

# 重启named
service named restart
```

### 进入邮件服务器容器

```bash
# 进入QQ邮件服务器
docker exec -it mail-qq-tencent /bin/bash

# 查看DNS配置
cat /etc/resolv.conf
cat /etc/hosts | grep gmail

# 测试DNS解析
nslookup gmail.com

# 查看Postfix配置
postconf | grep transport
cat /etc/postfix/transport

# 测试SMTP连接
telnet 10.202.0.10 25
```

---

## 7️⃣ 网络连通性测试

### 测试跨AS连通性

```bash
# AS-150（北京）→ AS-200（QQ,广州）
docker exec as150h-host_0-10.150.0.71 ping -c 3 10.200.0.71

# AS-150（北京）→ AS-202（Gmail,海外）
docker exec as150h-host_0-10.150.0.71 ping -c 3 10.202.0.71

# AS-200（QQ）→ AS-202（Gmail）
docker exec as200h-host_0-10.200.0.71 ping -c 3 10.202.0.71
```

**预期结果**: TTL约60左右（经过多跳路由）

### 路由跟踪

```bash
# 从北京用户到Gmail的路由路径
docker exec as150h-host_0-10.150.0.71 traceroute 10.202.0.10
```

**典型路径**:
```
1  10.150.0.254 (AS-150路由器)
2  10.100.0.2 (AS-2 Transit)
3  10.103.0.2 (IX-103)
4  10.202.0.254 (AS-202路由器)
5  10.202.0.10 (Gmail服务器)
```

### 测试邮件服务器连通性

```bash
# 从QQ服务器ping其他服务器
docker exec mail-qq-tencent ping -c 2 10.201.0.10  # 163
docker exec mail-qq-tencent ping -c 2 10.202.0.10  # Gmail
docker exec mail-qq-tencent ping -c 2 10.203.0.10  # Outlook
```

---

## 8️⃣ DNS记录测试（核心）

### DNS层次结构测试

```bash
echo "=== 1. 测试Root DNS ==="
docker exec as150h-dns-cache-10.150.0.53 nslookup -type=ns . 10.150.0.71

echo -e "\n=== 2. 测试.com TLD ==="
docker exec as150h-dns-cache-10.150.0.53 nslookup -type=ns com. 10.150.0.73

echo -e "\n=== 3. 测试qq.com权威DNS ==="
docker exec as150h-dns-cache-10.150.0.53 nslookup -type=ns qq.com 10.200.0.71

echo -e "\n=== 4. 完整递归查询 ==="
docker exec as150h-dns-cache-10.150.0.53 nslookup qq.com
```

### DNS服务器分布验证

```bash
# Root DNS服务器（AS-150）
echo "=== Root DNS Servers ==="
docker exec as150h-host_0-10.150.0.71 hostname -I  # a-root-server
docker exec as150h-host_1-10.150.0.72 hostname -I  # b-root-server

# TLD DNS服务器（AS-150）
echo -e "\n=== TLD DNS Servers ==="
docker exec as150h-host_2-10.150.0.73 hostname -I  # .com
docker exec as150h-host_3-10.150.0.74 hostname -I  # .net
docker exec as150h-host_4-10.150.0.75 hostname -I  # .cn

# 邮件域DNS服务器（各自AS）
echo -e "\n=== Mail Domain DNS Servers ==="
docker exec as200h-host_0-10.200.0.71 hostname -I  # qq.com
docker exec as201h-host_0-10.201.0.71 hostname -I  # 163.com
docker exec as202h-host_0-10.202.0.71 hostname -I  # gmail.com
```

### MX记录详细测试

```bash
# 完整MX记录测试
for domain in qq.com 163.com gmail.com outlook.com company.cn startup.net; do
    echo "=== MX记录: $domain ==="
    docker exec as150h-dns-cache-10.150.0.53 nslookup -type=mx $domain
    echo ""
done
```

**测试记录表**:

| 域名 | MX记录 | 邮件服务器IP | 验证结果 |
|------|--------|-------------|---------|
| qq.com | mail.qq.com (优先级10) | 10.200.0.10 | ✅ |
| 163.com | mail.163.com (优先级10) | 10.201.0.10 | ✅ |
| gmail.com | mail.gmail.com (优先级10) | 10.202.0.10 | ✅ |
| outlook.com | mail.outlook.com (优先级10) | 10.203.0.10 | ✅ |
| company.cn | mail.company.cn (优先级10) | 10.204.0.10 | ✅ |
| startup.net | mail.startup.net (优先级10) | 10.205.0.10 | ✅ |

---

## 9️⃣ BGP路由观察

### 查看BGP会话状态

```bash
# AS-2 (中国电信) BGP状态
docker exec as2brd-r100-10.100.0.2 birdc show protocols | grep bgp

# AS-150路由器BGP状态
docker exec as150brd-router0-10.150.0.254 birdc show protocols
```

### 查看BGP路由表

```bash
# 查看AS-150学习到的所有路由
docker exec as150brd-router0-10.150.0.254 birdc show route

# 查看到QQ邮箱的路由
docker exec as150brd-router0-10.150.0.254 birdc show route for 10.200.0.0/24

# 查看到Gmail的路由
docker exec as150brd-router0-10.150.0.254 birdc show route for 10.202.0.0/24
```

**输出示例**:
```
10.200.0.0/24    unicast [u_as2 04:29:55.082] * (100) [AS200i]
    via 10.100.0.2 on ix100
```

**解读**: 通过AS-2（电信）到达AS-200（QQ）

---

### ⚠️ 已知限制：AS-204（company.cn）↔ AS-205（startup.net）

- 在当前多 IX + iBGP/IGP 配置下，AS-2 内部 r100 未形成 OSPF 邻居，部分 iBGP 邻居 Active，且 AS-205↔AS-2 的私有对等在 r100 侧未完全匹配，导致 204↔205 互通失败。
- 课堂演示建议聚焦 QQ/163/Gmail/Outlook 四个提供商（6 条跨域全部通过）。
- 详细分析与规避方案见：
  - `README.md` → “Known Issue: AS-204 (company.cn) ↔ AS-205 (startup.net) BGP reachability”
  - `docs/bgp_audit.md`

---

## 🔟 端口服务测试

### 从宿主机测试端口

```bash
# 测试QQ邮箱
telnet localhost 2200  # SMTP
telnet localhost 1400  # IMAP

# 测试Gmail
telnet localhost 2202  # SMTP
telnet localhost 1402  # IMAP

# 测试163
telnet localhost 2201  # SMTP
telnet localhost 1401  # IMAP
```

### 从容器内测试端口

```bash
# 进入用户容器
docker exec -it as150h-host_0-10.150.0.71 /bin/bash

# 测试QQ邮件服务器端口
telnet 10.200.0.10 25   # SMTP
telnet 10.200.0.10 143  # IMAP

# 测试Gmail邮件服务器端口
telnet 10.202.0.10 25   # SMTP
telnet 10.202.0.10 143  # IMAP
```

---

## 📝 完整演示脚本（B29）

```bash
#!/bin/bash
# 29-1项目完整演示脚本 - 重点展示DNS功能

echo "========================================="
echo "SEED 真实邮件系统 + DNS 演示"
echo "========================================="

echo -e "\n【第1部分: DNS解析测试】"
echo "-------------------------------------------"

echo "1.1 测试Root DNS"
docker exec as150h-dns-cache-10.150.0.53 nslookup -type=ns . 10.150.0.71

echo -e "\n1.2 测试TLD DNS (.com)"
docker exec as150h-dns-cache-10.150.0.53 nslookup -type=ns com. 10.150.0.73

echo -e "\n1.3 测试qq.com解析"
docker exec as150h-dns-cache-10.150.0.53 nslookup qq.com

echo -e "\n1.4 测试gmail.com解析"
docker exec as150h-dns-cache-10.150.0.53 nslookup gmail.com

echo -e "\n【第2部分: MX记录测试】"
echo "-------------------------------------------"

echo "2.1 查询qq.com MX记录"
docker exec as150h-dns-cache-10.150.0.53 nslookup -type=mx qq.com

echo -e "\n2.2 查询gmail.com MX记录"
docker exec as150h-dns-cache-10.150.0.53 nslookup -type=mx gmail.com

echo -e "\n【第3部分: 网络连通性测试】"
echo "-------------------------------------------"

echo "3.1 北京用户 → QQ服务器（广州）"
docker exec as150h-host_0-10.150.0.71 ping -c 2 10.200.0.71

echo -e "\n3.2 北京用户 → Gmail服务器（海外）"
docker exec as150h-host_0-10.150.0.71 ping -c 2 10.202.0.71

echo -e "\n【第4部分: BGP路由测试】"
echo "-------------------------------------------"

echo "4.1 查看到QQ的路由"
docker exec as150brd-router0-10.150.0.254 birdc show route for 10.200.0.0/24

echo -e "\n4.2 查看到Gmail的路由"
docker exec as150brd-router0-10.150.0.254 birdc show route for 10.202.0.0/24

echo -e "\n【第5部分: 邮件功能测试】"
echo "-------------------------------------------"

echo "5.1 QQ域内邮件发送"
printf "demo123\ndemo123\n" | docker exec -i mail-qq-tencent setup email add test1@qq.com
printf "demo123\ndemo123\n" | docker exec -i mail-qq-tencent setup email add test2@qq.com

echo "From: test1@qq.com
To: test2@qq.com
Subject: QQ Domain Test

QQ internal email." | docker exec -i mail-qq-tencent sendmail test2@qq.com

echo -e "\n5.2 等待邮件送达"
sleep 5

echo -e "\n5.3 验证收件箱"
docker exec mail-qq-tencent ls -lh /var/mail/qq.com/test2/new/ 2>&1 | head -3

echo -e "\n========================================="
echo "演示完成！"
echo "========================================="
```

---

## 📊 DNS测试数据记录表

### DNS A记录测试

| 域名 | 查询结果IP | DNS服务器 | 状态 | 延迟 |
|------|-----------|-----------|------|------|
| qq.com | 10.200.0.10 | 10.200.0.71 | ✅ | <50ms |
| 163.com | 10.201.0.10 | 10.201.0.71 | ✅ | <50ms |
| gmail.com | 10.202.0.10 | 10.202.0.71 | ✅ | <50ms |
| outlook.com | 10.203.0.10 | 10.203.0.71 | ✅ | <50ms |
| company.cn | 10.204.0.10 | 10.150.0.74 | ✅ | <50ms |
| startup.net | 10.205.0.10 | 10.205.0.71 | ✅ | <50ms |

### DNS MX记录测试

| 域名 | MX主机 | MX IP | 优先级 | 状态 |
|------|--------|-------|--------|------|
| qq.com | mail.qq.com | 10.200.0.10 | 10 | ✅ |
| 163.com | mail.163.com | 10.201.0.10 | 10 | ✅ |
| gmail.com | mail.gmail.com | 10.202.0.10 | 10 | ✅ |
| outlook.com | mail.outlook.com | 10.203.0.10 | 10 | ✅ |
| company.cn | mail.company.cn | 10.204.0.10 | 10 | ✅ |
| startup.net | mail.startup.net | 10.205.0.10 | 10 | ✅ |

---

## 🎓 教学知识点

### 知识点1: DNS层次结构

演示如何从Root查询到最终IP：
```
客户端 → Local DNS Cache (10.150.0.53)
       → Root DNS (10.150.0.71)
       → .com TLD (10.150.0.73)
       → qq.com权威DNS (10.200.0.71)
       → 返回IP: 10.200.0.10
```

### 知识点2: MX记录作用

1. 查询收件人域名的MX记录
2. 获取邮件服务器主机名
3. 解析主机名获取IP
4. 连接IP发送邮件

### 知识点3: BGP路由选择

观察不同ISP的路由选择：
- 电信用户 → 电信网络 → QQ（更快）
- 联通用户 → 联通网络 → Gmail（绕路）

---

## ⚠️ 重要提示

### DNS启动时间
DNS服务器需要2-3分钟完全启动，请耐心等待。

### BGP收敛时间
BGP路由需要约120秒收敛，启动后必须等待。

### 域内vs跨域
- **域内邮件**: ✅ 完全正常（qq.com内、gmail.com内）
- **跨域邮件**: 功能演示以DNS为主

---

**编写**: SEED Lab Team  
**更新**: 2025-10-02  
**重点**: DNS系统教学

