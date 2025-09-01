# Gophish 钓鱼平台配置指南

## 🚀 快速开始

### 1. 启动所有服务
```bash
chmod +x start_simulation.sh
./start_simulation.sh
```

### 2. 访问管理界面
- URL: https://localhost:3333
- 默认用户名: admin
- 密码: 在终端启动时显示（类似：4304d5255378177d）

## 📧 配置QQ邮箱发送

### 步骤1: 进入发送配置
进入 "Sending Profiles" -> "New Profile"

### 步骤2: 填写QQ邮箱配置
```
Name: QQ邮箱测试
From: 809050685@qq.com  
Host: smtp.qq.com:465
Username: 809050685@qq.com
Password: xutqpejdkpfcbbhi
```

⚠️ **重要设置：**
- 勾选 "Ignore Certificate Errors"
- 确保端口是 465 (SSL)

## 📬 创建钓鱼邮件模板

### 模板示例1: 系统升级通知
```
Subject: 【紧急】系统安全升级通知
内容: 
尊敬的用户，

我们的系统将进行重要安全升级，请立即点击以下链接完成必要的验证：
{{.URL}}

如不及时处理，您的账户可能被暂时冻结。

IT部门
```

### 模板示例2: 工资条通知  
```
Subject: 本月工资条查看通知
内容:
您好，

本月工资条已生成，请点击链接查看详情：
{{.URL}}

点击查看: {{.URL}}

财务部
```

### 模板示例3: 安全警告
```
Subject: 账户异常登录提醒
内容:
检测到您的账户在异地登录，为保障账户安全，请立即验证：
{{.URL}}

如非本人操作，请立即点击链接修改密码。

安全中心
```

## 👥 创建目标群组

### 步骤1: 进入用户管理
进入 "Users & Groups" -> "New Group"

### 步骤2: 添加测试用户
```
First Name: 测试
Last Name: 用户  
Email: test@example.com
Position: 员工
```

## 🎣 创建钓鱼页面

### 步骤1: 进入页面管理
进入 "Landing Pages" -> "New Page"

### 步骤2: 选择模板类型
- 企业内部系统登录
- 邮箱登录页面  
- 在线银行登录
- 社交媒体登录

### 示例登录页面代码：
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

## 🎯 启动钓鱼活动

### 步骤1: 创建活动
进入 "Campaigns" -> "New Campaign"

### 步骤2: 配置活动参数
- **Name**: 测试钓鱼活动
- **Email Template**: 选择之前创建的模板
- **Landing Page**: 选择钓鱼页面
- **URL**: http://localhost:8080 (Gophish会自动生成)
- **Sending Profile**: 选择QQ邮箱配置
- **Groups**: 选择目标用户组

### 步骤3: 设置发送时间
- 立即发送：选择当前时间
- 定时发送：设置未来时间

## 📊 查看攻击结果

### 1. Gophish统计
在 "Results" 页面查看：
- 📧 邮件发送状态
- 👆 点击链接的用户  
- 🔑 输入凭据的用户
- 🌍 地理位置信息
- ⏰ 时间线分析

### 2. 损失评估仪表板
访问 http://localhost:5000 查看：
- 💰 预估经济损失
- 📈 攻击类型分布
- ⚠️ 风险等级评估
- 📋 详细攻击日志

## 🛡️ 漏洞服务器说明

### XSS漏洞服务器 (端口5001)
- **用途**: 模拟企业反馈系统
- **漏洞**: 存储型XSS漏洞
- **测试方法**: 在反馈中输入 `<script>alert('XSS攻击成功！')</script>`
- **风险**: 用户数据泄露、会话劫持、恶意代码执行

### SQL注入服务器 (端口5002)  
- **用途**: 模拟员工查询系统
- **漏洞**: SQL注入漏洞
- **测试方法**: 在员工ID中输入 `1001' OR '1'='1`
- **风险**: 数据库完全暴露、敏感信息泄露

### Heartbleed仿真 (端口5003)
- **用途**: 模拟SSL/TLS服务
- **漏洞**: CVE-2014-0160 Heartbleed
- **测试方法**: 点击"执行Heartbleed测试"
- **风险**: 私钥泄露、内存数据暴露、系统全面沦陷

## 🔄 完整使用流程

### 第一阶段：钓鱼攻击
1. ✅ 配置Gophish邮箱设置
2. 📧 创建诱人的钓鱼邮件
3. 🎯 选择目标用户群体  
4. 🚀 发送钓鱼邮件
5. ⏰ 等待用户点击链接

### 第二阶段：钓后利用
1. 👆 用户点击邮件链接
2. 🔑 引导用户输入凭据
3. 🌐 将用户重定向到漏洞服务器
4. ⚠️ 触发XSS/SQL注入/Heartbleed攻击
5. 📊 记录攻击日志和损失数据

### 第三阶段：损失评估
1. 📈 查看实时攻击统计
2. 💰 评估潜在经济损失
3. 📋 分析攻击影响范围
4. 📊 生成风险评估报告

## 💡 最佳实践建议

### 邮件内容优化
- 🎭 使用紧急性语言（"立即"、"紧急"、"24小时内"）
- 🏢 模仿官方机构（IT部门、财务部、安全中心）
- 🔗 使用简短易记的链接
- ⚠️ 添加威胁元素（账户冻结、数据丢失）

### 钓鱼页面设计
- 🎨 高度还原目标网站外观
- 🔒 使用HTTPS增加可信度
- 📱 确保移动端兼容性
- ⚡ 页面加载速度要快

### 数据收集策略
- 📊 记录所有用户交互
- 🌍 收集地理位置信息
- 🕒 分析访问时间模式
- 📱 记录设备和浏览器信息

## ⚠️ 安全提醒

**本系统仅用于安全研究和员工安全意识培训，请勿用于非法用途！**

- 仅在授权环境中使用
- 不得攻击真实用户
- 遵守相关法律法规
- 保护测试数据安全
