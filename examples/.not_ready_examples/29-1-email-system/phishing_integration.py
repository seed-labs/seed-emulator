#!/usr/bin/env python3
"""
SEED 邮件系统 + Gophish 钓鱼集成
将29-1邮件系统与gophish钓鱼平台结合，创建完整的钓鱼实验环境
"""

import subprocess
import json
import time
import os
import requests
import sys
from pathlib import Path

class GophishIntegrator:
    """Gophish与SEED邮件系统集成器"""
    
    def __init__(self):
        self.gophish_path = "../gophish基础实验"
        self.gophish_url = "https://localhost:3333"
        self.api_key = ""
        self.mail_servers = [
            {"name": "QQ邮箱", "domain": "qq.com", "smtp_port": "2200"},
            {"name": "163邮箱", "domain": "163.com", "smtp_port": "2201"},
            {"name": "Gmail", "domain": "gmail.com", "smtp_port": "2202"},
            {"name": "Outlook", "domain": "outlook.com", "smtp_port": "2203"},
            {"name": "企业邮箱", "domain": "company.cn", "smtp_port": "2204"},
            {"name": "自建邮箱", "domain": "startup.net", "smtp_port": "2205"}
        ]
    
    def check_email_system_status(self):
        """检查29-1邮件系统状态"""
        print("🔍 检查SEED邮件系统状态...")
        
        if not os.path.exists("output/docker-compose.yml"):
            print("❌ 邮件系统未部署，请先运行: python3 email_realistic.py arm")
            return False
        
        # 检查容器状态
        try:
            result = subprocess.run(
                ["docker-compose", "-f", "output/docker-compose.yml", "ps", "--format", "json"],
                capture_output=True, text=True, cwd="."
            )
            
            if result.returncode != 0:
                print("❌ 无法获取容器状态")
                return False
            
            running_containers = 0
            mail_containers = 0
            
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    try:
                        container = json.loads(line)
                        if container.get('State') == 'running':
                            running_containers += 1
                        if 'mail-' in container.get('Name', ''):
                            mail_containers += 1
                            print(f"✅ {container['Name']}: {container['State']}")
                    except json.JSONDecodeError:
                        continue
            
            print(f"📊 系统状态: {running_containers} 个容器运行中，{mail_containers} 个邮件服务器")
            return mail_containers >= 6
            
        except Exception as e:
            print(f"❌ 检查容器状态失败: {e}")
            return False
    
    def setup_gophish_environment(self):
        """设置Gophish环境"""
        print("🎣 设置Gophish钓鱼平台...")
        
        gophish_dir = Path(self.gophish_path)
        if not gophish_dir.exists():
            print(f"❌ Gophish目录不存在: {self.gophish_path}")
            return False
        
        # 检查gophish二进制文件
        gophish_binary = gophish_dir / "gophish"
        if not gophish_binary.exists():
            print("❌ Gophish二进制文件不存在")
            return False
        
        print("✅ Gophish环境检查完成")
        return True
    
    def start_gophish_server(self):
        """启动Gophish服务器"""
        print("🚀 启动Gophish服务器...")
        
        gophish_dir = Path(self.gophish_path)
        
        # 启动gophish (在后台运行)
        try:
            process = subprocess.Popen(
                ["./gophish"],
                cwd=str(gophish_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # 等待服务器启动
            print("⏳ 等待Gophish服务器启动...")
            time.sleep(10)
            
            # 检查进程是否还在运行
            if process.poll() is None:
                print("✅ Gophish服务器启动成功")
                print(f"🌐 管理界面: {self.gophish_url}")
                return True
            else:
                stdout, stderr = process.communicate()
                print(f"❌ Gophish启动失败: {stderr}")
                return False
                
        except Exception as e:
            print(f"❌ 启动Gophish失败: {e}")
            return False
    
    def create_phishing_templates(self):
        """创建钓鱼邮件模板"""
        print("📧 创建钓鱼邮件模板...")
        
        templates = [
            {
                "name": "QQ邮箱安全通知",
                "subject": "【重要】QQ邮箱安全验证通知",
                "html": """
                <html>
                <body style="font-family: Arial, sans-serif;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                        <div style="text-align: center; margin-bottom: 30px;">
                            <img src="https://qzonestyle.gtimg.cn/qzone/vas/opensns/res/img/Connect_logo_7.png" alt="QQ邮箱" width="120">
                        </div>
                        <h2 style="color: #0066cc;">安全验证通知</h2>
                        <p>尊敬的用户，</p>
                        <p>我们检测到您的QQ邮箱存在异常登录行为，为了保护您的账户安全，请立即点击下方链接进行身份验证：</p>
                        <div style="text-align: center; margin: 30px 0;">
                            <a href="{{.URL}}" style="background-color: #0066cc; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px;">立即验证</a>
                        </div>
                        <p style="color: #666; font-size: 12px;">此邮件由系统自动发送，请勿回复。如有疑问，请联系客服。</p>
                        <p style="color: #666; font-size: 12px;">©2024 腾讯公司</p>
                    </div>
                </body>
                </html>
                """,
                "text": "QQ邮箱安全验证：请访问 {{.URL}} 完成身份验证"
            },
            {
                "name": "Gmail安全警报",
                "subject": "Security Alert: Suspicious Activity Detected",
                "html": """
                <html>
                <body style="font-family: 'Google Sans', Arial, sans-serif;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                        <div style="border-bottom: 1px solid #ddd; padding-bottom: 20px; margin-bottom: 30px;">
                            <img src="https://ssl.gstatic.com/accounts/ui/logo_2x.png" alt="Google" width="100">
                        </div>
                        <h2 style="color: #1a73e8;">Security Alert</h2>
                        <p>Hi there,</p>
                        <p>We've detected suspicious activity on your Gmail account. To protect your account, please verify your identity immediately.</p>
                        <div style="background-color: #fff3cd; border: 1px solid #ffeaa7; border-radius: 4px; padding: 15px; margin: 20px 0;">
                            <strong>⚠️ Action Required:</strong> Your account may be compromised
                        </div>
                        <div style="text-align: center; margin: 30px 0;">
                            <a href="{{.URL}}" style="background-color: #1a73e8; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px;">Secure My Account</a>
                        </div>
                        <p style="color: #666; font-size: 12px;">This is an automated message. Please do not reply.</p>
                        <p style="color: #666; font-size: 12px;">©2024 Google LLC</p>
                    </div>
                </body>
                </html>
                """,
                "text": "Gmail Security Alert: Please visit {{.URL}} to secure your account"
            },
            {
                "name": "企业IT通知",
                "subject": "【IT部门】紧急：系统维护通知",
                "html": """
                <html>
                <body style="font-family: Arial, sans-serif;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd;">
                        <div style="background-color: #f8f9fa; padding: 15px; margin-bottom: 20px;">
                            <h2 style="color: #d32f2f; margin: 0;">🚨 紧急系统维护通知</h2>
                        </div>
                        <p><strong>收件人：</strong> 全体员工</p>
                        <p><strong>发件人：</strong> IT部门</p>
                        <p><strong>时间：</strong> 2024年即日起</p>
                        
                        <hr style="border: 1px solid #eee; margin: 20px 0;">
                        
                        <p>各位同事：</p>
                        <p>由于检测到系统安全漏洞，IT部门将于今晚22:00进行紧急系统维护。为确保数据安全，请所有员工<strong>立即</strong>登录系统备份重要文件。</p>
                        
                        <div style="background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0;">
                            <strong>⚠️ 重要提醒：</strong><br>
                            维护期间系统将完全停机，未备份的数据可能丢失！
                        </div>
                        
                        <div style="text-align: center; margin: 30px 0;">
                            <a href="{{.URL}}" style="background-color: #dc3545; color: white; padding: 15px 40px; text-decoration: none; border-radius: 5px; font-weight: bold;">立即登录备份</a>
                        </div>
                        
                        <p>如有疑问，请联系IT支持: it-support@company.cn</p>
                        <p style="color: #666; font-size: 12px;">此邮件由IT部门发送 | company.cn</p>
                    </div>
                </body>
                </html>
                """,
                "text": "紧急系统维护：请访问 {{.URL}} 立即备份数据"
            }
        ]
        
        for template in templates:
            print(f"📝 创建模板: {template['name']}")
        
        print("✅ 钓鱼邮件模板创建完成")
        return templates
    
    def create_landing_pages(self):
        """创建钓鱼着陆页面"""
        print("🕸️ 创建钓鱼着陆页面...")
        
        pages = [
            {
                "name": "QQ邮箱登录页面",
                "html": """
                <!DOCTYPE html>
                <html>
                <head>
                    <title>QQ邮箱 - 安全验证</title>
                    <meta charset="utf-8">
                    <style>
                        body { font-family: Arial, sans-serif; background: #f5f5f5; margin: 0; padding: 20px; }
                        .container { max-width: 400px; margin: 50px auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                        .logo { text-align: center; margin-bottom: 30px; }
                        .form-group { margin-bottom: 20px; }
                        label { display: block; margin-bottom: 5px; color: #333; }
                        input[type="text"], input[type="password"] { width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 5px; box-sizing: border-box; }
                        .btn { width: 100%; padding: 12px; background: #0066cc; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }
                        .btn:hover { background: #0052a3; }
                        .warning { background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="logo">
                            <h2 style="color: #0066cc;">QQ邮箱安全验证</h2>
                        </div>
                        <div class="warning">
                            <strong>⚠️ 安全提醒：</strong> 检测到异常登录，请验证身份
                        </div>
                        <form method="post" action="/submit">
                            <div class="form-group">
                                <label>QQ号码或邮箱：</label>
                                <input type="text" name="username" required>
                            </div>
                            <div class="form-group">
                                <label>密码：</label>
                                <input type="password" name="password" required>
                            </div>
                            <button type="submit" class="btn">立即验证</button>
                        </form>
                        <p style="color: #666; font-size: 12px; text-align: center; margin-top: 20px;">
                            ©2024 腾讯公司 | 保护您的账户安全
                        </p>
                    </div>
                </body>
                </html>
                """
            },
            {
                "name": "Gmail登录页面",
                "html": """
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Gmail - Google Account Verification</title>
                    <meta charset="utf-8">
                    <style>
                        body { font-family: 'Google Sans', Arial, sans-serif; background: #fff; margin: 0; padding: 20px; }
                        .container { max-width: 450px; margin: 50px auto; border: 1px solid #dadce0; border-radius: 8px; padding: 40px; }
                        .logo { text-align: center; margin-bottom: 30px; }
                        .form-group { margin-bottom: 20px; }
                        label { display: block; margin-bottom: 8px; color: #202124; font-size: 14px; }
                        input[type="email"], input[type="password"] { width: 100%; padding: 12px 16px; border: 1px solid #dadce0; border-radius: 4px; box-sizing: border-box; font-size: 16px; }
                        input:focus { border-color: #1a73e8; outline: none; }
                        .btn { width: 100%; padding: 12px; background: #1a73e8; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; font-weight: 500; }
                        .btn:hover { background: #1557b0; }
                        .alert { background: #fef7e0; border: 1px solid #f9ab00; padding: 16px; border-radius: 4px; margin-bottom: 20px; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="logo">
                            <svg width="75" height="24" viewBox="0 0 75 24"><path fill="#4285F4" d="M36.3 12.2c0-.7-.1-1.4-.3-2H24v4.5h7c-.3 1.6-1.3 2.9-2.7 3.8v3.1h4.4c2.6-2.4 4.1-5.9 4.1-10.1z"/><path fill="#34A853" d="M24 24c3.7 0 6.8-1.2 9.1-3.3l-4.4-3.4c-1.2.8-2.8 1.3-4.7 1.3-3.6 0-6.6-2.4-7.7-5.7H11v3.5C13.3 21.1 18.2 24 24 24z"/><path fill="#FBBC04" d="M16.3 14.9c-.3-.8-.4-1.7-.4-2.6s.1-1.8.4-2.6V6.2H11C9.7 8.7 9.7 15.3 11 17.8l5.3-2.9z"/><path fill="#EA4335" d="M24 4.8c2 0 3.8.7 5.2 2l3.9-3.9C30.8 1.1 27.7 0 24 0 18.2 0 13.3 2.9 11 7.7l5.3 4.1c1.1-3.3 4.1-5.7 7.7-5.7z"/></svg>
                        </div>
                        <h1 style="font-size: 24px; color: #202124; margin-bottom: 8px;">Security Verification</h1>
                        <p style="color: #5f6368; margin-bottom: 24px;">Please sign in to verify your account</p>
                        <div class="alert">
                            <strong>⚠️ Security Alert:</strong> Suspicious activity detected on your account
                        </div>
                        <form method="post" action="/submit">
                            <div class="form-group">
                                <label>Email</label>
                                <input type="email" name="email" required>
                            </div>
                            <div class="form-group">
                                <label>Password</label>
                                <input type="password" name="password" required>
                            </div>
                            <button type="submit" class="btn">Verify Account</button>
                        </form>
                        <p style="color: #5f6368; font-size: 12px; text-align: center; margin-top: 24px;">
                            ©2024 Google LLC
                        </p>
                    </div>
                </body>
                </html>
                """
            }
        ]
        
        for page in pages:
            print(f"🌐 创建页面: {page['name']}")
        
        print("✅ 钓鱼着陆页面创建完成")
        return pages
    
    def create_user_groups(self):
        """创建目标用户组"""
        print("👥 创建目标用户组...")
        
        user_groups = [
            {
                "name": "QQ邮箱用户",
                "users": [
                    {"email": "zhangsan@qq.com", "first_name": "张", "last_name": "三"},
                    {"email": "lisi@qq.com", "first_name": "李", "last_name": "四"},
                    {"email": "wangwu@qq.com", "first_name": "王", "last_name": "五"}
                ]
            },
            {
                "name": "Gmail用户", 
                "users": [
                    {"email": "john@gmail.com", "first_name": "John", "last_name": "Smith"},
                    {"email": "jane@gmail.com", "first_name": "Jane", "last_name": "Doe"},
                    {"email": "mike@gmail.com", "first_name": "Mike", "last_name": "Johnson"}
                ]
            },
            {
                "name": "企业员工",
                "users": [
                    {"email": "admin@company.cn", "first_name": "管理", "last_name": "员"},
                    {"email": "hr@company.cn", "first_name": "人事", "last_name": "专员"},
                    {"email": "dev@company.cn", "first_name": "开发", "last_name": "工程师"}
                ]
            }
        ]
        
        for group in user_groups:
            print(f"👤 创建用户组: {group['name']} ({len(group['users'])} 个用户)")
        
        print("✅ 目标用户组创建完成")
        return user_groups
    
    def run_phishing_campaign(self):
        """运行钓鱼活动"""
        print("🎯 启动钓鱼活动...")
        
        campaigns = [
            {
                "name": "QQ邮箱安全验证活动",
                "template": "QQ邮箱安全通知",
                "page": "QQ邮箱登录页面",
                "group": "QQ邮箱用户",
                "smtp_server": "localhost:2200"
            },
            {
                "name": "Gmail安全警报活动",
                "template": "Gmail安全警报", 
                "page": "Gmail登录页面",
                "group": "Gmail用户",
                "smtp_server": "localhost:2202"
            },
            {
                "name": "企业IT紧急通知",
                "template": "企业IT通知",
                "page": "企业登录页面", 
                "group": "企业员工",
                "smtp_server": "localhost:2204"
            }
        ]
        
        for campaign in campaigns:
            print(f"📧 活动: {campaign['name']}")
            print(f"   📝 模板: {campaign['template']}")
            print(f"   🌐 页面: {campaign['page']}")
            print(f"   👥 目标: {campaign['group']}")
            print(f"   📬 SMTP: {campaign['smtp_server']}")
        
        print("✅ 钓鱼活动配置完成")
        return campaigns
    
    def generate_integration_guide(self):
        """生成集成指南"""
        guide = """
# 🎣 SEED邮件系统 + Gophish 钓鱼集成指南

## 🎯 集成概述
本指南展示如何将29-1邮件系统与gophish钓鱼平台结合，创建完整的钓鱼攻击实验环境。

## 🚀 快速开始

### 1. 启动邮件系统
```bash
# 在29-1-email-system目录下
python3 email_realistic.py arm
cd output && docker-compose up -d
```

### 2. 启动钓鱼集成
```bash
# 返回29-1目录
cd ..
python3 phishing_integration.py
```

### 3. 访问系统
- **Gophish管理**: https://localhost:3333
- **邮件系统监控**: http://localhost:8080/map.html
- **攻击统计面板**: http://localhost:5000

## 📧 邮件服务器配置

在Gophish中配置SMTP服务器：

### QQ邮箱SMTP
```
Host: localhost:2200
Username: system@qq.com
Password: [容器中设置的密码]
From: "QQ邮箱安全中心" <security@qq.com>
```

### Gmail SMTP
```
Host: localhost:2202
Username: security@gmail.com
Password: [容器中设置的密码]
From: "Gmail Security" <no-reply@gmail.com>
```

### 企业邮箱SMTP
```
Host: localhost:2204
Username: it-admin@company.cn
Password: [容器中设置的密码]
From: "IT部门" <it-support@company.cn>
```

## 🎯 钓鱼活动示例

### 活动1: QQ邮箱安全验证
- **目标**: QQ邮箱用户
- **场景**: 模拟账户异常，要求验证
- **着陆页**: 仿QQ邮箱登录页面

### 活动2: Gmail安全警报
- **目标**: Gmail用户
- **场景**: 检测到可疑活动
- **着陆页**: 仿Gmail登录页面

### 活动3: 企业IT紧急通知
- **目标**: 企业员工
- **场景**: 系统维护，要求备份
- **着陆页**: 企业内网登录页面

## 📊 监控和分析

### 实时监控
- 邮件发送状态
- 用户点击率
- 凭据获取情况
- 网络流量分析

### 数据分析
- 攻击成功率统计
- 用户行为分析
- 风险评估报告
- 防护建议生成

## 🛡️ 安全说明

⚠️ **重要提醒**：
1. 仅用于授权的安全测试和教育目的
2. 不得用于真实的恶意攻击
3. 确保在隔离环境中运行
4. 遵守相关法律法规

## 🎓 教学价值

### 学习目标
1. 理解钓鱼攻击的完整流程
2. 掌握邮件安全防护技术
3. 学习社会工程学攻击手法
4. 培养网络安全意识

### 实验场景
1. **邮件钓鱼**: 模拟真实钓鱼邮件攻击
2. **域名欺骗**: 使用相似域名迷惑用户
3. **凭据窃取**: 获取用户登录信息
4. **数据分析**: 分析攻击效果和用户行为

---
**生成时间**: $(date)
**项目**: SEED邮件系统钓鱼集成
**版本**: 29-1-phishing
        """
        
        with open("PHISHING_INTEGRATION_GUIDE.md", "w", encoding="utf-8") as f:
            f.write(guide)
        
        print("✅ 集成指南已生成: PHISHING_INTEGRATION_GUIDE.md")

def main():
    """主函数"""
    print("""
    ╭─────────────────────────────────────────────────────────────╮
    │           SEED邮件系统 + Gophish 钓鱼集成工具               │
    │                    29-1-phishing 版本                      │
    ╰─────────────────────────────────────────────────────────────╯
    """)
    
    integrator = GophishIntegrator()
    
    # 检查邮件系统状态
    if not integrator.check_email_system_status():
        print("❌ 请先启动29-1邮件系统")
        return
    
    # 设置Gophish环境
    if not integrator.setup_gophish_environment():
        print("❌ Gophish环境设置失败")
        return
    
    # 创建钓鱼组件
    templates = integrator.create_phishing_templates()
    pages = integrator.create_landing_pages()
    groups = integrator.create_user_groups()
    campaigns = integrator.run_phishing_campaign()
    
    # 生成集成指南
    integrator.generate_integration_guide()
    
    print(f"""
    
🎉 钓鱼集成配置完成！

📊 配置摘要:
   📧 邮件模板: {len(templates)} 个
   🌐 着陆页面: {len(pages)} 个  
   👥 用户组: {len(groups)} 个
   🎯 活动配置: {len(campaigns)} 个

🚀 下一步操作:
   1. 启动Gophish: cd {integrator.gophish_path} && ./gophish
   2. 访问管理界面: https://localhost:3333
   3. 导入配置文件进行钓鱼测试
   4. 查看集成指南: cat PHISHING_INTEGRATION_GUIDE.md

⚠️  安全提醒: 仅用于授权的安全测试和教育目的
    """)

if __name__ == "__main__":
    main()
