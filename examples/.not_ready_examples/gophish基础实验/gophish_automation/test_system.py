#!/usr/bin/env python
"""
系统测试脚本
验证Gophish自动化工具的各个组件是否正常工作
"""

import os
import sys
import time
from typing import Dict, List

def test_imports():
    """测试所有模块导入"""
    print("🔍 测试模块导入...")
    
    try:
        from config import GOPHISH_API_KEY, OPENAI_API_KEY
        print("  ✅ config.py - 配置文件")
        
        from ai_generator import AIPhishingGenerator
        print("  ✅ ai_generator.py - AI生成器")
        
        from gophish_automation import GophishAutomation
        print("  ✅ gophish_automation.py - Gophish自动化")
        
        from batch_generator import BatchPhishingGenerator
        print("  ✅ batch_generator.py - 批量生成器")
        
        return True
    except ImportError as e:
        print(f"  ❌ 导入失败: {e}")
        return False

def test_gophish_connection():
    """测试Gophish连接"""
    print("\n🔗 测试Gophish连接...")
    
    try:
        from gophish_automation import GophishAutomation
        automation = GophishAutomation()
        
        # 尝试获取campaigns来测试连接
        campaigns = automation.api.campaigns.get()
        print(f"  ✅ Gophish连接成功 - 发现 {len(campaigns)} 个活动")
        return True
    except Exception as e:
        print(f"  ❌ Gophish连接失败: {e}")
        return False

def test_ai_generator():
    """测试AI生成器"""
    print("\n🤖 测试AI生成器...")
    
    try:
        from ai_generator import AIPhishingGenerator
        generator = AIPhishingGenerator()
        
        # 测试邮件模板生成
        print("  📧 测试邮件生成...")
        template = generator.generate_phishing_email(
            campaign_type="security_alert",
            target_company="测试公司"
        )
        
        if template and 'subject' in template:
            print(f"    ✅ 邮件生成成功: {template['subject'][:30]}...")
        else:
            print("    ❌ 邮件生成失败")
            return False
        
        # 测试页面生成
        print("  🌐 测试页面生成...")
        page = generator.generate_landing_page(
            page_type="login",
            company_name="测试公司"
        )
        
        if page and 'html' in page:
            print(f"    ✅ 页面生成成功: {len(page['html'])} 字符")
            return True
        else:
            print("    ❌ 页面生成失败")
            return False
            
    except Exception as e:
        print(f"  ❌ AI生成器测试失败: {e}")
        return False

def test_real_email_analysis():
    """测试真实邮件分析"""
    print("\n📧 测试真实邮件分析...")
    
    try:
        from ai_generator import AIPhishingGenerator
        generator = AIPhishingGenerator()
        
        real_emails = generator.get_available_real_emails()
        if real_emails:
            print(f"  ✅ 发现 {len(real_emails)} 个真实邮件模板")
            
            # 分析第一个邮件
            first_email = real_emails[0]
            analysis = generator.analyze_real_email(first_email)
            
            if analysis:
                print(f"    ✅ 邮件分析成功: {os.path.basename(first_email)}")
                print(f"    📄 主题: {analysis['subject'][:50]}...")
                return True
            else:
                print(f"    ❌ 邮件分析失败: {os.path.basename(first_email)}")
                return False
        else:
            print("  ⚠️  未发现真实邮件模板")
            return True  # 不是错误，只是没有邮件
            
    except Exception as e:
        print(f"  ❌ 真实邮件分析失败: {e}")
        return False

def test_smtp_configuration():
    """测试SMTP配置"""
    print("\n📨 测试SMTP配置...")
    
    try:
        from gophish_automation import GophishAutomation
        automation = GophishAutomation()
        
        # 创建测试SMTP配置
        smtp = automation.setup_smtp_profile("测试SMTP配置")
        
        if smtp:
            print(f"  ✅ SMTP配置成功: {smtp.name}")
            return True
        else:
            print("  ❌ SMTP配置失败")
            return False
            
    except Exception as e:
        print(f"  ❌ SMTP配置测试失败: {e}")
        return False

def test_user_group_creation():
    """测试用户组创建"""
    print("\n👥 测试用户组创建...")
    
    try:
        from gophish_automation import GophishAutomation
        automation = GophishAutomation()
        
        test_users = [
            {
                'first_name': '测试',
                'last_name': '用户1',
                'email': 'test1@example.com',
                'position': '测试工程师'
            }
        ]
        
        group = automation.create_user_group("测试用户组", test_users)
        
        if group:
            print(f"  ✅ 用户组创建成功: {group.name}")
            return True
        else:
            print("  ❌ 用户组创建失败")
            return False
            
    except Exception as e:
        print(f"  ❌ 用户组创建测试失败: {e}")
        return False

def test_template_creation():
    """测试模板创建"""
    print("\n📝 测试模板创建...")
    
    try:
        from gophish_automation import GophishAutomation
        automation = GophishAutomation()
        
        template_data = {
            'name': '测试邮件模板',
            'subject': '测试主题',
            'text': '这是一个测试邮件模板，包含钓鱼链接：{{.URL}}',
            'html': '<html><body><p>测试HTML邮件</p><a href="{{.URL}}">点击这里</a></body></html>'
        }
        
        template = automation.create_email_template(template_data)
        
        if template:
            print(f"  ✅ 邮件模板创建成功: {template.name}")
            return True
        else:
            print("  ❌ 邮件模板创建失败")
            return False
            
    except Exception as e:
        print(f"  ❌ 邮件模板创建测试失败: {e}")
        return False

def test_page_creation():
    """测试页面创建"""
    print("\n🌐 测试页面创建...")
    
    try:
        from gophish_automation import GophishAutomation
        automation = GophishAutomation()
        
        page_data = {
            'name': '测试钓鱼页面',
            'html': '''
            <!DOCTYPE html>
            <html>
            <head><title>测试页面</title></head>
            <body>
                {{.Tracker}}
                <h1>测试钓鱼页面</h1>
                <form method="post">
                    <input type="email" name="email" placeholder="邮箱" required>
                    <input type="password" name="password" placeholder="密码" required>
                    <button type="submit">登录</button>
                </form>
            </body>
            </html>
            ''',
            'capture_credentials': True,
            'capture_passwords': True
        }
        
        page = automation.create_landing_page(page_data)
        
        if page:
            print(f"  ✅ 钓鱼页面创建成功: {page.name}")
            return True
        else:
            print("  ❌ 钓鱼页面创建失败")
            return False
            
    except Exception as e:
        print(f"  ❌ 钓鱼页面创建测试失败: {e}")
        return False

def test_resource_listing():
    """测试资源列表"""
    print("\n📋 测试资源列表...")
    
    try:
        from gophish_automation import GophishAutomation
        automation = GophishAutomation()
        
        resources = automation.list_all_resources()
        
        if resources:
            print("  ✅ 资源列表获取成功:")
            for resource_type, items in resources.items():
                print(f"    📁 {resource_type}: {len(items)} 个")
            return True
        else:
            print("  ❌ 资源列表获取失败")
            return False
            
    except Exception as e:
        print(f"  ❌ 资源列表测试失败: {e}")
        return False

def run_all_tests():
    """运行所有测试"""
    print("🧪 Gophish自动化工具系统测试")
    print("=" * 50)
    
    tests = [
        ("模块导入", test_imports),
        ("Gophish连接", test_gophish_connection),
        ("AI生成器", test_ai_generator),
        ("真实邮件分析", test_real_email_analysis),
        ("SMTP配置", test_smtp_configuration),
        ("用户组创建", test_user_group_creation),
        ("模板创建", test_template_creation),
        ("页面创建", test_page_creation),
        ("资源列表", test_resource_listing)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ 测试异常: {e}")
            results.append((test_name, False))
        
        time.sleep(1)  # 避免API请求过快
    
    # 测试总结
    print("\n" + "="*60)
    print("📊 测试总结")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {test_name:20} {status}")
    
    print(f"\n🎯 总体结果: {passed}/{total} 个测试通过")
    
    if passed == total:
        print("🎉 所有测试通过！系统ready for action!")
        return True
    else:
        print("⚠️ 部分测试失败，请检查配置和环境")
        return False

def quick_test():
    """快速测试核心功能"""
    print("⚡ 快速测试模式")
    print("=" * 30)
    
    # 只测试核心功能
    tests = [
        test_imports,
        test_gophish_connection,
        test_ai_generator
    ]
    
    for i, test_func in enumerate(tests, 1):
        print(f"\n{i}. 执行测试...")
        try:
            result = test_func()
            if not result:
                print("❌ 核心功能测试失败")
                return False
        except Exception as e:
            print(f"❌ 测试异常: {e}")
            return False
    
    print("\n✅ 核心功能正常！")
    return True

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "quick":
        quick_test()
    else:
        run_all_tests()
