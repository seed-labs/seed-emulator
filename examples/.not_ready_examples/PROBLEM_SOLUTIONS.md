# SEED邮件系统问题解决方案文档

## 📋 问题概览

本文档汇总了SEED邮件系统在运行过程中遇到的问题及其解决方案。

## 🔧 已解决的问题

### 1. 29项目邮箱账户缺失问题

**问题描述：**
- 默认建立的邮箱账户丢失
- alice@seedemail.net, bob@seedemail.net 等账户不存在

**原因分析：**
- Docker容器重启后数据丢失
- 邮件服务器配置未正确初始化

**解决方案：**
```bash
# 重新创建账户
echo -e "password123\npassword123" | docker exec -i mail-150-seedemail setup email add alice@seedemail.net
echo -e "password123\npassword123" | docker exec -i mail-150-seedemail setup email add bob@seedemail.net
echo -e "admin123\nadmin123" | docker exec -i mail-151-corporate setup email add admin@corporate.local
echo -e "info123\ninfo123" | docker exec -i mail-152-smallbiz setup email add info@smallbiz.org
```

**验证方法：**
```bash
docker exec mail-150-seedemail setup email list
docker exec mail-151-corporate setup email list
docker exec mail-152-smallbiz setup email list
```

### 2. 邮件服务器连接问题

**问题描述：**
- 前端无法连接到邮件服务器
- 邮件发送/接收失败

**原因分析：**
- 邮件服务器配置问题
- 端口映射不正确
- 权限问题

**解决方案：**
```bash
# 测试邮件发送
swaks --to alice@seedemail.net --server localhost --port 2525 --from admin@seedemail.net --header "Subject: Test Email" --body "This is a test email"

# 检查端口状态
netstat -tlnp | grep -E ":(2525|2526|2527|8080)"
```

### 3. Docker权限问题

**问题描述：**
```
PermissionError: [Errno 13] Permission denied: 'mail-150-seedemail-data'
```

**原因分析：**
- Docker容器以root用户身份创建文件
- 宿主机普通用户无法删除root所有者的文件

**解决方案：**
```bash
# 使用sudo删除目录
sudo rm -rf output/

# 或者改变文件所有者
sudo chown -R parallels:parallels output/
```

### 4. Flask应用导入错误

**问题描述：**
```
ModuleNotFoundError: No module named 'flask'
```

**原因分析：**
- 未激活正确的conda环境
- 缺少Flask依赖

**解决方案：**
```bash
# 激活环境
cd /home/parallels/seed-email-system
source development.env
conda activate seed-emulator

# 启动应用
python3 system_overview_app.py
```

### 5. Bootstrap标签页JavaScript错误

**问题描述：**
```
selector-engine.js:37 Uncaught TypeError: Illegal invocation
```

**原因分析：**
- HTML标签页使用错误的语法
- Bootstrap 5标签页需要button元素而不是a元素

**解决方案：**
将导航链接从：
```html
<a href="#overview" data-bs-toggle="tab">总览</a>
```

改为：
```html
<button data-bs-target="#overview" data-bs-toggle="tab" type="button">总览</button>
```

## 🚨 当前存在的问题

### 1. 29-1项目ContainerConfig错误

**问题描述：**
```
KeyError: 'ContainerConfig'
```

**原因分析：**
- Docker Compose版本过旧 (1.29.2)
- 容器镜像配置问题

**临时解决方案：**
```bash
# 清理并重启项目
cd examples/.not_ready_examples/29-1-email-system/output
docker-compose down --remove-orphans -v
cd ..
python3 email_realistic.py arm
```

### 2. 30项目ASN号过大问题

**问题描述：**
```
AssertionError: can't use auto: asn > 255
```

**原因分析：**
- SEED-Emulator ASN号限制为255以内
- 30项目使用了过大的ASN号 (300, 400等)

**解决方案：**
修改`phishing_ai_system.py`中的ASN号：
```python
# 将过大的ASN号改为合理范围
Makers.makeStubAsWithHosts(emu, base, 50, 100, 3)  # 改为50
```

## 📊 系统状态检查

### 当前运行项目状态

#### 29基础项目 ✅ 正常运行
- **邮箱账户：** 已创建alice@seedemail.net, bob@seedemail.net, admin@seedemail.net
- **邮件服务器：** 3个域名正常运行
- **端口：** 2525(SMTP), 1430(IMAP), 5000(Web)
- **网络图：** http://localhost:8080/map.html

#### 29-1真实项目 ⚠️ 配置错误
- **状态：** 编译成功但启动失败
- **错误：** ContainerConfig KeyError
- **建议：** 使用Docker Compose V2或清理缓存

#### 30 AI项目 ❌ ASN错误
- **状态：** 编译失败
- **错误：** ASN号过大
- **解决方案：** 修改ASN号配置

### 端口占用情况
```bash
# 检查关键端口
netstat -tlnp | grep -E ":(5000|2525|2526|2527|8080)"

# 预期输出：
tcp        0      0 0.0.0.0:2525            LISTEN      # seedemail SMTP
tcp        0      0 0.0.0.0:2526            LISTEN      # corporate SMTP
tcp        0      0 0.0.0.0:2527            LISTEN      # smallbiz SMTP
tcp        0      0 0.0.0.0:8080            LISTEN      # 网络图
tcp        0      0 0.0.0.0:5000            LISTEN      # 系统总览
```

## 🛠️ 维护命令

### Docker容器管理
```bash
# 查看所有容器
docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# 清理停止的容器
docker container prune -f

# 清理未使用的镜像
docker image prune -f

# 清理卷
docker volume prune -f
```

### 邮件服务器管理
```bash
# 查看账户列表
docker exec mail-150-seedemail setup email list

# 添加新账户
docker exec mail-150-seedemail setup email add newuser@seedemail.net

# 删除账户
docker exec mail-150-seedemail setup email del olduser@seedemail.net

# 重启邮件服务器
docker restart mail-150-seedemail
```

### 系统总览管理
```bash
# 启动系统总览
cd examples/.not_ready_examples
source docker_aliases.sh
seed-overview

# 或者直接启动
python3 system_overview_app.py
```

## 📈 项目功能对比

| 功能特性 | 29基础版 | 29-1真实版 | 30 AI版 |
|---------|---------|-----------|--------|
| 邮件服务器 | ✅ | ✅ | ✅ |
| Web界面 | ✅ | 计划中 | ✅ |
| DNS系统 | ❌ | ✅ | ✅ |
| 真实ISP | ❌ | ✅ | ❌ |
| AI攻击 | ❌ | ❌ | ✅ |
| AI防护 | ❌ | ❌ | ✅ |
| 钓鱼平台 | ❌ | ❌ | ✅ |

## 🎯 使用建议

### 推荐使用项目
1. **29基础版** - 最稳定，适合学习邮件系统基础
2. **系统总览** - 统一管理界面，端口4257

### 开发建议
1. **环境激活** - 每次使用前都要激活seed-emulator环境
2. **别名加载** - 使用`source docker_aliases.sh`加载便捷命令
3. **权限处理** - Docker文件权限问题及时清理
4. **端口检查** - 启动前检查端口占用情况

### 故障排除步骤
1. **激活环境** - `source development.env && conda activate seed-emulator`
2. **清理缓存** - `docker system prune -f`
3. **检查端口** - `netstat -tlnp | grep :5000`
4. **重启项目** - 使用seed-*命令重新启动

## 📞 获取帮助

### 常用命令
```bash
# 系统帮助
seed-help

# 检查状态
seed-status

# 清理系统
seed-force-cleanup

# 检查端口
seed-check-ports
```

### 技术支持
- 📖 **文档：** 查看各项目的README.md
- 🔧 **日志：** 检查webmail.log和seed_email.log
- 🐛 **调试：** 使用浏览器开发者工具检查JavaScript错误

---

*最后更新时间：2025-08-31*
*版本：SEED邮件系统 v1.0*
