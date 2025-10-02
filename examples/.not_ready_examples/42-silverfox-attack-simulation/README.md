# 🦊 42-银狐木马攻击仿真复现实验 (4257号实验包)

**实验编号**: 42-silverfox-attack-simulation  
**端口**: 4257  
**文档版本**: 1.0  
**更新日期**: 2025-09-24  

## 📋 实验概述

本实验包基于现有的SEED邮件系统环境，完整复现"银狐"木马攻击链，从初始钓鱼邮件到内网渗透的全过程。集成了Gophish钓鱼平台、Aurora-demos自动化框架和PentestAgent渗透测试工具。

### 🎯 攻击链阶段

1. **初始访问与立足点建立** - 钓鱼邮件 → 恶意载荷投递
2. **内网侦察** - 网络扫描 → 主机枚举 → 用户发现
3. **攻击规划** - 漏洞分析 → 攻击路径生成
4. **横向移动与权限提升** - 凭据收集 → 横向扩散
5. **数据窃取与影响** - 敏感数据窃取 → 数据外泄

## 🚀 快速启动

### 环境外测试 (推荐先执行)
```bash
# 激活seed-emulator环境
conda activate seed-emulator

# 进入实验目录
cd /home/parallels/seed-email-system/examples/.not_ready_examples/42-silverfox-attack-simulation

# 环境外功能测试
./test_outside_simulation.sh

# 访问测试界面
http://localhost:4257
```

### 完整仿真环境
```bash
# 启动完整攻击链仿真
./start_silverfox_simulation.sh

# 访问管理界面
http://localhost:4257
```

## 📁 项目结构

```
42-silverfox-attack-simulation/
├── README.md                    # 本文档
├── silverfox_simulation.py      # 核心仿真脚本
├── start_silverfox_simulation.sh # 启动脚本
├── test_outside_simulation.sh   # 环境外测试脚本
├── web_interface.py             # Web管理界面 (端口4257)
├── config/                      # 配置文件
│   ├── attack_chain_config.yaml # 攻击链配置
│   ├── gophish_config.json      # Gophish配置
│   └── network_config.yaml      # 网络配置
├── payloads/                    # 恶意载荷
│   ├── fake_chrome_installer.sh # 伪装Chrome安装包
│   ├── backdoor_scripts/        # 后门脚本
│   └── data_collection/         # 数据收集脚本
├── templates/                   # Web模板和邮件模板
│   ├── phishing_templates/      # 钓鱼邮件模板
│   ├── landing_pages/           # 着陆页模板
│   └── web_templates/           # Web界面模板
├── simulation_framework/        # 仿真框架
│   ├── attack_orchestrator.py   # 攻击编排器
│   ├── network_simulator.py     # 网络仿真器
│   ├── lateral_movement.py      # 横向移动模拟
│   └── data_exfiltration.py     # 数据外泄模拟
├── external_tools/              # 外部工具集成
│   ├── gophish_integration.py   # Gophish集成
│   ├── aurora_integration.py    # Aurora-demos集成
│   └── pentest_agent_integration.py # PentestAgent集成
├── analysis/                    # 分析工具
│   ├── log_analyzer.py          # 日志分析
│   ├── network_analyzer.py      # 网络流量分析
│   └── report_generator.py      # 报告生成
├── docker/                      # Docker环境
│   ├── docker-compose.yml       # 内网环境定义
│   ├── victim_workstation/      # 受害者工作站
│   ├── file_server/             # 文件服务器
│   ├── mail_server/             # 邮件服务器
│   ├── web_server/              # Web服务器
│   └── database_server/         # 数据库服务器
├── results/                     # 结果输出
│   ├── logs/                    # 系统日志
│   ├── reports/                 # 分析报告
│   └── screenshots/             # 截图记录
└── docs/                        # 详细文档
    ├── ATTACK_CHAIN_DETAILS.md  # 攻击链详细说明
    ├── CONFIGURATION_GUIDE.md   # 配置指南
    └── TROUBLESHOOTING.md       # 故障排除
```

## 🔧 主要功能

### 1. 攻击链自动化执行
- 完整的5阶段攻击链自动执行
- 实时攻击状态监控
- 可视化攻击路径展示

### 2. 钓鱼平台集成
- 集成Gophish钓鱼邮件发送
- 自定义钓鱼邮件模板
- 着陆页面自动生成

### 3. 内网渗透仿真
- Docker容器化内网环境
- 真实的横向移动演示
- 多种权限提升技术

### 4. 数据分析与报告
- 实时攻击日志收集
- 网络流量分析
- 自动化报告生成

### 5. Web管理界面
- 统一管理控制台 (端口4257)
- 实时仿真状态监控
- 结果可视化展示

## 🎛️ 访问地址

启动后可通过以下地址访问各个系统：

| 服务 | 地址 | 说明 |
|------|------|------|
| 🦊 **银狐仿真主界面** | http://localhost:4257 | 主要管理界面 |
| 📧 **钓鱼邮件管理** | http://localhost:3333 | Gophish管理界面 |
| 🌐 **基础邮件系统** | http://localhost:5000 | 29项目邮件系统 |
| 🌍 **真实网络邮件** | http://localhost:5001 | 29-1项目邮件系统 |
| 🤖 **AI钓鱼检测** | http://localhost:5002 | 30项目AI系统 |
| 📊 **系统总览** | http://localhost:4257/overview | 系统状态监控 |

## 🔐 默认凭据

- **Gophish**: admin / [自动生成]
- **Webmail**: alice@seedemail.net / password123
- **内网服务器**: root / password (仅限仿真环境)

## ⚠️ 安全提醒

1. **仅用于教学研究** - 请勿用于非法活动
2. **隔离环境运行** - 建议在虚拟机中执行
3. **遵守法律法规** - 符合当地网络安全法规
4. **定期清理** - 实验结束后清理相关文件

## 📖 详细文档

- [攻击链详细说明](docs/ATTACK_CHAIN_DETAILS.md)
- [配置指南](docs/CONFIGURATION_GUIDE.md)
- [故障排除](docs/TROUBLESHOOTING.md)

## 🤝 技术支持

如遇问题，请参考故障排除文档或联系技术支持。

---
*基于SEED-Emulator网络仿真环境 | 集成现有seed-email-system资源*