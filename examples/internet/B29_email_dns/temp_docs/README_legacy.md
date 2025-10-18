# SEED 邮件系统 - 真实版 (29-1-email-system)

## 🚀 快速开始（TL;DR）

```bash
# 准备环境
cd /home/parallels/seed-email-system && source development.env

# 进入项目并生成
cd examples/.not_ready_examples/29-1-email-system
/home/parallels/miniconda3/envs/seed-emulator/bin/python email_realistic.py arm

# 构建与启动
cd output && docker-compose build --no-cache && docker-compose up -d && cd ..

# 初始化测试账号并启动 Roundcube (8082)
./manage_roundcube.sh accounts
./manage_roundcube.sh start

# DNS 快速验证
cd output
docker exec as150h-dns-cache-10.150.0.53 nslookup -type=mx gmail.com
docker exec as150h-dns-cache-10.150.0.53 nslookup -type=mx qq.com
cd ..
```

## 🧹 快速清理/停止

```bash
# 停止 Roundcube（可选）
./manage_roundcube.sh stop

# 停止 29-1 邮件系统（在 output/ 下执行）
cd output && docker-compose down && cd ..
```

一个模拟真实互联网邮件基础设施的完整仿真环境，包含QQ、163、Gmail、Outlook等知名邮件服务商，集成Roundcube Webmail提供真实的Web邮件体验。

## ✨ 核心特性

- 🌐 **真实服务商模拟**: QQ、163、Gmail、Outlook、企业邮箱、自建邮箱
- 🌍 **完整DNS系统**: 域名解析和MX记录（计划中）
- 📬 **Roundcube Webmail**: 支持6个邮件服务商的Web客户端
- 🔀 **多ISP架构**: 中国电信、联通、移动三大运营商
- 🌏 **地理分布**: 北京、上海、广州、海外节点
- 🎓 **教学友好**: 适合网络协议、国际邮件、安全测试教学

## 🚀 快速开始（三步）

```bash
# 步骤1: 生成并启动邮件系统
cd /home/parallels/seed-email-system
source development.env
cd examples/.not_ready_examples/29-1-email-system
/home/parallels/miniconda3/envs/seed-emulator/bin/python email_realistic.py arm
cd output && docker-compose up -d && cd ..

# 步骤2: 等待BGP收敛（重要！）
sleep 120

# 步骤3: 启动Roundcube
./manage_roundcube.sh start && ./manage_roundcube.sh accounts
```

**访问系统**:
- 📬 Roundcube: http://localhost:8082 (user@qq.com / password123)
- 🌐 网络拓扑: http://localhost:8080/map.html

**测试DNS**（核心特性）:
```bash
docker exec as150h-dns-cache-10.150.0.53 nslookup qq.com
docker exec as150h-dns-cache-10.150.0.53 nslookup -type=mx gmail.com
```

## 🌐 系统架构

### 网络拓扑

```
    Internet Exchange Points
    ┌──────────────────────────────────────────┐
    │ Beijing-IX(100) Shanghai-IX(101)         │
    │ Guangzhou-IX(102) Global-IX(103)         │
    └──────────────┬───────────────────────────┘
                   │
    ISP Providers (AS-2, AS-3, AS-4)
    中国电信、联通、移动
                   │
    ┌──────────────┴───────────────────────────┐
    │                                          │
    邮件服务商 (AS-200~205)              用户网络 (AS-150~153)
    QQ/163/Gmail/Outlook/企业/自建       北京/上海/广州/企业用户
```

### 邮件服务提供商

| 服务商 | 域名 | AS | 位置 | 容器名 | SMTP端口 | IMAP端口 |
|--------|------|-----|------|--------|---------|---------|
| QQ邮箱 | qq.com | 200 | 广州 | mail-qq-tencent | 2200 | 1400 |
| 163邮箱 | 163.com | 201 | 杭州 | mail-163-netease | 2201 | 1401 |
| Gmail | gmail.com | 202 | 海外 | mail-gmail-google | 2202 | 1402 |
| Outlook | outlook.com | 203 | 海外 | mail-outlook-microsoft | 2203 | 1403 |
| 企业邮箱 | company.cn | 204 | 上海 | mail-company-aliyun | 2204 | 1404 |
| 自建邮箱 | startup.net | 205 | 北京 | mail-startup-selfhosted | 2205 | 1405 |

### Internet Exchange Points

| IX | 名称 | ID | 位置 |
|----|------|-----|------|
| Beijing-IX | 北京互联网交换中心 | 100 | 北京 |
| Shanghai-IX | 上海互联网交换中心 | 101 | 上海 |
| Guangzhou-IX | 广州互联网交换中心 | 102 | 广州 |
| Global-IX | 国际互联网交换中心 | 103 | 国际 |

### ISP 提供商

| ISP | AS | 覆盖范围 | IX连接 |
|-----|-----|---------|--------|
| 中国电信 | 2 | 全国 | 100,101,102,103 |
| 中国联通 | 3 | 北方主导 | 100,101 |
| 中国移动 | 4 | 移动网络 | 100,102 |

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
# 查看容器状态
cd output && docker-compose ps | grep mail

# 查看特定服务器日志
docker logs mail-qq-tencent -f
docker logs mail-gmail-google -f

# 停止所有容器
docker-compose down
```

### 手动创建邮件账户

```bash
# QQ邮箱
printf "password\npassword\n" | docker exec -i mail-qq-tencent setup email add user@qq.com

# Gmail
printf "password\npassword\n" | docker exec -i mail-gmail-google setup email add user@gmail.com

# 163邮箱
printf "password\npassword\n" | docker exec -i mail-163-netease setup email add user@163.com

# 查看账户列表
docker exec mail-qq-tencent setup email list
```

## 📧 使用Roundcube

### 登录

1. 打开 http://localhost:8082
2. 输入用户名和密码
3. 选择服务器或留空自动检测
4. 点击登录

### 跨服务商邮件测试

可以测试不同服务商之间的邮件发送：
- user@qq.com → user@gmail.com (QQ到Gmail)
- user@163.com → user@outlook.com (163到Outlook)
- admin@company.cn → founder@startup.net (企业到自建)

## 🔧 项目结构

```
29-1-email-system/
├── email_realistic.py              # 主程序：生成真实邮件系统
├── webmail_server.py               # Web管理界面
├── manage_roundcube.sh             # Roundcube管理脚本
├── docker-compose-roundcube.yml    # Roundcube Docker配置
├── roundcube-config/               # Roundcube自定义配置
│   └── config.inc.php
├── templates/                      # Web界面模板
├── static/                         # 静态资源
└── output/                         # 生成的Docker配置（55+容器）
```

## 🎓 教学应用

### 适用课程

- **网络协议分析**: BGP/OSPF/DNS协议实战
- **邮件系统原理**: SMTP/IMAP深入学习
- **国际邮件路由**: 跨境邮件传输模拟
- **网络地理学**: 理解互联网地理和政治结构
- **社会工程学**: 钓鱼攻击原理和防护

### 实验场景

**1. 跨境邮件路由分析**
```bash
# 分析QQ到Gmail的路由路径
docker exec mail-qq-tencent traceroute 10.202.0.10

# 观察BGP路由表
docker exec as2brd-r100 birdc show route
```

**2. 跨服务商邮件测试**
```bash
# 从QQ发送到Gmail
# 使用Roundcube Web界面或命令行测试
```

**3. DNS解析验证**（计划中）
```bash
# 测试MX记录
nslookup -type=mx qq.com
nslookup -type=mx gmail.com
```

## 📊 与29版本对比

| 特性 | 29-email-system | 29-1-email-system |
|------|----------------|-------------------|
| 邮件服务器数量 | 3个 | 6个 |
| 真实服务商模拟 | 否 | 是 (QQ/Gmail等) |
| 地理分布 | 简单 | 真实城市分布 |
| ISP数量 | 1个 | 3个 (电信/联通/移动) |
| IX数量 | 1个 | 4个 |
| 容器数量 | ~20个 | ~55个 |
| Roundcube端口 | 8081 | 8082 |
| 教学复杂度 | 基础 | 高级 |

## 🔍 故障排除

### Roundcube无法访问

```bash
# 检查容器状态
docker ps | grep roundcube

# 查看日志
docker logs roundcube-webmail-29-1

# 重启
./manage_roundcube.sh restart
```

### 邮件服务器启动失败

```bash
# 检查特定服务器
cd output && docker-compose ps | grep mail

# 查看日志
docker logs mail-qq-tencent

# 重启特定服务器
docker-compose restart mail-qq-tencent
```

### 端口冲突

```bash
# 检查端口占用
netstat -tlnp | grep -E "8082|2200|2201"

# 修改端口（编辑docker-compose-roundcube.yml）
```

## 💡 高级配置

### 自定义Roundcube配置

编辑 `roundcube-config/config.inc.php` 可以自定义：
- 添加更多邮件服务商
- 修改界面语言和主题
- 配置插件
- 调整安全选项

修改后重启Roundcube：
```bash
./manage_roundcube.sh restart
```

## 📚 详细文档

- **[DEMO-TEACH.md](./DEMO-TEACH.md)** - 演示教学指南（含DNS测试）⭐
- **[DNS_TESTING_GUIDE.md](./DNS_TESTING_GUIDE.md)** - DNS测试专题指南⭐
- `manage_roundcube.sh --help` - Roundcube管理帮助

## ⚠️ 注意事项

1. **容器数量多**: 55+个容器，建议8GB以上内存
2. **启动时间长**: 约2-3分钟等待BGP收敛
3. **仅供学习**: 这是实验环境，不用于生产
4. **网络隔离**: 运行在Docker网络中

## 📊 系统资源

- **容器数量**: ~57个
- **内存占用**: ~1.5GB
- **启动时间**: ~180秒
- **存储空间**: ~3GB

## 🔄 更新日志

### v1.0 (2025-10-02)
- ✅ 真实邮件服务商系统完成
- ✅ Roundcube Webmail集成
- ✅ 管理脚本开发
- ✅ 项目结构清理
- ✅ 文档体系建立

---

## ✅ 项目状态（2025-10-02）

### 已实现功能
- ✅ 6个真实邮件服务商运行正常
- ✅ **完整DNS系统**（Root/TLD/权威DNS）
- ✅ **MX记录配置验证通过**
- ✅ BGP路由配置完成
- ✅ 网络连通性正常
- ✅ **域内邮件正常**（user@qq.com → bob@qq.com）
- ✅ Roundcube Webmail集成完成
- ✅ DNS解析测试通过

### 核心特性（相比29项目）
- ✨ **完整DNS层次结构**（教学重点）
- ✨ **MX记录配置**（教学重点）
- ✨ 真实服务商模拟
- ✨ 多ISP架构

### 推荐用途
- DNS系统学习（主要用途）
- MX记录原理教学
- BGP路由观察
- 真实网络架构模拟

---

**版本**: 1.0  
**状态**: ✅ DNS功能完成，域内邮件正常  
**维护**: SEED Lab Team  
**推荐**: ⭐⭐⭐⭐⭐（DNS教学）
