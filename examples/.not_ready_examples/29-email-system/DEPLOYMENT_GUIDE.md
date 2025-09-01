# SEED 邮件系统部署指南

## 🚀 快速开始 (5分钟部署)

### 前置条件
```bash
# 确保系统环境
- Ubuntu 18.04+ 或其他Linux发行版
- Docker 和 docker-compose
- Python 3.8+
- 至少 4GB RAM, 10GB 磁盘空间
```

### 1. 环境准备
```bash
# 进入项目目录
cd /path/to/seed-email-system

# 激活SEED环境
source development.env
conda activate seed-emulator
```

### 2. 部署邮件系统
```bash
# 进入邮件系统目录
cd examples/.not_ready_examples/29-email-system

# 生成配置 (ARM64平台)
python3 email_simple.py arm

# 或者AMD64平台
python3 email_simple.py amd

# 启动系统
cd output/
docker-compose up -d
```

### 3. 创建邮件账户
```bash
# 为每个域名创建测试账户
printf "password123\npassword123\n" | docker exec -i mail-150-seedemail setup email add alice@seedemail.net
printf "password123\npassword123\n" | docker exec -i mail-150-seedemail setup email add bob@seedemail.net
printf "admin123\nadmin123\n" | docker exec -i mail-151-corporate setup email add admin@corporate.local
printf "info123\ninfo123\n" | docker exec -i mail-152-smallbiz setup email add info@smallbiz.org
```

### 4. 验证部署
```bash
# 检查容器状态
docker-compose ps

# 测试SMTP服务
echo 'EHLO test' | nc localhost 2525

# 访问网络可视化
# 浏览器打开: http://localhost:8080/map.html
```

## 📋 系统访问信息

### 邮件服务器端口
| 服务 | 域名 | SMTP端口 | IMAP端口 |
|-----|------|----------|----------|
| 公共邮件 | seedemail.net | :2525 | :1430 |
| 企业邮件 | corporate.local | :2526 | :1431 |
| 小企业邮件 | smallbiz.org | :2527 | :1432 |

### 测试账户
| 邮箱地址 | 密码 | 用途 |
|---------|------|------|
| alice@seedemail.net | password123 | 公共邮件测试 |
| bob@seedemail.net | password123 | 公共邮件测试 |
| admin@corporate.local | admin123 | 企业邮件测试 |
| info@smallbiz.org | info123 | 小企业邮件测试 |

### 系统监控
- **网络拓扑**: http://localhost:8080/map.html
- **容器状态**: `docker-compose ps`
- **服务日志**: `docker logs <container_name>`

## 🔧 邮件客户端配置

### 使用外部邮件客户端

#### Thunderbird 配置示例
```
服务器类型: IMAP
服务器名称: localhost
端口: 1430 (seedemail.net) / 1431 (corporate.local) / 1432 (smallbiz.org)
安全设置: 无 (测试环境)
用户名: 完整邮箱地址
密码: 对应账户密码

SMTP设置:
服务器名称: localhost  
端口: 2525 (seedemail.net) / 2526 (corporate.local) / 2527 (smallbiz.org)
安全设置: 无 (测试环境)
```

### 命令行测试邮件发送
```bash
# 安装测试工具 (在客户端容器内)
docker exec -it as160h-host_0-10.160.0.71 bash
apt update && apt install -y swaks

# 发送测试邮件
swaks --to alice@seedemail.net \
      --from bob@seedemail.net \
      --server localhost:2525 \
      --body "Hello from SEED Email System!"
```

## 🛠️ 常用运维命令

### 容器管理
```bash
# 启动系统
docker-compose up -d

# 停止系统
docker-compose down

# 重启特定服务
docker-compose restart mail-150-seedemail

# 查看日志
docker-compose logs -f mail-150-seedemail
```

### 用户管理
```bash
# 添加新用户
printf "newpass\nnewpass\n" | docker exec -i mail-150-seedemail setup email add newuser@seedemail.net

# 删除用户
docker exec -it mail-150-seedemail setup email del user@seedemail.net

# 列出所有用户
docker exec -it mail-150-seedemail setup email list

# 修改用户密码
printf "newpass\nnewpass\n" | docker exec -i mail-150-seedemail setup email update user@seedemail.net
```

### 系统监控
```bash
# 检查系统资源使用
docker stats

# 检查网络连通性
docker exec -it as160h-host_0-10.160.0.71 ping 10.150.0.10

# 检查邮件服务状态
docker exec -it mail-150-seedemail supervisorctl status
```

## 🔍 故障排除

### 常见问题及解决方案

#### 1. 容器启动失败
```bash
# 症状: docker-compose up 失败
# 解决:
docker-compose down --remove-orphans
docker system prune -f
docker network prune -f
docker-compose up -d
```

#### 2. 端口冲突
```bash
# 症状: "Port already in use" 错误
# 检查端口占用:
netstat -tlnp | grep -E "2525|2526|2527|1430|1431|1432"

# 解决: 停止占用端口的服务或修改配置文件中的端口号
```

#### 3. 邮件服务器无响应
```bash
# 检查邮件服务器状态
docker logs mail-150-seedemail --tail 20

# 重启邮件服务器
docker-compose restart mail-150-seedemail

# 检查服务端口
docker exec -it mail-150-seedemail ss -tlnp | grep -E "(25|143)"
```

#### 4. 网络连通性问题
```bash
# 检查BGP路由收敛
docker exec -it as160brd-router0-10.160.0.254 birdc show route

# 等待路由收敛 (通常需要1-2分钟)
sleep 120

# 测试基础连通性
docker exec -it as160h-host_0-10.160.0.71 ping 10.100.0.2
```

#### 5. 邮件账户问题
```bash
# 症状: 邮件账户创建失败或登录失败
# 检查账户是否存在:
docker exec -it mail-150-seedemail setup email list

# 重新创建账户:
docker exec -it mail-150-seedemail setup email del user@seedemail.net
printf "newpass\nnewpass\n" | docker exec -i mail-150-seedemail setup email add user@seedemail.net
```

## 🧪 高级测试

### 跨域邮件测试
```bash
# 从一个域名向另一个域名发送邮件
swaks --to admin@corporate.local \
      --from alice@seedemail.net \
      --server localhost:2526 \
      --auth-user alice@seedemail.net \
      --auth-password password123
```

### 批量用户创建
```bash
# 批量创建测试用户
for i in {1..5}; do
    printf "test123\ntest123\n" | docker exec -i mail-150-seedemail setup email add user$i@seedemail.net
done
```

### 性能压力测试
```bash
# 并发连接测试
for i in {1..10}; do
    echo "EHLO test$i" | nc localhost 2525 &
done
wait
```

## 📦 系统卸载

### 完全清理
```bash
# 停止所有容器
cd output/
docker-compose down --remove-orphans

# 清理Docker资源
docker system prune -a -f
docker volume prune -f
docker network prune -f

# 删除项目文件 (可选)
cd ..
sudo rm -rf output/
```

## 🔄 系统更新

### 更新到最新版本
```bash
# 停止现有系统
docker-compose down

# 清理旧配置
cd .. && rm -rf output/

# 重新生成配置
python3 email_simple.py arm

# 启动更新后的系统
cd output/ && docker-compose up -d
```

## 📞 技术支持

### 获取帮助
- **查看日志**: 所有操作都有详细日志记录
- **参考文档**: 查看 README.md 和 TESTING_GUIDE.md
- **验证报告**: 参考 VALIDATION_REPORT.md 中的测试结果

### 报告问题
如果遇到问题，请提供以下信息：
1. 系统环境 (OS, Docker版本)
2. 错误日志 (`docker-compose logs`)
3. 容器状态 (`docker-compose ps`)
4. 复现步骤

---

**📝 部署清单**:
- [ ] 环境准备完成
- [ ] 系统部署成功
- [ ] 邮件账户创建
- [ ] 功能验证通过
- [ ] 监控界面可访问

**🎉 部署完成！你现在拥有了一个功能完整的邮件系统仿真环境！**
