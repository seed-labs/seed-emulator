#!/usr/bin/env python
"""
Gophish自动化配置工具
完全替代界面操作，通过API自动配置钓鱼平台
"""

import os
import sys
import time
import json
from typing import List, Dict, Optional
from gophish import Gophish
from gophish.models import *
import requests
import urllib3

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from config import GOPHISH_API_KEY, GOPHISH_HOST, SMTP_CONFIG, DEFAULT_PHISHING_URL
from ai_generator import AIPhishingGenerator

class GophishAutomation:
    def __init__(self):
        """初始化Gophish自动化工具"""
        self.api = Gophish(GOPHISH_API_KEY, host=GOPHISH_HOST, verify=False)
        self.ai_generator = AIPhishingGenerator()
        
        # 测试连接
        try:
            self.api.campaigns.get()
            print("✅ Gophish API连接成功")
        except Exception as e:
            print(f"❌ Gophish API连接失败: {e}")
            print("请确保Gophish服务正在运行，API密钥正确")
            sys.exit(1)
    
    def setup_smtp_profile(self, name: str = None) -> SMTP:
        """配置SMTP发送配置"""
        smtp_name = name or SMTP_CONFIG["name"]
        
        print(f"📧 配置SMTP发送配置: {smtp_name}")
        
        # 检查是否已存在
        try:
            existing_smtp = self.api.smtp.get()
            for smtp in existing_smtp:
                if smtp.name == smtp_name:
                    print(f"✅ SMTP配置已存在: {smtp_name}")
                    return smtp
        except:
            pass
        
        # 创建新的SMTP配置
        smtp = SMTP(
            name=smtp_name,
            host=SMTP_CONFIG["host"],
            from_address=f"安全团队 <{SMTP_CONFIG['from_address']}>",
            username=SMTP_CONFIG["username"],
            password=SMTP_CONFIG["password"],
            ignore_cert_errors=SMTP_CONFIG["ignore_cert_errors"],
            interface_type="SMTP"
        )
        
        try:
            smtp = self.api.smtp.post(smtp)
            print(f"✅ SMTP配置创建成功: {smtp_name}")
            return smtp
        except Exception as e:
            print(f"❌ SMTP配置创建失败: {e}")
            return None
    
    def create_user_group(self, group_name: str, users: List[Dict]) -> Group:
        """创建用户组"""
        print(f"👥 创建用户组: {group_name}")
        
        # 检查是否已存在
        try:
            existing_groups = self.api.groups.get()
            for group in existing_groups:
                if group.name == group_name:
                    print(f"✅ 用户组已存在: {group_name}")
                    return group
        except:
            pass
        
        # 创建用户列表
        targets = []
        for user in users:
            target = User(
                first_name=user.get('first_name', ''),
                last_name=user.get('last_name', ''),
                email=user['email'],
                position=user.get('position', '')
            )
            targets.append(target)
        
        # 创建用户组
        group = Group(name=group_name, targets=targets)
        
        try:
            group = self.api.groups.post(group)
            print(f"✅ 用户组创建成功: {group_name} ({len(targets)}个用户)")
            return group
        except Exception as e:
            print(f"❌ 用户组创建失败: {e}")
            return None
    
    def create_email_template(self, template_data: Dict) -> Template:
        """创建邮件模板"""
        template_name = template_data['name']
        print(f"📝 创建邮件模板: {template_name}")
        
        # 检查是否已存在
        try:
            existing_templates = self.api.templates.get()
            for tmpl in existing_templates:
                if tmpl.name == template_name:
                    print(f"✅ 邮件模板已存在: {template_name}")
                    return tmpl
        except:
            pass
        
        # 创建邮件模板
        template = Template(
            name=template_name,
            subject=template_data.get('subject', '重要通知'),
            text=template_data.get('text', ''),
            html=template_data.get('html', ''),
            attachments=template_data.get('attachments', [])
        )
        
        try:
            template = self.api.templates.post(template)
            print(f"✅ 邮件模板创建成功: {template_name}")
            return template
        except Exception as e:
            print(f"❌ 邮件模板创建失败: {e}")
            return None
    
    def create_landing_page(self, page_data: Dict) -> Page:
        """创建钓鱼页面"""
        page_name = page_data['name']
        print(f"🌐 创建钓鱼页面: {page_name}")
        
        # 检查是否已存在
        try:
            existing_pages = self.api.pages.get()
            for pg in existing_pages:
                if pg.name == page_name:
                    print(f"✅ 钓鱼页面已存在: {page_name}")
                    return pg
        except:
            pass
        
        # 创建钓鱼页面
        page = Page(
            name=page_name,
            html=page_data['html'],
            capture_credentials=page_data.get('capture_credentials', True),
            capture_passwords=page_data.get('capture_passwords', True),
            redirect_url=page_data.get('redirect_url', '')
        )
        
        try:
            page = self.api.pages.post(page)
            print(f"✅ 钓鱼页面创建成功: {page_name}")
            return page
        except Exception as e:
            print(f"❌ 钓鱼页面创建失败: {e}")
            return None
    
    def create_campaign(self, 
                       campaign_name: str,
                       group_name: str,
                       template_name: str,
                       page_name: str,
                       smtp_name: str,
                       url: str = None) -> Campaign:
        """创建钓鱼活动"""
        print(f"🎯 创建钓鱼活动: {campaign_name}")
        
        phishing_url = url or DEFAULT_PHISHING_URL
        
        # 创建活动
        campaign = Campaign(
            name=campaign_name,
            groups=[Group(name=group_name)],
            template=Template(name=template_name),
            page=Page(name=page_name),
            smtp=SMTP(name=smtp_name),
            url=phishing_url
        )
        
        try:
            campaign = self.api.campaigns.post(campaign)
            print(f"✅ 钓鱼活动创建成功: {campaign_name}")
            print(f"📊 活动详情:")
            print(f"  - ID: {campaign.id}")
            print(f"  - 状态: {campaign.status}")
            print(f"  - 创建时间: {campaign.created_date}")
            print(f"  - 钓鱼URL: {phishing_url}")
            return campaign
        except Exception as e:
            print(f"❌ 钓鱼活动创建失败: {e}")
            return None
    
    def get_campaign_results(self, campaign_id: int = None) -> Dict:
        """获取活动结果"""
        try:
            if campaign_id:
                campaign = self.api.campaigns.get(campaign_id)
                campaigns = [campaign]
            else:
                campaigns = self.api.campaigns.get()
            
            results = {}
            for campaign in campaigns:
                stats = {
                    'name': campaign.name,
                    'status': campaign.status,
                    'created_date': str(campaign.created_date),
                    'results': []
                }
                
                for result in campaign.results:
                    stats['results'].append({
                        'email': result.email,
                        'first_name': result.first_name,
                        'last_name': result.last_name,
                        'status': result.status,
                        'ip': result.ip,
                        'latitude': result.latitude,
                        'longitude': result.longitude
                    })
                
                # 统计数据
                total = len(campaign.results)
                sent = len([r for r in campaign.results if r.status in ['Email Sent', 'Clicked Link', 'Submitted Data']])
                clicked = len([r for r in campaign.results if r.status in ['Clicked Link', 'Submitted Data']])
                submitted = len([r for r in campaign.results if r.status == 'Submitted Data'])
                
                stats['summary'] = {
                    'total': total,
                    'sent': sent,
                    'clicked': clicked,
                    'submitted': submitted,
                    'click_rate': round(clicked/sent*100, 2) if sent > 0 else 0,
                    'submission_rate': round(submitted/sent*100, 2) if sent > 0 else 0
                }
                
                results[campaign.id] = stats
            
            return results
        except Exception as e:
            print(f"❌ 获取活动结果失败: {e}")
            return {}
    
    def list_all_resources(self) -> Dict:
        """列出所有资源"""
        resources = {}
        
        try:
            # 获取用户组
            groups = self.api.groups.get()
            resources['groups'] = [{'id': g.id, 'name': g.name, 'users': len(g.targets)} for g in groups]
            
            # 获取邮件模板
            templates = self.api.templates.get()
            resources['templates'] = [{'id': t.id, 'name': t.name, 'subject': t.subject} for t in templates]
            
            # 获取钓鱼页面
            pages = self.api.pages.get()
            resources['pages'] = [{'id': p.id, 'name': p.name} for p in pages]
            
            # 获取SMTP配置
            smtp_profiles = self.api.smtp.get()
            resources['smtp'] = [{'id': s.id, 'name': s.name, 'host': s.host} for s in smtp_profiles]
            
            # 获取活动
            campaigns = self.api.campaigns.get()
            resources['campaigns'] = [{'id': c.id, 'name': c.name, 'status': c.status} for c in campaigns]
            
        except Exception as e:
            print(f"❌ 获取资源列表失败: {e}")
        
        return resources
    
    def quick_setup_demo(self):
        """快速演示设置"""
        print("🚀 开始快速演示设置...")
        
        # 1. 设置SMTP
        smtp = self.setup_smtp_profile()
        if not smtp:
            return
        
        # 2. 创建测试用户组
        test_users = [
            {
                'first_name': '张',
                'last_name': '三',
                'email': 'test1@example.com',
                'position': '软件工程师'
            },
            {
                'first_name': '李',
                'last_name': '四',
                'email': 'test2@example.com',
                'position': '产品经理'
            }
        ]
        
        group = self.create_user_group("演示用户组", test_users)
        if not group:
            return
        
        # 3. 生成AI邮件模板
        print("🤖 使用AI生成邮件模板...")
        ai_template = self.ai_generator.generate_phishing_email(
            campaign_type="security_alert",
            target_company="XX科技公司"
        )
        
        if ai_template:
            template = self.create_email_template(ai_template)
        else:
            # 使用默认模板
            template_data = {
                'name': '默认安全警告模板',
                'subject': '【紧急】您的账户存在安全风险',
                'text': '我们检测到您的账户存在异常登录行为，请立即点击以下链接验证您的身份：{{.URL}}',
                'html': '''
                <html>
                <body>
                <h2>🔒 账户安全警告</h2>
                <p>尊敬的用户，</p>
                <p>我们的安全系统检测到您的账户存在<strong>异常登录行为</strong>。</p>
                <p>为了保护您的账户安全，请立即点击下方按钮验证您的身份：</p>
                <p><a href="{{.URL}}" style="background-color: #ff4444; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">立即验证</a></p>
                <p>如果您未进行此操作，请忽略此邮件。</p>
                <p>谢谢！<br>安全团队</p>
                </body>
                </html>
                '''
            }
            template = self.create_email_template(template_data)
        
        if not template:
            return
        
        # 4. 生成AI钓鱼页面
        print("🤖 使用AI生成钓鱼页面...")
        ai_page = self.ai_generator.generate_landing_page(
            page_type="login",
            company_name="XX科技公司",
            style="corporate"
        )
        
        if ai_page:
            page = self.create_landing_page(ai_page)
        else:
            # 使用默认页面
            page_data = {
                'name': '默认登录验证页面',
                'html': '''
                <!DOCTYPE html>
                <html>
                <head>
                    <title>账户验证</title>
                    <meta charset="utf-8">
                    <style>
                        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
                        .container { max-width: 400px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                        .logo { text-align: center; margin-bottom: 30px; }
                        .form-group { margin-bottom: 20px; }
                        label { display: block; margin-bottom: 5px; font-weight: bold; }
                        input[type="email"], input[type="password"] { width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 4px; font-size: 16px; }
                        .btn { width: 100%; padding: 12px; background: #007bff; color: white; border: none; border-radius: 4px; font-size: 16px; cursor: pointer; }
                        .btn:hover { background: #0056b3; }
                        .warning { background: #fff3cd; border: 1px solid #ffeaa7; padding: 10px; border-radius: 4px; margin-bottom: 20px; }
                    </style>
                </head>
                <body>
                    {{.Tracker}}
                    <div class="container">
                        <div class="logo">
                            <h2>🔒 账户安全验证</h2>
                        </div>
                        <div class="warning">
                            ⚠️ 检测到异常登录，请验证您的身份
                        </div>
                        <form method="post" action="">
                            <div class="form-group">
                                <label>邮箱地址：</label>
                                <input type="email" name="email" required>
                            </div>
                            <div class="form-group">
                                <label>密码：</label>
                                <input type="password" name="password" required>
                            </div>
                            <button type="submit" class="btn">验证身份</button>
                        </form>
                    </div>
                </body>
                </html>
                ''',
                'capture_credentials': True,
                'capture_passwords': True
            }
            page = self.create_landing_page(page_data)
        
        if not page:
            return
        
        # 5. 创建活动
        campaign = self.create_campaign(
            campaign_name="安全意识培训演示",
            group_name=group.name,
            template_name=template.name,
            page_name=page.name,
            smtp_name=smtp.name,
            url="http://localhost:5001"  # 指向我们的XSS服务器作为示例
        )
        
        if campaign:
            print("\n🎉 演示设置完成！")
            print(f"📊 访问 {GOPHISH_HOST} 查看活动详情")
            print(f"🌐 钓鱼页面将在用户点击邮件链接时显示")

def main():
    """主函数"""
    automation = GophishAutomation()
    
    print("🎯 Gophish自动化配置工具")
    print("=" * 50)
    
    while True:
        print("\n请选择操作：")
        print("1. 快速演示设置")
        print("2. 创建SMTP配置")
        print("3. 创建用户组")
        print("4. 生成AI邮件模板")
        print("5. 生成AI钓鱼页面")
        print("6. 创建钓鱼活动")
        print("7. 查看活动结果")
        print("8. 列出所有资源")
        print("9. 退出")
        
        choice = input("\n请输入选择 (1-9): ").strip()
        
        if choice == '1':
            automation.quick_setup_demo()
        
        elif choice == '2':
            name = input("输入SMTP配置名称 (默认: QQ邮箱服务器): ").strip() or None
            automation.setup_smtp_profile(name)
        
        elif choice == '3':
            group_name = input("输入用户组名称: ").strip()
            if group_name:
                users = []
                while True:
                    email = input("输入用户邮箱 (直接回车结束): ").strip()
                    if not email:
                        break
                    first_name = input("姓: ").strip()
                    last_name = input("名: ").strip()
                    position = input("职位: ").strip()
                    users.append({
                        'email': email,
                        'first_name': first_name,
                        'last_name': last_name,
                        'position': position
                    })
                
                if users:
                    automation.create_user_group(group_name, users)
        
        elif choice == '4':
            campaign_type = input("钓鱼类型 (security_alert/system_update/account_verification): ").strip() or "security_alert"
            company = input("目标公司名称: ").strip() or "XX公司"
            
            # 显示可用的真实邮件模板
            real_emails = automation.ai_generator.get_available_real_emails()
            if real_emails:
                print("\n可用的真实邮件模板：")
                for i, email in enumerate(real_emails, 1):
                    print(f"  {i}. {os.path.basename(email)}")
                
                ref_choice = input("选择参考邮件编号 (直接回车跳过): ").strip()
                reference_email = None
                if ref_choice.isdigit() and 1 <= int(ref_choice) <= len(real_emails):
                    reference_email = real_emails[int(ref_choice) - 1]
            else:
                reference_email = None
            
            template_data = automation.ai_generator.generate_phishing_email(
                campaign_type=campaign_type,
                target_company=company,
                reference_email=reference_email
            )
            
            if template_data:
                automation.create_email_template(template_data)
        
        elif choice == '5':
            page_type = input("页面类型 (login/verification/update_info): ").strip() or "login"
            company = input("公司名称: ").strip() or "XX公司"
            style = input("设计风格 (corporate/modern/minimal): ").strip() or "corporate"
            
            page_data = automation.ai_generator.generate_landing_page(
                page_type=page_type,
                company_name=company,
                style=style
            )
            
            if page_data:
                automation.create_landing_page(page_data)
        
        elif choice == '6':
            campaign_name = input("活动名称: ").strip()
            group_name = input("用户组名称: ").strip()
            template_name = input("邮件模板名称: ").strip()
            page_name = input("钓鱼页面名称: ").strip()
            smtp_name = input("SMTP配置名称: ").strip()
            url = input("钓鱼URL (默认: http://localhost:8080): ").strip() or "http://localhost:8080"
            
            if all([campaign_name, group_name, template_name, page_name, smtp_name]):
                automation.create_campaign(campaign_name, group_name, template_name, page_name, smtp_name, url)
        
        elif choice == '7':
            campaign_id = input("活动ID (直接回车查看所有): ").strip()
            campaign_id = int(campaign_id) if campaign_id.isdigit() else None
            
            results = automation.get_campaign_results(campaign_id)
            if results:
                for cid, data in results.items():
                    print(f"\n📊 活动: {data['name']} (ID: {cid})")
                    print(f"状态: {data['status']}")
                    print(f"创建时间: {data['created_date']}")
                    summary = data['summary']
                    print(f"统计: {summary['sent']}发送, {summary['clicked']}点击, {summary['submitted']}提交")
                    print(f"点击率: {summary['click_rate']}%, 提交率: {summary['submission_rate']}%")
        
        elif choice == '8':
            resources = automation.list_all_resources()
            for resource_type, items in resources.items():
                print(f"\n📋 {resource_type.title()}:")
                for item in items:
                    print(f"  - {item}")
        
        elif choice == '9':
            print("再见！")
            break
        
        else:
            print("无效选择，请重试")

if __name__ == "__main__":
    main()
