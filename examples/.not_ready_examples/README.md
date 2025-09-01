# 🎯 SEED邮件系统完整解决方案

基于SEED Emulator的邮件系统实验平台，集成了基础邮件服务、跨域邮件传输、AI钓鱼检测、以及完整的网络安全教学演示环境。

## 📋 项目总览

```
SEED邮件系统完整架构
├── 🎯 核心目标: 邮件系统安全教学与实验
├── 🏗️ 架构层次: 基础→增强→AI→高级
├── 📊 实验场景: 7个完整实验演示
├── 🔧 技术栈: SEED Emulator + Docker + Flask + AI
├── 🎪 演示效果: 真实邮件传输 + 钓鱼攻击链 + 损失评估
└── 📚 教学价值: 网络安全、系统安全、AI安全
```

## 🚀 快速开始

### 环境要求
- Ubuntu 20.04+ / CentOS 7+
- Python 3.8+
- Docker & Docker Compose
- 8GB+ RAM, 50GB+ 磁盘空间

### 一键启动 (推荐)
```bash
# 进入项目目录
cd /home/parallels/seed-email-system/examples/.not_ready_examples

# 一键启动所有服务
./quick_start.sh

# 验证启动状态
seed-overview
```

### 手动启动
```bash
# 激活环境
conda activate seed-emulator

# 加载别名系统
source docker_aliases.sh

# 逐个启动项目
seed-29        # 基础邮件系统
seed-29-1      # 真实邮件网络
seed-30        # AI钓鱼系统
./start_simulation.sh  # 钓鱼仿真环境
```

## 📖 核心实验场景

### 🏗️ 实验#1: 邮件系统基础测试
**项目**: 29-email-system  
**目标**: 掌握基础邮件服务架构  
**端口**: http://localhost:5000  
**功能**: SMTP/IMAP服务，Web界面，邮件模板

### 🌐 实验#2: 真实邮件服务商测试
**项目**: 29-1-email-system  
**目标**: 理解跨域邮件传输机制  
**端口**: http://localhost:5001  
**功能**: 多域名支持，BGP路由，DNS解析

### 🦠 实验#3: XSS漏洞攻击测试
**项目**: gophish基础实验  
**目标**: 掌握XSS存储型攻击技术  
**端口**: http://localhost:5004  
**功能**: 反馈表单，存储型XSS，攻击日志

### 💉 实验#4: SQL注入攻击测试
**项目**: gophish基础实验  
**目标**: 学习SQL注入漏洞利用  
**端口**: http://localhost:5002  
**功能**: 员工查询，数据库泄露，注入检测

### 🔓 实验#5: Heartbleed内存泄露测试
**项目**: gophish基础实验  
**目标**: 理解SSL/TLS内存泄露漏洞  
**端口**: http://localhost:5003  
**功能**: SSL通信，内存泄露，敏感数据保护

### 📊 实验#6: 损失评估仪表板测试
**项目**: gophish基础实验  
**目标**: 掌握网络安全经济影响评估  
**端口**: http://localhost:5888  
**功能**: 实时统计，损失计算，可视化图表

### 🔗 实验#7: 完整攻击链集成测试
**目标**: 从邮件到攻击的完整闭环演示  
**流程**: 钓鱼邮件 → 用户点击 → 多重攻击 → 损失评估  
**价值**: 理解真实网络攻击的完整生命周期

## 🎛️ 系统管理面板

### 系统总览面板
**地址**: http://localhost:4257  
**功能**: 统一管理界面，项目状态监控，系统健康检查

```bash
# 启动系统总览
seed-overview

# 或直接运行
python3 system_overview_app.py
```

### Webmail客户端
**地址**: http://localhost:8000  
**功能**: RoundCube Webmail，邮件收发界面

**默认账户**:
- 用户名: alice@seedemail.net / admin@corporate.local
- 密码: password123

## 📚 项目文档结构

### 核心文档
- **[SEED_MAIL_SYSTEM_TEST_SCHEME.md](SEED_MAIL_SYSTEM_TEST_SCHEME.md)** - 完整测试方案和操作指南
- **[PROBLEM_SOLUTIONS.md](PROBLEM_SOLUTIONS.md)** - 常见问题解决方案
- **[README_DOCS.md](README_DOCS.md)** - 项目文档总览

### 项目文档
- **[29-email-system/README.md](29-email-system/README.md)** - 基础邮件系统文档
- **[29-1-email-system/README.md](29-1-email-system/README.md)** - 真实网络邮件系统文档
- **[30-phishing-ai-system/README.md](30-phishing-ai-system/README.md)** - AI钓鱼系统文档
- **[gophish基础实验/README.md](gophish基础实验/README.md)** - 钓鱼仿真系统文档

### 技术文档
- **[SYSTEM_OVERVIEW_README.md](SYSTEM_OVERVIEW_README.md)** - 系统架构总览
- **[FINAL_SYSTEM_OVERVIEW.md](FINAL_SYSTEM_OVERVIEW.md)** - 最终系统总结
- **[PROJECT_COMPLETION_SUMMARY.md](PROJECT_COMPLETION_SUMMARY.md)** - 项目完成总结

## 🔧 开发与部署

### 项目结构
```
seed-email-system/
├── examples/.not_ready_examples/          # 实验项目目录
│   ├── 29-email-system/                   # 基础邮件系统
│   ├── 29-1-email-system/                 # 真实网络邮件系统
│   ├── 30-phishing-ai-system/             # AI钓鱼系统
│   ├── gophish基础实验/                   # 钓鱼仿真环境
│   ├── docker_aliases.sh                  # Docker别名系统
│   ├── quick_start.sh                     # 一键启动脚本
│   └── system_overview_app.py             # 系统总览面板
├── docs/                                  # 文档目录
└── scripts/                               # 工具脚本
```

### 开发环境配置
```bash
# 克隆项目
git clone https://github.com/zzw4257/seed-email-system.git
cd seed-email-system

# 激活conda环境
conda activate seed-emulator

# 安装依赖
pip install -r requirements.txt

# 验证环境
python3 --version && docker --version
```

### 部署脚本
```bash
# 清理环境
./force_cleanup.sh

# 优化系统
python3 system_optimization.py

# 启动测试
./test_integration.sh
```

## 🎯 教学应用场景

### 网络安全课程
1. **邮件系统安全基础** - SMTP/IMAP协议安全
2. **Web应用安全** - XSS/SQL注入漏洞
3. **加密通信安全** - SSL/TLS漏洞分析
4. **网络攻击链** - 从钓鱼到数据泄露
5. **安全经济影响** - 攻击损失量化评估

### 实验教学流程
1. **环境搭建** (10分钟) - 系统部署和配置
2. **基础实验** (20分钟) - 邮件系统功能验证
3. **安全实验** (30分钟) - 漏洞攻击与防御
4. **综合实验** (20分钟) - 完整攻击链演示
5. **评估总结** (10分钟) - 实验报告与分析

## 📊 系统规格

### 硬件要求
- **CPU**: 4核以上
- **内存**: 8GB以上
- **存储**: 50GB以上
- **网络**: 千兆网卡

### 软件依赖
- **操作系统**: Ubuntu 20.04 / CentOS 7+
- **Python**: 3.8+
- **Docker**: 20.10+
- **Docker Compose**: 2.0+

### 网络端口分配
| 服务 | 端口 | 说明 |
|------|------|------|
| 29项目Web | 5000 | 基础邮件系统管理界面 |
| 29-1项目Web | 5001 | 真实网络邮件系统界面 |
| SQL注入服务器 | 5002 | 数据库漏洞仿真 |
| Heartbleed服务器 | 5003 | SSL漏洞仿真 |
| XSS服务器 | 5004 | Web漏洞仿真 |
| 系统总览 | 4257 | 统一管理系统界面 |
| 损失评估 | 5888 | 攻击统计仪表板 |
| Webmail | 8000 | RoundCube邮件客户端 |
| Gophish | 3333 | 钓鱼邮件管理平台 |

## 🚨 注意事项

### 安全提醒
- ⚠️ **仅用于教学研究** - 请勿用于非法活动
- 🔒 **隔离环境** - 在虚拟机或容器中运行
- 📝 **合规使用** - 遵守当地法律法规

### 系统维护
- 💾 **定期备份** - 重要数据定期备份
- 🔄 **版本更新** - 及时更新系统和软件
- 📊 **监控日志** - 注意系统运行日志

### 故障排除
- 📖 **查看文档** - 先查阅相关文档
- 🐛 **常见问题** - 参考`PROBLEM_SOLUTIONS.md`
- 💬 **技术支持** - 提交Issue获取帮助

## 🤝 贡献指南

### 代码贡献
1. Fork项目到个人仓库
2. 创建功能分支: `git checkout -b feature/new-feature`
3. 提交更改: `git commit -m 'Add new feature'`
4. 推送分支: `git push origin feature/new-feature`
5. 创建Pull Request

### 文档贡献
- 发现文档问题请提交Issue
- 改进建议欢迎Pull Request
- 翻译贡献请联系维护者

## 📄 许可证

本项目采用MIT许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 🙏 致谢

感谢SEED实验室提供的技术支持和实验环境，感谢所有贡献者的辛勤工作。

## 📞 联系方式

- **项目主页**: https://github.com/zzw4257/seed-email-system
- **问题反馈**: [提交Issue](https://github.com/zzw4257/seed-email-system/issues)
- **邮箱**: zzw4257@example.com

---

*最后更新: 2025年1月*  
*版本: v2.0*  
*维护者: SEED-Lab团队*
