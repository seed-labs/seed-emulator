# 真实邮件系统仿真 (29-1-email-system)

这是一个**完全独立**的真实邮件系统仿真项目，专注于模拟真实的互联网邮件基础设施。该项目逻辑自洽，不依赖29项目，为30项目的高级钓鱼功能奠定基础。

## 🎯 项目特色

### 相比29版本的重大改进
- ✅ **DNS系统集成**: 完整的域名解析和MX记录配置
- ✅ **真实服务商模拟**: QQ、163、Gmail、Outlook等知名邮件服务
- ✅ **地理位置分布**: 模拟中国三大城市和海外节点的真实拓扑
- ✅ **多ISP架构**: 中国电信、联通、移动三大运营商
- ✅ **国际化支持**: 支持中文域名和国际邮件传输
- ✅ **钓鱼实验就绪**: 为gophish集成做好准备

## 🌐 网络架构

### Internet Exchange Points
```
Beijing-IX (100)     Shanghai-IX (101)    Guangzhou-IX (102)    Global-IX (103)
     |                      |                     |                   |
北京互联网交换中心      上海互联网交换中心      广州互联网交换中心      国际互联网交换中心
```

### Internet Service Providers
```
AS-1: 中国电信 (全网覆盖)    ←→ 连接所有IX
AS-2: 中国联通 (北方主导)    ←→ 连接北京、上海IX  
AS-3: 中国移动 (移动网络)    ←→ 连接北京、广州IX
```

### 邮件服务提供商
| AS号 | 服务商 | 域名 | 位置 | 容器名 | SMTP端口 |
|-----|-------|------|------|--------|----------|
| 200 | 腾讯QQ | qq.com | 广州 | mail-qq-tencent | :2200 |
| 201 | 网易163 | 163.com | 杭州 | mail-163-netease | :2201 |
| 202 | Google Gmail | gmail.com | 海外 | mail-gmail-google | :2202 |
| 203 | Microsoft Outlook | outlook.com | 海外 | mail-outlook-microsoft | :2203 |
| 204 | 阿里云企业邮 | company.cn | 上海 | mail-company-aliyun | :2204 |
| 205 | 自建邮箱 | startup.net | 北京 | mail-startup-selfhosted | :2205 |

### 用户网络
- **AS-300**: 北京用户 (4个主机) - 模拟北方用户群体
- **AS-301**: 上海用户 (4个主机) - 模拟华东用户群体  
- **AS-302**: 广州用户 (4个主机) - 模拟华南用户群体
- **AS-303**: 企业内网 (5个主机) - 模拟企业网络环境

## 🚀 快速部署

### 环境准备
```bash
# 激活SEED环境
cd /home/parallels/seed-email-system
source development.env
conda activate seed-emulator

# 进入项目目录
cd examples/.not_ready_examples/29-1-email-system
```

### 生成和启动
```bash
# 生成真实邮件系统配置
python3 email_realistic.py arm    # ARM64平台
# 或者
python3 email_realistic.py amd    # AMD64平台

# 启动系统
cd output/
docker-compose up -d

# 查看启动状态
docker-compose ps | grep mail
```

### 访问系统
- **网络拓扑可视化**: http://localhost:8080/map.html
- **邮件服务器**: 各服务商独立端口 (见上表)

## 📧 邮件账户管理

### 创建测试账户
```bash
# QQ邮箱账户
docker exec -it mail-qq-tencent setup email add zhangsan@qq.com
docker exec -it mail-qq-tencent setup email add lisi@qq.com

# 163邮箱账户  
docker exec -it mail-163-netease setup email add wangwu@163.com
docker exec -it mail-163-netease setup email add zhaoliu@163.com

# Gmail账户
docker exec -it mail-gmail-google setup email add john@gmail.com
docker exec -it mail-gmail-google setup email add jane@gmail.com

# Outlook账户
docker exec -it mail-outlook-microsoft setup email add mike@outlook.com
docker exec -it mail-outlook-microsoft setup email add sarah@outlook.com

# 企业邮箱账户
docker exec -it mail-company-aliyun setup email add admin@company.cn
docker exec -it mail-company-aliyun setup email add hr@company.cn

# 自建邮箱账户
docker exec -it mail-startup-selfhosted setup email add founder@startup.net
docker exec -it mail-startup-selfhosted setup email add cto@startup.net
```

### 查看账户列表
```bash
# 查看QQ邮箱用户
docker exec -it mail-qq-tencent setup email list

# 查看Gmail用户
docker exec -it mail-gmail-google setup email list
```

## 🧪 功能测试

### DNS解析测试
```bash
# 进入客户端容器
docker exec -it as300h-host_0-10.300.0.71 bash

# 测试DNS解析
nslookup qq.com
nslookup gmail.com  
nslookup mail.163.com

# 测试MX记录
dig MX qq.com
dig MX gmail.com
```

### 跨域邮件测试
```bash
# 从QQ发送到Gmail (模拟跨境邮件)
swaks --to john@gmail.com \
      --from zhangsan@qq.com \
      --server localhost:2200 \
      --body "跨境邮件测试: QQ -> Gmail"

# 从163发送到Outlook (模拟国际邮件)  
swaks --to mike@outlook.com \
      --from wangwu@163.com \
      --server localhost:2201 \
      --body "国际邮件测试: 163 -> Outlook"

# 企业内部邮件
swaks --to hr@company.cn \
      --from admin@company.cn \
      --server localhost:2204 \
      --body "企业内部邮件测试"
```

### 网络连通性测试
```bash
# 测试北京到广州的连通性
docker exec -it as300h-host_0-10.300.0.71 ping 10.200.0.10

# 测试上海到海外的连通性  
docker exec -it as301h-host_0-10.301.0.71 ping 10.202.0.10

# 测试路由跟踪
docker exec -it as300h-host_0-10.300.0.71 traceroute 10.203.0.10
```

## 🔧 高级配置

### 邮件客户端配置

#### QQ邮箱配置
```
服务器: localhost
SMTP端口: 2200
IMAP端口: 1400
用户名: your_username@qq.com
密码: [在容器中设置的密码]
```

#### Gmail配置  
```
服务器: localhost
SMTP端口: 2202
IMAP端口: 1402
用户名: your_username@gmail.com
密码: [在容器中设置的密码]
```

### DNS服务器配置
系统自动配置了完整的DNS层次结构:
- 根DNS服务器 (.) 
- 顶级域DNS (.com, .net, .cn)
- 邮件服务商DNS (qq.com, gmail.com等)
- MX记录自动配置

## 🎯 实验场景

### 1. 邮件路由分析
研究邮件如何在不同ISP和地理位置间传输:
```bash
# 分析QQ到Gmail的路由路径
docker exec -it mail-qq-tencent traceroute 10.202.0.10

# 观察BGP路由表
docker exec -it as1brd-r100-10.100.0.1 birdc show route
```

### 2. DNS劫持模拟
模拟DNS劫持攻击场景:
```bash
# 修改DNS配置模拟劫持
# (详细步骤见高级实验指南)
```

### 3. 跨境邮件监控
模拟邮件经过多个国家/地区的传输:
```bash
# 海外邮件路径分析
docker exec -it as202h-host_0-10.202.0.71 traceroute 10.200.0.10
```

## 🚨 钓鱼实验准备

### 与gophish集成准备
此版本为集成gophish钓鱼工具做好了准备:

1. **真实域名模拟**: 提供了qq.com、gmail.com等真实域名
2. **多样化目标**: 不同类型的邮件服务商和用户群体
3. **网络隔离**: 安全的实验环境，不会影响真实网络
4. **DNS控制**: 可以自定义DNS解析实现钓鱼域名

### 下一步集成计划
- 集成gophish服务器容器
- 配置钓鱼邮件模板
- 设置目标用户组  
- 建立攻击场景

## 📊 系统监控

### 容器状态监控
```bash
# 查看所有邮件服务器状态
docker-compose ps | grep mail

# 查看特定服务器日志
docker logs mail-qq-tencent --tail 20
docker logs mail-gmail-google --tail 20

# 查看资源使用情况
docker stats $(docker ps -q --filter "name=mail-")
```

### 网络流量监控
```bash
# 监控邮件服务器间的流量
docker exec -it as200brd-router0-10.200.0.254 tcpdump -i any port 25

# 监控DNS查询
docker exec -it as1brd-r0-10.100.0.1 tcpdump -i any port 53
```

## 🔍 故障排除

### 常见问题

#### 1. 邮件服务器启动失败
```bash
# 检查容器日志
docker logs mail-qq-tencent

# 检查端口冲突
netstat -tlnp | grep -E "2200|2201|2202"

# 重启特定服务器
docker-compose restart mail-qq-tencent
```

#### 2. DNS解析问题
```bash
# 检查DNS服务器状态
docker exec -it as1brd-r0-10.100.0.1 nslookup qq.com

# 重新启动DNS服务
docker-compose restart $(docker-compose ps -q | grep dns)
```

#### 3. 跨域邮件发送失败
```bash
# 检查路由表
docker exec -it as200brd-router0-10.200.0.254 birdc show route

# 等待BGP收敛
sleep 120

# 重新测试连通性
docker exec -it as300h-host_0-10.300.0.71 ping 10.202.0.10
```

## 📝 与29版本对比

| 特性 | 29-email-system | 29-1-email-system |
|-----|-----------------|-------------------|
| 邮件服务器数量 | 3个 | 6个 |
| DNS系统 | 无 | 完整DNS层次 |
| 真实服务商模拟 | 否 | 是 (QQ/Gmail等) |
| 地理分布 | 简单 | 真实城市分布 |
| ISP数量 | 1个 | 3个 (电信/联通/移动) |
| 国际化支持 | 基础 | 完整 |
| 钓鱼实验就绪 | 否 | 是 |

## 🎓 教学价值

### 适用课程
- **网络协议分析**: BGP/OSPF/DNS协议实战
- **邮件系统原理**: SMTP/IMAP/POP3协议深入学习  
- **网络安全基础**: 邮件安全、DNS安全、路由安全
- **社会工程学**: 钓鱼攻击原理和防护
- **网络地理学**: 理解互联网的地理和政治结构

### 学习目标
1. 理解真实互联网的层次结构
2. 掌握邮件系统的完整工作流程
3. 学习DNS系统的安全重要性
4. 了解跨境网络通信的复杂性
5. 为高级网络安全实验打基础

---

**项目状态**: 🚀 已完成，功能完整  
**推荐指数**: ⭐⭐⭐⭐⭐ (5星推荐)  
**适用对象**: 网络安全研究者、教学实验、钓鱼攻击研究  

**下一步**: 集成gophish实现完整的钓鱼攻击实验平台
