# 🎯 SEED邮件系统 - 完整网络安全教学平台

[![SEED Lab](https://img.shields.io/badge/SEED-Lab-blue.svg)](https://seedsecuritylabs.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/docker-20.10+-blue.svg)](https://www.docker.com/)

基于SEED Emulator构建的完整邮件系统实验平台，涵盖从基础邮件服务到高级网络安全攻击的完整教学场景。

## 🌟 项目特色

### 🎯 核心功能
- ✅ **7个完整实验场景** - 从基础到高级的递进式学习
- ✅ **真实网络环境** - 基于SEED Emulator的模拟互联网
- ✅ **AI增强功能** - 集成AI钓鱼检测和生成
- ✅ **可视化管理** - Web界面统一管理系统
- ✅ **完整攻击链** - 从钓鱼邮件到数据泄露的闭环演示

### 🎪 实验演示
| 实验编号 | 实验名称 | 技术要点 | 演示效果 |
|---------|---------|---------|---------|
| **#1** | 邮件系统基础测试 | SMTP/IMAP/Webmail | 邮件收发界面 |
| **#2** | 真实邮件服务商测试 | 跨域传输/BGP/DNS | 多域名通信 |
| **#3** | XSS漏洞攻击测试 | 存储型XSS/JavaScript注入 | Web漏洞利用 |
| **#4** | SQL注入攻击测试 | 数据库注入/数据泄露 | 敏感信息窃取 |
| **#5** | Heartbleed内存泄露测试 | SSL/TLS漏洞/内存泄露 | 加密通信攻击 |
| **#6** | 损失评估仪表板测试 | 攻击统计/经济影响 | 可视化分析 |
| **#7** | 完整攻击链集成测试 | 钓鱼→攻击→评估 | 全链路演示 |

## 🚀 快速开始

### 环境要求
- **操作系统**: Ubuntu 20.04+ / CentOS 7+
- **Python**: 3.8+
- **Docker**: 20.10+
- **内存**: 8GB+
- **存储**: 50GB+

### 一键部署
```bash
# 克隆项目
git clone https://github.com/zzw4257/seed-email-system.git
cd seed-email-system

# 激活环境
conda activate seed-emulator

# 进入实验目录
cd examples/.not_ready_examples

# 一键启动所有服务
./quick_start.sh

# 验证启动状态
seed-overview
```

### 手动部署
```bash
# 加载别名系统
source docker_aliases.sh

# 逐个启动项目
seed-29        # 基础邮件系统
seed-29-1      # 真实邮件网络
seed-30        # AI钓鱼系统
./start_simulation.sh  # 钓鱼仿真
```

## 🎛️ 系统访问地址

启动完成后，可以通过以下地址访问各个系统：

| 系统 | 访问地址 | 功能说明 |
|------|---------|---------|
| 🏗️ **基础邮件系统** | http://localhost:5000 | 邮件服务器管理界面 |
| 🌐 **真实邮件网络** | http://localhost:5001 | 跨域邮件传输系统 |
| 🤖 **AI钓鱼系统** | http://localhost:5002 | AI增强的安全检测 |
| 💉 **SQL注入仿真** | http://localhost:5002 | 数据库漏洞演示 |
| 🦠 **XSS漏洞仿真** | http://localhost:5004 | Web安全漏洞演示 |
| 🔓 **Heartbleed仿真** | http://localhost:5003 | SSL/TLS漏洞演示 |
| 📊 **损失评估仪表板** | http://localhost:5888 | 攻击统计可视化 |
| 📧 **Webmail客户端** | http://localhost:8000 | RoundCube邮件界面 |
| 🎛️ **系统总览面板** | http://localhost:4257 | 统一管理系统 |

### 默认账户
- **Webmail**: alice@seedemail.net / admin@corporate.local
- **密码**: password123

## 📚 文档导航

### 🚀 快速入门
- **[完整测试方案](examples/.not_ready_examples/SEED_MAIL_SYSTEM_TEST_SCHEME.md)** - 详细的操作指南和测试流程
- **[快速开始指南](examples/.not_ready_examples/README_DOCS.md)** - 新手入门指南

### 📖 项目文档
- **[29项目文档](examples/.not_ready_examples/29-email-system/README.md)** - 基础邮件系统详细说明
- **[29-1项目文档](examples/.not_ready_examples/29-1-email-system/README.md)** - 真实网络邮件系统文档
- **[30项目文档](examples/.not_ready_examples/30-phishing-ai-system/README.md)** - AI钓鱼系统文档
- **[Gophish文档](examples/.not_ready_examples/gophish基础实验/README.md)** - 钓鱼仿真系统文档

### 🔧 技术文档
- **[问题解决方案](examples/.not_ready_examples/PROBLEM_SOLUTIONS.md)** - 常见问题和修复方法
- **[系统架构总览](examples/.not_ready_examples/SYSTEM_OVERVIEW_README.md)** - 技术架构说明
- **[项目完成总结](examples/.not_ready_examples/PROJECT_COMPLETION_SUMMARY.md)** - 项目实现总结

## 🏗️ 项目架构

```
SEED邮件系统架构
├── 📁 examples/.not_ready_examples/          # 实验项目根目录
│   ├── 29-email-system/                     # 基础邮件系统
│   │   ├── email_simple.py                  # SEED配置脚本
│   │   ├── webmail_server.py               # Flask管理界面
│   │   └── templates/                       # HTML模板
│   ├── 29-1-email-system/                   # 真实网络邮件系统
│   │   ├── email_realistic.py               # 跨域网络配置
│   │   ├── webmail_server.py               # 管理界面
│   │   └── output/                          # 编译输出
│   ├── 30-phishing-ai-system/               # AI钓鱼系统
│   │   ├── phishing_ai_system.py            # AI核心逻辑
│   │   ├── scripts/                         # 初始化脚本
│   │   └── test_flask.py                    # 测试界面
│   ├── gophish基础实验/                     # 钓鱼仿真系统
│   │   ├── vulnerable_servers/              # 漏洞服务器
│   │   ├── dashboard/                       # 损失评估
│   │   └── start_simulation.sh              # 启动脚本
│   ├── docker_aliases.sh                    # Docker别名系统
│   ├── system_overview_app.py               # 系统总览面板
│   └── quick_start.sh                       # 一键启动脚本
└── 📁 docs/                                 # 项目文档
```

## 🎯 教学应用

### 课程体系
本平台适用于网络安全相关课程的教学：

1. **网络协议安全** - SMTP/IMAP协议分析
2. **Web应用安全** - XSS/SQL注入漏洞
3. **加密通信安全** - SSL/TLS漏洞分析
4. **网络攻击技术** - 钓鱼邮件和攻击链
5. **安全影响评估** - 经济损失量化分析

### 实验流程
1. **环境搭建** (10分钟) - 系统部署配置
2. **基础实验** (20分钟) - 邮件系统功能验证
3. **安全实验** (30分钟) - 漏洞攻击与防御
4. **综合实验** (20分钟) - 完整攻击链演示
5. **评估总结** (10分钟) - 实验报告与分析

## 🔧 开发指南

### 环境配置
```bash
# 创建conda环境
conda create -n seed-emulator python=3.8
conda activate seed-emulator

# 安装SEED Emulator
pip install seed-emulator

# 验证安装
python -c "import seed_emulator as se; print('SEED版本:', se.__version__)"
```

### 本地开发
```bash
# 克隆项目
git clone https://github.com/zzw4257/seed-email-system.git
cd seed-email-system

# 安装开发依赖
pip install -r requirements-dev.txt

# 运行测试
python -m pytest tests/

# 代码格式化
black . && isort .
```

### Docker部署
```bash
# 构建镜像
docker build -t seed-email-system .

# 运行容器
docker run -p 5000:5000 -p 5001:5001 -p 5002:5002 seed-email-system

# 使用Compose
docker-compose up -d
```

## 📊 系统监控

### 健康检查
```bash
# 系统总览面板
curl http://localhost:4257/api/health

# 项目状态检查
curl http://localhost:4257/api/projects

# Docker容器状态
docker ps --filter "name=seed" --format "table {{.Names}}\t{{.Status}}"
```

### 日志查看
```bash
# 查看系统日志
tail -f examples/.not_ready_examples/29-email-system/webmail.log

# 查看Docker日志
docker logs mail-150-seedemail

# 查看攻击日志
tail -f examples/.not_ready_examples/gophish基础实验/logs/attacks.log
```

## 🚨 安全注意事项

### ⚠️ 重要提醒
- **仅限教学使用** - 请勿用于任何非法活动
- **隔离运行环境** - 建议在虚拟机或容器中运行
- **合规要求** - 确保遵守当地法律法规

### 🔒 安全配置
- 默认密码仅用于演示，请及时修改
- 生产环境请使用强密码和安全配置
- 定期更新系统和依赖包

## 🤝 贡献指南

我们欢迎各种形式的贡献！

### 代码贡献
1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

### 文档贡献
- 发现文档问题请提交 Issue
- 改进建议欢迎 Pull Request
- 翻译贡献请联系维护者

### 测试贡献
- 编写测试用例
- 报告 Bug 和问题
- 验证功能和性能

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- **SEED实验室** - 提供优秀的技术平台和实验环境
- **开源社区** - 众多优秀的开源项目和工具
- **贡献者们** - 所有为项目发展做出贡献的开发者

## 📞 联系我们

- **项目主页**: https://github.com/zzw4257/seed-email-system
- **问题反馈**: [GitHub Issues](https://github.com/zzw4257/seed-email-system/issues)
- **讨论交流**: [GitHub Discussions](https://github.com/zzw4257/seed-email-system/discussions)

## 🎯 版本信息

### 当前版本: v2.0
- ✅ 7个完整实验场景
- ✅ 完整的攻击链演示
- ✅ AI增强功能集成
- ✅ 可视化管理界面
- ✅ 详细的技术文档

### 近期更新
- 🎉 完整测试方案文档
- 🎉 系统总览面板优化
- 🎉 Docker别名系统完善
- 🎉 问题解决方案文档

---

**⭐ 如果这个项目对你有帮助，请给我们一个 Star！**

*最后更新: 2025年1月*  
*维护者: [zzw4257](https://github.com/zzw4257)*