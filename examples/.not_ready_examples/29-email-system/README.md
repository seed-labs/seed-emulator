# Email System Implementation on SEED Emulator

这个实验演示了如何在SEED Emulator框架中构建一个完整的邮件系统仿真环境。该实验利用docker-mailserver容器来实现邮件服务功能，模拟真实的邮件基础设施。

## 实验目标

1. **基础邮件系统**: 构建包含多个邮件服务器的网络拓扑
2. **多域名支持**: 模拟不同类型的邮件提供商（公共、企业、小企业）
3. **网络仿真**: 理解邮件系统在互联网中的工作原理
4. **安全扩展**: 为后续的钓鱼攻击实验奠定基础

## 项目结构

```
29-email-system/
├── README.md              # 本文档
├── email_simple.py        # 简化版邮件系统 (MVP)
├── email_system.py        # 完整版邮件系统 (带DNS)
├── DEVELOPMENT.md          # 开发日志和问题记录
└── configs/               # 邮件服务器配置文件
    ├── seedemail/         # seedemail.net 配置
    ├── corporate/         # corporate.local 配置  
    └── smallbiz/          # smallbiz.org 配置
```

## 版本说明

### MVP版本 (`email_simple.py`)
- ✅ 基础网络拓扑（3个邮件服务器AS + 2个客户端AS）
- ✅ docker-mailserver容器集成
- ✅ 多域名支持（seedemail.net, corporate.local, smallbiz.org）
- ✅ ARM64/AMD64平台支持
- ✅ 基础SMTP/IMAP服务
- ❌ 暂不包含DNS服务器配置

### 完整版本 (`email_system.py`)
- ✅ 包含MVP的所有功能
- ✅ DNS服务器配置
- ✅ MX记录和域名解析
- ❌ 仍在开发中

## 系统架构

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
        
                    Client Networks
                    AS-160, AS-161
```

### 邮件服务器配置

| 域名 | AS | 内部IP | SMTP端口 | IMAP端口 | 类型 |
|-----|----|---------|---------|---------|----|
| seedemail.net | 150 | 10.150.0.10 | 25150 | 143150 | 公共邮件 |
| corporate.local | 151 | 10.151.0.10 | 25151 | 143151 | 企业邮件 |
| smallbiz.org | 152 | 10.152.0.10 | 25152 | 143152 | 小企业 |

## 运行要求

### 系统要求
- Ubuntu 18.04+ 或其他Linux发行版
- Docker 和 docker-compose
- Python 3.8+
- 至少4GB RAM，10GB磁盘空间

### SEED Emulator环境
```bash
# 激活SEED环境
cd /home/parallels/seed-email-system
source development.env
conda activate seed-emulator
```

## 使用说明

### 1. 运行简化版邮件系统

```bash
# 进入项目目录
cd examples/.not_ready_examples/29-email-system

# 运行脚本生成仿真环境
python3 email_simple.py arm    # ARM64平台
# 或者
python3 email_simple.py amd    # AMD64平台

# 启动仿真
cd output/
docker-compose up -d
```

### 2. 启动Web管理界面 ⭐ **新功能**

```bash
# 返回项目根目录
cd ..

# 启动Web管理界面
./start_webmail.sh
```

访问地址:
- **Web管理界面**: http://localhost:5000 (邮件系统管理)
- **网络可视化**: http://localhost:8080/map.html (网络拓扑)

### 3. 查看运行状态

```bash
# 检查容器状态
cd output && docker-compose ps

# 查看邮件服务器日志
docker logs mail-150-seedemail
docker logs mail-151-corporate
docker logs mail-152-smallbiz
```

### 4. 创建邮件账户

```bash
# 在seedemail.net创建用户
docker exec -it mail-150-seedemail setup email add alice@seedemail.net
docker exec -it mail-150-seedemail setup email add bob@seedemail.net

# 在corporate.local创建用户
docker exec -it mail-151-corporate setup email add admin@corporate.local
docker exec -it mail-151-corporate setup email add manager@corporate.local

# 在smallbiz.org创建用户  
docker exec -it mail-152-smallbiz setup email add info@smallbiz.org
docker exec -it mail-152-smallbiz setup email add support@smallbiz.org
```

### 5. 测试邮件功能

```bash
# 进入客户端容器进行测试
docker exec -it as160h-host_0 bash

# 安装邮件客户端工具
apt update && apt install -y swaks telnet

# 测试SMTP连接
telnet 10.150.0.10 25

# 发送测试邮件
swaks --to alice@seedemail.net \
      --from bob@seedemail.net \
      --server 10.150.0.10:25 \
      --body "Hello from SEED Email System!"
```

### 5. 邮件客户端配置

如果需要使用外部邮件客户端，可以使用以下配置：

**IMAP接收设置:**
- 服务器: localhost
- 端口: 143150 (seedemail.net), 143151 (corporate.local), 143152 (smallbiz.org)
- 加密: 无 (测试环境)

**SMTP发送设置:**
- 服务器: localhost  
- 端口: 25150 (seedemail.net), 25151 (corporate.local), 25152 (smallbiz.org)
- 加密: 无 (测试环境)

## 故障排除

### 常见问题

1. **容器启动失败**
   ```bash
   # 检查docker-compose日志
   docker-compose logs
   
   # 清理并重新启动
   docker-compose down
   docker-compose up -d
   ```

2. **邮件服务器无法启动**
   ```bash
   # 检查端口是否被占用
   netstat -tlnp | grep -E "25150|25151|25152"
   
   # 检查mailserver容器日志
   docker logs mail-150-seedemail -f
   ```

3. **网络连接问题**
   ```bash
   # 进入容器检查网络
   docker exec -it as150h-host_0 bash
   ping 10.151.0.10
   
   # 检查路由表
   ip route show
   ```

4. **ARM64平台镜像问题**
   ```bash
   # 手动拉取ARM64镜像
   docker pull --platform linux/arm64 mailserver/docker-mailserver:edge
   ```

### 性能优化

1. **内存使用优化**
   - 减少邮件服务器数量
   - 调整docker-mailserver配置禁用不必要的服务

2. **启动时间优化**
   - 使用预构建的容器镜像
   - 减少初始化时的服务启动时间

## 扩展实验

### 计划中的功能扩展

1. **DNS系统集成** (`email_system.py`)
   - 完整的DNS服务器配置
   - MX记录和SPF记录支持
   - 域名解析测试

2. **安全特性** (未来版本)
   - TLS/SSL加密配置
   - DKIM签名验证
   - SPF和DMARC策略

3. **钓鱼攻击实验** (`30-phishing`)
   - 伪造邮件发送
   - 钓鱼网站托管
   - 安全意识培训

## 开发日志

详细的开发过程和问题解决方案请参考 [DEVELOPMENT.md](./DEVELOPMENT.md)

## 参考文档

- [SEED Emulator官方文档](https://github.com/seed-labs/seed-emulator)
- [docker-mailserver项目](https://github.com/docker-mailserver/docker-mailserver)
- [真实环境邮件服务器部署参考](../reference/inst.md)

## 许可证

本项目遵循SEED Lab的开源许可证协议。

---

**作者**: SEED Lab  
**创建时间**: 2024年  
**状态**: 开发中 (MVP已完成)
