#!/usr/bin/env python
"""
Gophish AI自动化工具演示脚本
展示完整的钓鱼实验自动化流程
"""

import time
import os
from ai_generator import AIPhishingGenerator
from gophish_automation import GophishAutomation
from batch_generator import BatchPhishingGenerator

def print_section(title: str):
    """打印章节标题"""
    print(f"\n{'='*60}")
    print(f"🎯 {title}")
    print(f"{'='*60}")

def print_step(step: str):
    """打印步骤"""
    print(f"\n📋 {step}")
    print("-" * 40)

def demo_ai_content_generation():
    """演示AI内容生成"""
    print_section("AI内容生成演示")
    
    generator = AIPhishingGenerator()
    
    # 1. 显示可用的真实邮件模板
    print_step("1. 分析真实邮件模板")
    real_emails = generator.get_available_real_emails()
    print(f"发现 {len(real_emails)} 个真实邮件模板：")
    for i, email in enumerate(real_emails[:3], 1):  # 只显示前3个
        filename = os.path.basename(email)
        print(f"  {i}. {filename}")
        
        # 分析邮件
        analysis = generator.analyze_real_email(email)
        if analysis:
            print(f"     📧 主题: {analysis['subject'][:50]}...")
            print(f"     👤 发件人: {analysis['sender']}")
    
    # 2. 生成AI邮件模板
    print_step("2. 生成AI钓鱼邮件模板")
    
    scenarios = [
        ("安全警告", "security_alert", "XX科技公司"),
        ("系统更新", "system_update", "AWS"),
        ("账户验证", "account_verification", "企业内部")
    ]
    
    generated_templates = []
    
    for name, type_, company in scenarios:
        print(f"\n🤖 生成{name}类型邮件...")
        
        # 选择参考邮件
        reference_email = real_emails[0] if real_emails else None
        
        template = generator.generate_phishing_email(
            campaign_type=type_,
            target_company=company,
            reference_email=reference_email
        )
        
        if template:
            print(f"✅ 生成成功")
            print(f"   📝 主题: {template['subject']}")
            print(f"   📄 内容长度: {len(template['text'])} 字符")
            generated_templates.append(template)
        else:
            print(f"❌ 生成失败")
    
    # 3. 生成AI钓鱼页面
    print_step("3. 生成AI钓鱼页面")
    
    page_scenarios = [
        ("企业登录页", "login", "XX科技公司", "corporate"),
        ("安全验证页", "verification", "安全团队", "modern"),
        ("信息更新页", "update_info", "HR部门", "minimal")
    ]
    
    generated_pages = []
    
    for name, type_, company, style in page_scenarios:
        print(f"\n🌐 生成{name}...")
        
        page = generator.generate_landing_page(
            page_type=type_,
            company_name=company,
            style=style
        )
        
        if page:
            print(f"✅ 生成成功")
            print(f"   📄 HTML长度: {len(page['html'])} 字符")
            print(f"   🎨 样式: {style}")
            generated_pages.append(page)
        else:
            print(f"❌ 生成失败")
    
    return generated_templates, generated_pages

def demo_gophish_automation():
    """演示Gophish自动化配置"""
    print_section("Gophish自动化配置演示")
    
    automation = GophishAutomation()
    
    # 1. 配置SMTP
    print_step("1. 配置SMTP服务器")
    smtp = automation.setup_smtp_profile("演示_QQ邮箱")
    if smtp:
        print(f"✅ SMTP配置成功: {smtp.name}")
        print(f"   📧 服务器: {smtp.host}")
        print(f"   👤 发件人: {smtp.from_address}")
    
    # 2. 创建用户组
    print_step("2. 创建测试用户组")
    
    demo_users = [
        {'first_name': '张', 'last_name': '三', 'email': 'zhangsan@demo.com', 'position': '软件工程师'},
        {'first_name': '李', 'last_name': '四', 'email': 'lisi@demo.com', 'position': '产品经理'},
        {'first_name': '王', 'last_name': '五', 'email': 'wangwu@demo.com', 'position': '设计师'}
    ]
    
    group = automation.create_user_group("演示用户组", demo_users)
    if group:
        print(f"✅ 用户组创建成功: {group.name}")
        print(f"   👥 用户数量: {len(group.targets)}")
        for target in group.targets:
            print(f"   📧 {target.first_name}{target.last_name} ({target.email})")
    
    return automation, smtp, group

def demo_template_and_page_upload(automation, templates, pages):
    """演示模板和页面上传"""
    print_step("3. 上传邮件模板和钓鱼页面")
    
    uploaded_templates = []
    uploaded_pages = []
    
    # 上传邮件模板
    print("📧 上传邮件模板...")
    for i, template in enumerate(templates[:2], 1):  # 只上传前2个
        template['name'] = f"演示邮件模板_{i}"
        gophish_template = automation.create_email_template(template)
        if gophish_template:
            uploaded_templates.append(gophish_template)
            print(f"  ✅ 模板{i}上传成功: {gophish_template.name}")
    
    # 上传钓鱼页面
    print("\n🌐 上传钓鱼页面...")
    for i, page in enumerate(pages[:2], 1):  # 只上传前2个
        page['name'] = f"演示钓鱼页面_{i}"
        gophish_page = automation.create_landing_page(page)
        if gophish_page:
            uploaded_pages.append(gophish_page)
            print(f"  ✅ 页面{i}上传成功: {gophish_page.name}")
    
    return uploaded_templates, uploaded_pages

def demo_campaign_creation(automation, smtp, group, templates, pages):
    """演示钓鱼活动创建"""
    print_step("4. 创建钓鱼活动")
    
    if templates and pages:
        campaign = automation.create_campaign(
            campaign_name="AI钓鱼演示活动",
            group_name=group.name,
            template_name=templates[0].name,
            page_name=pages[0].name,
            smtp_name=smtp.name,
            url="http://localhost:5001"  # 指向XSS服务器
        )
        
        if campaign:
            print(f"✅ 钓鱼活动创建成功!")
            print(f"   🎯 活动名称: {campaign.name}")
            print(f"   🆔 活动ID: {campaign.id}")
            print(f"   📊 状态: {campaign.status}")
            print(f"   🌐 钓鱼URL: http://localhost:5001")
            return campaign
    
    return None

def demo_results_monitoring(automation):
    """演示结果监控"""
    print_step("5. 监控活动结果")
    
    # 获取所有活动结果
    results = automation.get_campaign_results()
    
    if results:
        print("📊 活动结果概览:")
        for campaign_id, data in results.items():
            print(f"\n🎯 活动: {data['name']} (ID: {campaign_id})")
            print(f"   📅 创建时间: {data['created_date']}")
            print(f"   📊 状态: {data['status']}")
            
            summary = data['summary']
            print(f"   📈 统计数据:")
            print(f"     • 总用户: {summary['total']}")
            print(f"     • 邮件发送: {summary['sent']}")
            print(f"     • 链接点击: {summary['clicked']}")
            print(f"     • 数据提交: {summary['submitted']}")
            print(f"     • 点击率: {summary['click_rate']}%")
            print(f"     • 提交率: {summary['submission_rate']}%")
    else:
        print("📭 暂无活动结果")

def demo_resource_listing(automation):
    """演示资源列表"""
    print_step("6. 查看所有资源")
    
    resources = automation.list_all_resources()
    
    for resource_type, items in resources.items():
        print(f"\n📁 {resource_type.upper()} ({len(items)}个):")
        for item in items:
            if resource_type == 'groups':
                print(f"   👥 {item['name']} - {item['users']}个用户")
            elif resource_type == 'templates':
                print(f"   📧 {item['name']} - {item['subject'][:30]}...")
            elif resource_type == 'pages':
                print(f"   🌐 {item['name']}")
            elif resource_type == 'smtp':
                print(f"   📨 {item['name']} - {item['host']}")
            elif resource_type == 'campaigns':
                print(f"   🎯 {item['name']} - {item['status']}")

def demo_batch_generation():
    """演示批量生成功能"""
    print_section("批量生成功能演示")
    
    batch_generator = BatchPhishingGenerator()
    
    print_step("1. 查看预定义场景")
    scenarios = batch_generator.generate_campaign_scenarios()
    print(f"发现 {len(scenarios)} 个预定义场景:")
    for i, scenario in enumerate(scenarios, 1):
        print(f"  {i}. {scenario['name']}")
        print(f"     类型: {scenario['type']}")
        print(f"     目标: {scenario['company']}")
        print(f"     描述: {scenario['description']}")

def demo_integration_with_vulnerable_servers():
    """演示与漏洞服务器的集成"""
    print_section("漏洞服务器集成演示")
    
    print("🔗 本系统与以下漏洞服务器完全集成:")
    
    servers = [
        ("XSS漏洞服务器", "http://localhost:5001", "跨站脚本攻击演示"),
        ("SQL注入服务器", "http://localhost:5002", "数据库注入攻击演示"),
        ("Heartbleed服务器", "http://localhost:5003", "SSL心脏滴血漏洞演示"),
        ("损失评估仪表板", "http://localhost:5888", "攻击损失统计和可视化")
    ]
    
    for name, url, desc in servers:
        print(f"\n🌐 {name}")
        print(f"   📍 地址: {url}")
        print(f"   📝 功能: {desc}")
    
    print("\n🎯 完整攻击链演示:")
    print("  1. 📧 发送AI生成的钓鱼邮件")
    print("  2. 👆 用户点击邮件链接")
    print("  3. 🌐 跳转到AI生成的钓鱼页面")
    print("  4. 📝 用户输入凭证信息")
    print("  5. 🔄 重定向到漏洞服务器")
    print("  6. 💥 演示后续攻击利用")
    print("  7. 📊 统计攻击效果和损失")

def main():
    """主演示流程"""
    print("🎭 Gophish AI自动化工具完整演示")
    print("此演示将展示如何使用AI自动化配置钓鱼实验平台")
    print("\n按Enter键继续，或输入'q'退出...")
    
    # 交互式演示
    while True:
        user_input = input().strip().lower()
        if user_input == 'q':
            print("演示结束，再见！")
            return
        break
    
    try:
        # 1. AI内容生成演示
        templates, pages = demo_ai_content_generation()
        
        input("\n按Enter继续下一部分...")
        
        # 2. Gophish自动化配置演示
        automation, smtp, group = demo_gophish_automation()
        
        input("\n按Enter继续下一部分...")
        
        # 3. 上传内容演示
        uploaded_templates, uploaded_pages = demo_template_and_page_upload(
            automation, templates, pages
        )
        
        input("\n按Enter继续下一部分...")
        
        # 4. 创建活动演示
        campaign = demo_campaign_creation(
            automation, smtp, group, uploaded_templates, uploaded_pages
        )
        
        input("\n按Enter继续下一部分...")
        
        # 5. 结果监控演示
        demo_results_monitoring(automation)
        
        input("\n按Enter继续下一部分...")
        
        # 6. 资源列表演示
        demo_resource_listing(automation)
        
        input("\n按Enter继续下一部分...")
        
        # 7. 批量生成演示
        demo_batch_generation()
        
        input("\n按Enter继续下一部分...")
        
        # 8. 集成演示
        demo_integration_with_vulnerable_servers()
        
        # 演示总结
        print_section("演示总结")
        print("🎉 恭喜！您已经完成了Gophish AI自动化工具的完整演示！")
        print("\n✨ 您学到了什么:")
        print("  🤖 使用AI生成真实可信的钓鱼邮件和页面")
        print("  ⚙️ 通过API完全自动化配置Gophish平台")
        print("  📊 创建和监控钓鱼活动结果")
        print("  🔄 批量生成和管理钓鱼内容")
        print("  🌐 与漏洞服务器集成进行完整攻击链演示")
        
        print("\n🚀 下一步建议:")
        print("  1. 运行 'python batch_generator.py' 创建完整实验环境")
        print("  2. 访问 https://localhost:3333 查看Gophish管理界面")
        print("  3. 访问 http://localhost:5888 查看损失评估仪表板")
        print("  4. 开始您的钓鱼安全意识培训实验！")
        
    except KeyboardInterrupt:
        print("\n\n🛑 演示被用户中断")
    except Exception as e:
        print(f"\n❌ 演示过程中发生错误: {e}")
        print("请检查配置和网络连接")

if __name__ == "__main__":
    main()
