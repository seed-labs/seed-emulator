# 🎯 Gophish AI自动化配置工具

这是一个完全自动化的Gophish配置工具，集成了OpenAI GPT来生成高质量的钓鱼邮件模板和钓鱼页面，完全替代手动界面操作。

## 🚀 快速开始

### 1. 环境准备

```bash
# 激活conda环境
conda activate gophish-test

# 确保Gophish正在运行
cd ..
./gophish
```

### 2. 配置验证

确保以下配置正确：

- **Gophish API Key**: `a78b08ef30d9dc06074a49d155ff14f7d586d65007702a9c4170384d9c00d588`
- **OpenAI API**: 已配置有效的API密钥和端点
- **QQ邮箱**: `809050685@qq.com` 授权码 `xutqpejdkpfcbbhi`

### 3. 一键完整设置

```bash
python batch_generator.py
# 选择选项 4: 创建完整实验环境
```

这将自动完成：
- ✅ 配置SMTP服务器
- ✅ 创建多个测试用户组
- ✅ 使用AI生成5种不同类型的钓鱼邮件模板
- ✅ 生成对应的钓鱼页面
- ✅ 创建示例钓鱼活动
- ✅ 生成详细的设置报告

## 📁 文件结构

```
gophish_automation/
├── config.py              # 配置文件
├── ai_generator.py         # AI内容生成器
├── gophish_automation.py   # Gophish自动化工具
├── batch_generator.py      # 批量生成器
└── README.md              # 说明文档
```

## 🤖 AI生成器功能

### 邮件模板生成

支持以下钓鱼场景：
- 🔒 **security_alert**: 安全警告类邮件
- 🔄 **system_update**: 系统升级通知
- ✅ **account_verification**: 账户验证
- ⚠️ **urgent_action**: 紧急操作要求
- 🎁 **reward_notification**: 奖励通知

### 钓鱼页面生成

支持以下页面类型：
- 🔐 **login**: 登录页面
- 🛡️ **verification**: 身份验证页面
- 📝 **update_info**: 信息更新页面
- 🔍 **security_check**: 安全检查页面
- 📄 **document_access**: 文档访问页面
- 📊 **survey**: 调查问卷页面

## 🛠️ 使用方法

### 方法1: 交互式配置

```bash
python gophish_automation.py
```

提供完整的交互式菜单：
1. 快速演示设置
2. 创建SMTP配置
3. 创建用户组
4. 生成AI邮件模板
5. 生成AI钓鱼页面
6. 创建钓鱼活动
7. 查看活动结果
8. 列出所有资源

### 方法2: 批量生成

```bash
python batch_generator.py
```

功能选项：
1. 分析所有真实邮件模板
2. 批量生成钓鱼内容
3. 上传生成的内容到Gophish
4. 创建完整实验环境 ⭐
5. 查看生成场景

### 方法3: 单独使用AI生成器

```bash
python ai_generator.py
```

## 🎨 AI增强功能

### 真实邮件模板集成

系统会自动分析 `../mail_template/` 目录下的真实邮件：
- 📧 Google安全提醒
- 🔒 MetaMask账户通知
- ☁️ AWS欢迎邮件
- 📱 各种企业邮件模板

AI会基于这些真实邮件的风格和格式生成更加逼真的钓鱼内容。

### 智能内容优化

- **语言风格匹配**: 根据目标公司调整语言风格
- **格式适配**: 模仿真实企业邮件的HTML格式
- **紧迫感营造**: 自动添加时间压力和行动召唤
- **可信度增强**: 包含适当的免责声明和联系信息

## 📊 监控和结果

### 活动结果查看

```bash
# 通过工具查看
python gophish_automation.py
# 选择选项 7: 查看活动结果

# 或直接访问Gophish界面
open https://localhost:3333
```

### 损失评估集成

钓鱼结果会自动同步到损失评估仪表板：
```
http://localhost:5888
```

## 🔧 高级配置

### 自定义SMTP配置

修改 `config.py` 中的SMTP设置：

```python
SMTP_CONFIG = {
    "name": "自定义邮箱服务器",
    "host": "your-smtp-host:port",
    "from_address": "your-email@domain.com",
    "username": "your-username",
    "password": "your-password",
    "ignore_cert_errors": True
}
```

### 自定义AI提示词

在 `ai_generator.py` 中修改 `system_prompt` 和 `user_prompt` 来定制AI生成的内容风格。

### 添加新的钓鱼场景

在 `batch_generator.py` 的 `generate_campaign_scenarios()` 方法中添加新场景：

```python
{
    'name': '自定义场景名称',
    'type': 'custom_type',
    'company': '目标公司',
    'description': '场景描述'
}
```

## 🚨 安全提醒

⚠️ **重要警告**：
- 仅在授权的测试环境中使用
- 不得对真实用户进行未授权的钓鱼攻击
- 遵守相关法律法规和企业政策
- 实验结束后及时清理所有数据

## 📈 实验流程

### 完整实验步骤

1. **环境准备** (5分钟)
   ```bash
   conda activate gophish-test
   cd gophish_automation
   ```

2. **快速设置** (10分钟)
   ```bash
   python batch_generator.py
   # 选择选项 4
   ```

3. **启动钓鱼活动** (即时)
   - 访问 `https://localhost:3333`
   - 查看自动创建的活动
   - 开始发送钓鱼邮件

4. **监控结果** (持续)
   - Gophish界面: `https://localhost:3333`
   - 损失评估: `http://localhost:5888`
   - 漏洞利用: `http://localhost:5001-5003`

5. **钓后利用** (进阶)
   - 引导"中招"用户访问漏洞服务器
   - 演示XSS、SQL注入、Heartbleed攻击
   - 收集攻击数据和损失评估

## 🎯 示例场景

### 场景1: 技术部门安全意识测试

```bash
# 生成针对技术人员的钓鱼邮件
python gophish_automation.py
# 选择: 生成AI邮件模板 -> security_alert -> "XX科技公司"
```

### 场景2: 管理层商业邮件诈骗

```bash
# 生成针对管理层的奖励通知
python gophish_automation.py
# 选择: 生成AI邮件模板 -> reward_notification -> "集团总部"
```

### 场景3: 全员系统升级通知

```bash
# 使用AWS风格的系统更新通知
# 系统会自动参考真实的AWS邮件模板
```

## 📝 日志和报告

系统会自动生成：
- **设置报告**: `gophish_setup_report.json`
- **活动日志**: Gophish内置日志
- **攻击数据**: 损失评估数据库

## 🔗 集成说明

本工具与现有的实验环境完全集成：
- 🎣 **Gophish**: 钓鱼平台核心
- 🤖 **OpenAI GPT**: 内容生成
- 📊 **损失评估仪表板**: 结果可视化
- 🌐 **漏洞服务器**: 钓后利用
- 📧 **QQ邮箱**: 真实邮件发送

## 💡 最佳实践

1. **逐步测试**: 先创建小规模测试组
2. **内容验证**: 检查生成的邮件和页面质量
3. **结果监控**: 及时查看钓鱼效果
4. **安全评估**: 分析攻击成功率和用户行为
5. **培训跟进**: 基于结果进行安全意识培训

---

🎉 **开始您的AI驱动的钓鱼安全测试之旅吧！**
