# 🐳 SEED邮件系统 Docker别名使用指南

## 📋 概述

为了简化SEED邮件系统的Docker管理，我们提供了一套完整的命令别名系统，让您可以更高效地管理和操作Docker容器。

## 🚀 快速开始

### 方法一: 临时使用 (推荐新手)
```bash
# 在项目根目录下
source docker_aliases.sh

# 或者使用设置向导
./setup_aliases.sh
```

### 方法二: 永久安装
```bash
# 运行设置向导，选择选项2
./setup_aliases.sh
# 然后选择 [2] 永久添加到 ~/.bashrc
```

### 方法三: 项目专用别名
```bash
# 在各个项目目录下
cd 29-email-system && source load_aliases.sh
cd 29-1-email-system && source load_aliases.sh  
cd 30-phishing-ai-system && source load_aliases.sh
```

## 📦 Docker Compose 命令别名

| 别名 | 原命令 | 说明 |
|------|--------|------|
| `dcbuild` | `docker-compose build` | 构建容器镜像 |
| `dcup` | `docker-compose up` | 启动容器 |
| `dcupd` | `docker-compose up -d` | 后台启动容器 |
| `dcdown` | `docker-compose down` | 停止容器 |
| `dcrestart` | `docker-compose restart` | 重启容器 |
| `dcstop` | `docker-compose stop` | 停止容器(不删除) |
| `dcstart` | `docker-compose start` | 启动已停止的容器 |
| `dclogs` | `docker-compose logs` | 查看日志 |
| `dclogf` | `docker-compose logs -f` | 跟踪日志 |
| `dcps` | `docker-compose ps` | 查看服务状态 |

### 扩展命令
| 别名 | 说明 |
|------|------|
| `dcdown-clean` | 完全清理 (包括volumes和orphans) |
| `dcbuild-clean` | 无缓存构建 |

## 🐳 Docker 容器管理别名

| 别名 | 原命令 | 说明 |
|------|--------|------|
| `dockps` | `docker ps --format "table ..."` | 格式化显示运行中容器 |
| `dockpsa` | `docker ps -a --format "table ..."` | 格式化显示所有容器 |
| `docksh <id>` | `docker exec -it <id> /bin/bash` | 进入容器Shell |
| `docksh-sh <id>` | `docker exec -it <id> /bin/sh` | 进入容器Shell(sh) |

### 使用示例
```bash
# 查看运行中的容器
dockps

# 进入容器 (只需输入ID前几位)
docksh 96a  # 等同于 docker exec -it 96a... /bin/bash
```

## 🎯 SEED 项目专用命令

### 快速启动项目
```bash
seed-29        # 启动29基础版邮件系统
seed-29-1      # 启动29-1真实版邮件系统  
seed-30        # 启动30钓鱼AI系统
seed-stop      # 停止所有SEED项目
```

### 系统监控
```bash
seed-status      # 检查所有SEED项目状态
seed-ai-status   # 检查AI服务状态
seed-shell <容器> # 进入SEED容器
```

### 日志查看
```bash
seed-logs <容器名>  # 查看特定容器日志
```

## 📧 邮件测试命令

### 邮件发送测试
```bash
# 发送测试邮件
seed-mail-send admin@seedemail.net user@corporate.local "测试邮件" "这是测试内容"

# 查看邮件测试帮助
seed-mail-test
```

## 🌐 网络调试命令

### 网络连通性测试
```bash
# 网络ping测试
seed-ping as150h-host_0-10.150.0.71 10.200.0.71

# 路由跟踪
seed-traceroute as150h-host_0-10.150.0.71 10.200.0.71
```

## 🧹 系统清理命令

```bash
docker-clean       # 基础清理
docker-clean-all   # 完全清理 (包括未使用的镜像)
docker-clean-volumes  # 清理volumes
docker-clean-networks # 清理networks
```

## 📚 项目专用命令详解

### 29-email-system 专用命令

```bash
# 加载29项目别名
cd 29-email-system && source load_aliases.sh

# 项目管理
start-29         # 启动29邮件系统
stop-29          # 停止29邮件系统
status-29        # 检查29系统状态
web-29           # 启动Web管理界面

# 邮件管理
mail-test        # 邮件服务测试指南

# 日志管理
logs-29 [服务]   # 查看特定服务日志

# 帮助
help-29          # 查看29项目专用命令
```

### 29-1-email-system 专用命令

```bash
# 加载29-1项目别名
cd 29-1-email-system && source load_aliases.sh

# 项目管理
start-29-1       # 启动29-1真实邮件系统
stop-29-1        # 停止29-1邮件系统
status-29-1      # 检查29-1系统状态
test-29-1        # 运行网络测试

# 网络测试
network-test <源容器> <目标IP>    # 网络连通性测试
route-test <源容器> <目标IP>      # 路由跟踪测试
bgp-routes <路由器容器>          # BGP路由表查看

# 帮助
help-29-1        # 查看29-1项目专用命令
```

#### 网络测试示例
```bash
# 测试北京用户到QQ邮箱的连通性
network-test as150h-host_0-10.150.0.71 10.200.0.71

# 查看BGP路由
bgp-routes as2brd-r100-10.100.0.2
```

### 30-phishing-ai-system 专用命令

```bash
# 加载30项目别名
cd 30-phishing-ai-system && source load_aliases.sh

# 项目管理
start-30         # 启动30钓鱼AI系统
stop-30          # 停止30钓鱼系统
status-30        # 检查30系统状态

# Web界面
web-console      # 打开Web管理控制台
gophish-web      # 打开Gophish钓鱼平台

# AI服务
ai-status        # AI服务详细状态
ai-test          # AI功能测试

# 钓鱼实验
phishing-demo    # 钓鱼攻击演示指南

# 帮助
help-30          # 查看30项目专用命令
```

#### AI测试示例
```bash
# 检查AI服务状态
ai-status

# 测试AI功能
ai-test

# 打开Web控制台
web-console
```

## 💡 使用技巧

### 1. 容器ID简化输入
```bash
# 不需要输入完整ID
docksh 96a    # 等同于 docker exec -it 96a1b2c3... /bin/bash
```

### 2. 组合使用
```bash
# 快速重启项目
dcdown && dcup

# 查看日志并跟踪
dclogs mail-service && dclogf mail-service
```

### 3. 快速调试
```bash
# 一键查看系统状态
seed-status

# 快速进入邮件服务器
seed-shell mail-150-seedemail
```

### 4. 批量操作
```bash
# 停止所有SEED项目
seed-stop

# 清理整个系统
docker-clean-all
```

## 🔧 故障排除

### 常见问题

1. **别名不工作**
   ```bash
   # 重新加载别名
   source docker_aliases.sh
   ```

2. **容器连接失败**
   ```bash
   # 检查容器状态
   dockps
   
   # 尝试不同的Shell
   docksh-sh <id>
   ```

3. **服务未响应**
   ```bash
   # 检查服务状态
   seed-status
   
   # 查看日志
   seed-logs <容器名>
   ```

### 重置环境
```bash
# 完全重置Docker环境
dcdown-clean
docker-clean-all
docker system prune -af --volumes
```

## 🎓 学习路径建议

### 初学者
1. 先使用 `./setup_aliases.sh` 临时加载别名
2. 从 `seed-29` 开始体验基础功能
3. 使用 `seed-help` 了解所有可用命令

### 进阶用户
1. 永久安装别名到 `~/.bashrc`
2. 学习项目专用命令
3. 组合使用多个别名提高效率

### 专家用户
1. 自定义修改 `docker_aliases.sh`
2. 创建项目特定的别名
3. 集成到CI/CD流程中

## 📞 获取帮助

- **查看所有命令**: `seed-help`
- **项目专用帮助**: `help-29`, `help-29-1`, `help-30`
- **设置向导**: `./setup_aliases.sh`

---

**🎉 现在您可以更高效地管理SEED邮件系统了！**

记住，这些别名旨在简化您的工作流程，让您专注于网络安全实验而不是复杂的Docker命令。
