# 银狐木马攻击模拟自动化框架集成

## 概述

本目录包含了完整的自动化框架集成，用于实现银狐木马攻击链的自动化执行和评估。集成了三个主要的自动化框架：

- **Gophish**: 钓鱼平台，用于自动化钓鱼邮件发送和跟踪
- **Aurora-demos**: 攻击链自动化框架，用于编排完整的攻击链执行
- **PentestAgent**: 渗透测试自动化框架，用于侦察和漏洞评估

## 文件结构

```
automation_frameworks/
├── unified_integrator.py          # 统一集成器主文件
├── unified_config.json            # 统一配置文件
├── gophish_integration.py         # Gophish集成模块
├── gophish_config.json            # Gophish配置文件
├── aurora_demos_integration.py    # Aurora-demos集成模块
├── aurora_config.yaml             # Aurora-demos配置文件
├── pentest_agent_integration.py   # PentestAgent集成模块
└── pentest_agent_config.json      # PentestAgent配置文件
```

## 安装和配置

### 1. 安装依赖

```bash
pip install requests pyyaml
```

### 2. 配置各个框架

#### Gophish配置
编辑 `gophish_config.json`：
```json
{
  "api_key": "your-gophish-api-key",
  "api_url": "http://localhost:3333/api"
}
```

#### Aurora-demos配置
编辑 `aurora_config.yaml`：
```yaml
aurora_path: "/opt/aurora-demos"
working_directory: "/tmp/aurora-workspace"
```

#### PentestAgent配置
编辑 `pentest_agent_config.json`：
```json
{
  "api_url": "http://localhost:5000/api",
  "api_key": "your-pentest-agent-api-key"
}
```

### 3. 启动外部服务

确保以下服务正在运行：

- Gophish服务器 (端口3333)
- Aurora-demos框架
- PentestAgent服务 (端口5000)

## 使用方法

### 基本使用

```python
from automation_frameworks.unified_integrator import UnifiedAutomationIntegrator

# 初始化集成器
integrator = UnifiedAutomationIntegrator()

# 运行完整集成攻击模拟
results = integrator.run_integrated_attack_simulation()

# 生成报告
integrator.generate_integrated_report(results, "/path/to/report.json")
```

### 分阶段执行

```python
# 执行特定阶段
phases = ["recon", "phishing", "execution"]
results = integrator.run_phased_attack_simulation(phases)
```

### 单独使用各个框架

#### Gophish钓鱼活动

```python
from automation_frameworks.gophish_integration import GophishIntegration

gophish = GophishIntegration()
infrastructure = gophish.setup_phishing_infrastructure()
results = gophish.run_phishing_campaign(infrastructure)
```

#### Aurora-demos攻击链

```python
from automation_frameworks.aurora_demos_integration import AuroraDemosIntegration

aurora = AuroraDemosIntegration()
results = aurora.run_silverfox_simulation()
```

#### PentestAgent渗透测试

```python
from automation_frameworks.pentest_agent_integration import PentestAgentIntegration

pentest = PentestAgentIntegration()
targets = ["192.168.1.100", "mail-server"]
results = pentest.run_comprehensive_pentest(targets)
```

## 配置选项

### 统一配置 (unified_config.json)

- `frameworks`: 启用/禁用各个框架
- `targets`: 攻击目标列表
- `attack_phases`: 攻击阶段配置
- `simulation_settings`: 模拟运行设置
- `reporting`: 报告生成配置
- `logging`: 日志配置
- `security`: 安全设置

### 框架特定配置

每个框架都有自己的配置文件，包含API密钥、路径设置和特定选项。

## 安全注意事项

1. **测试环境**: 仅在隔离的测试环境中运行
2. **API密钥**: 妥善保管API密钥，不要提交到版本控制
3. **网络隔离**: 确保测试网络与生产网络隔离
4. **清理**: 运行完成后清理所有测试数据和痕迹

## 故障排除

### 常见问题

1. **连接失败**: 检查框架服务是否正在运行
2. **认证失败**: 验证API密钥配置
3. **超时错误**: 调整超时设置或检查网络连接
4. **权限错误**: 确保用户有执行权限

### 日志查看

```bash
# 查看集成器日志
tail -f /var/log/silverfox/integrator.log

# 查看框架特定日志
tail -f /var/log/gophish/gophish.log
tail -f /var/log/aurora/aurora.log
tail -f /var/log/pentest-agent/agent.log
```

## 扩展开发

### 添加新框架

1. 创建框架集成类
2. 实现标准接口方法
3. 添加配置文件
4. 更新统一集成器

### 自定义攻击链

在 `aurora_config.yaml` 中定义自定义攻击阶段：

```yaml
custom_chain:
  name: "自定义攻击链"
  stages:
    - reconnaissance
    - custom_phase
    - cleanup
```

## 报告和分析

生成的报告包含：

- 执行状态和结果
- 各阶段详细日志
- 性能指标
- 安全建议

报告格式支持JSON、HTML和PDF。

## 许可证

本项目遵循与主项目相同的许可证。