#!/usr/bin/env python
"""
批量钓鱼内容生成器
基于真实邮件模板批量生成钓鱼邮件和页面
"""

import os
import json
import time
from typing import List, Dict
from ai_generator import AIPhishingGenerator
from gophish_automation import GophishAutomation
from config import MAIL_TEMPLATE_DIR

class BatchPhishingGenerator:
    def __init__(self):
        self.ai_generator = AIPhishingGenerator()
        self.automation = GophishAutomation()
        
    def analyze_all_real_emails(self) -> List[Dict]:
        """分析所有真实邮件模板"""
        real_emails = self.ai_generator.get_available_real_emails()
        analyzed_emails = []
        
        print(f"📧 分析 {len(real_emails)} 个真实邮件模板...")
        
        for email_path in real_emails:
            print(f"  分析: {os.path.basename(email_path)}")
            analysis = self.ai_generator.analyze_real_email(email_path)
            if analysis:
                analysis['file_path'] = email_path
                analysis['filename'] = os.path.basename(email_path)
                analyzed_emails.append(analysis)
        
        return analyzed_emails
    
    def generate_campaign_scenarios(self) -> List[Dict]:
        """生成钓鱼活动场景"""
        scenarios = [
            {
                'name': 'AI_安全警告_Google风格',
                'type': 'security_alert',
                'company': 'Google',
                'description': '模仿Google安全警告的钓鱼邮件'
            },
            {
                'name': 'AI_系统更新_AWS风格',
                'type': 'system_update',
                'company': 'AWS',
                'description': '模仿AWS系统更新通知'
            },
            {
                'name': 'AI_账户验证_企业版',
                'type': 'account_verification',
                'company': '企业内部',
                'description': '企业内部账户验证通知'
            },
            {
                'name': 'AI_紧急操作_安全团队',
                'type': 'urgent_action',
                'company': '安全团队',
                'description': '来自安全团队的紧急操作通知'
            },
            {
                'name': 'AI_奖励通知_HR部门',
                'type': 'reward_notification',
                'company': 'HR部门',
                'description': 'HR部门发出的奖励通知'
            }
        ]
        
        return scenarios
    
    def batch_generate_templates(self, use_real_email_reference: bool = True) -> Dict:
        """批量生成邮件模板"""
        print("🤖 开始批量生成邮件模板...")
        
        scenarios = self.generate_campaign_scenarios()
        real_emails = self.ai_generator.get_available_real_emails()
        
        results = {
            'templates': [],
            'pages': [],
            'failed': []
        }
        
        for i, scenario in enumerate(scenarios):
            print(f"\n📝 生成场景 {i+1}/{len(scenarios)}: {scenario['name']}")
            
            # 选择参考邮件
            reference_email = None
            if use_real_email_reference and real_emails:
                # 简单的匹配逻辑：根据类型选择合适的参考邮件
                if scenario['type'] == 'security_alert':
                    reference_email = next((e for e in real_emails if '安全' in e or 'security' in e.lower()), real_emails[0])
                elif scenario['type'] == 'system_update':
                    reference_email = next((e for e in real_emails if 'AWS' in e or 'update' in e.lower()), real_emails[0])
                else:
                    reference_email = real_emails[i % len(real_emails)]  # 轮循使用
            
            scenario['reference_email'] = reference_email
            
            # 生成邮件模板
            try:
                template = self.ai_generator.generate_phishing_email(
                    campaign_type=scenario['type'],
                    target_company=scenario['company'],
                    reference_email=reference_email
                )
                
                if template:
                    template['scenario'] = scenario
                    results['templates'].append(template)
                    print(f"  ✅ 邮件模板生成成功")
                else:
                    results['failed'].append({'type': 'template', 'scenario': scenario, 'error': 'Generation failed'})
                    print(f"  ❌ 邮件模板生成失败")
                
            except Exception as e:
                results['failed'].append({'type': 'template', 'scenario': scenario, 'error': str(e)})
                print(f"  ❌ 邮件模板生成异常: {e}")
            
            # 生成对应的钓鱼页面
            try:
                page_type = self._scenario_to_page_type(scenario['type'])
                page = self.ai_generator.generate_landing_page(
                    page_type=page_type,
                    company_name=scenario['company'],
                    style='corporate'
                )
                
                if page:
                    page['scenario'] = scenario
                    results['pages'].append(page)
                    print(f"  ✅ 钓鱼页面生成成功")
                else:
                    results['failed'].append({'type': 'page', 'scenario': scenario, 'error': 'Generation failed'})
                    print(f"  ❌ 钓鱼页面生成失败")
                    
            except Exception as e:
                results['failed'].append({'type': 'page', 'scenario': scenario, 'error': str(e)})
                print(f"  ❌ 钓鱼页面生成异常: {e}")
        
        return results
    
    def _scenario_to_page_type(self, scenario_type: str) -> str:
        """将场景类型转换为页面类型"""
        mapping = {
            'security_alert': 'security_check',
            'system_update': 'update_info',
            'account_verification': 'verification',
            'urgent_action': 'login',
            'reward_notification': 'survey'
        }
        return mapping.get(scenario_type, 'login')
    
    def upload_to_gophish(self, generated_content: Dict) -> Dict:
        """将生成的内容上传到Gophish"""
        print("\n📤 开始上传到Gophish...")
        
        upload_results = {
            'templates': [],
            'pages': [],
            'failed': []
        }
        
        # 上传邮件模板
        for template in generated_content['templates']:
            try:
                gophish_template = self.automation.create_email_template(template)
                if gophish_template:
                    upload_results['templates'].append({
                        'name': template['name'],
                        'id': gophish_template.id,
                        'scenario': template['scenario']
                    })
                else:
                    upload_results['failed'].append({
                        'type': 'template',
                        'name': template['name'],
                        'error': 'Upload failed'
                    })
            except Exception as e:
                upload_results['failed'].append({
                    'type': 'template',
                    'name': template['name'],
                    'error': str(e)
                })
        
        # 上传钓鱼页面
        for page in generated_content['pages']:
            try:
                gophish_page = self.automation.create_landing_page(page)
                if gophish_page:
                    upload_results['pages'].append({
                        'name': page['name'],
                        'id': gophish_page.id,
                        'scenario': page['scenario']
                    })
                else:
                    upload_results['failed'].append({
                        'type': 'page',
                        'name': page['name'],
                        'error': 'Upload failed'
                    })
            except Exception as e:
                upload_results['failed'].append({
                    'type': 'page',
                    'name': page['name'],
                    'error': str(e)
                })
        
        return upload_results
    
    def create_comprehensive_setup(self):
        """创建完整的钓鱼实验环境"""
        print("🚀 创建完整的钓鱼实验环境...")
        
        # 1. 配置SMTP
        print("\n1️⃣ 配置SMTP服务器...")
        smtp = self.automation.setup_smtp_profile()
        if not smtp:
            print("❌ SMTP配置失败，终止设置")
            return
        
        # 2. 创建多个测试用户组
        print("\n2️⃣ 创建测试用户组...")
        user_groups = [
            {
                'name': '技术部员工',
                'users': [
                    {'first_name': '张', 'last_name': '工程师', 'email': 'engineer1@test.com', 'position': '高级工程师'},
                    {'first_name': '李', 'last_name': '开发', 'email': 'dev1@test.com', 'position': '软件开发'},
                    {'first_name': '王', 'last_name': '架构师', 'email': 'architect1@test.com', 'position': '系统架构师'}
                ]
            },
            {
                'name': '管理层',
                'users': [
                    {'first_name': '陈', 'last_name': '总监', 'email': 'director1@test.com', 'position': '技术总监'},
                    {'first_name': '刘', 'last_name': '经理', 'email': 'manager1@test.com', 'position': '项目经理'}
                ]
            },
            {
                'name': '财务部',
                'users': [
                    {'first_name': '赵', 'last_name': '会计', 'email': 'accountant1@test.com', 'position': '会计'},
                    {'first_name': '孙', 'last_name': '出纳', 'email': 'cashier1@test.com', 'position': '出纳'}
                ]
            }
        ]
        
        created_groups = []
        for group_data in user_groups:
            group = self.automation.create_user_group(group_data['name'], group_data['users'])
            if group:
                created_groups.append(group)
        
        # 3. 批量生成内容
        print("\n3️⃣ 批量生成钓鱼内容...")
        generated_content = self.batch_generate_templates(use_real_email_reference=True)
        
        # 4. 上传到Gophish
        print("\n4️⃣ 上传内容到Gophish...")
        upload_results = self.upload_to_gophish(generated_content)
        
        # 5. 创建示例活动
        print("\n5️⃣ 创建示例钓鱼活动...")
        if upload_results['templates'] and upload_results['pages'] and created_groups:
            for i, (template, page) in enumerate(zip(upload_results['templates'][:3], upload_results['pages'][:3])):
                group = created_groups[i % len(created_groups)]
                
                campaign_name = f"AI钓鱼测试_{template['scenario']['company']}_{i+1}"
                campaign = self.automation.create_campaign(
                    campaign_name=campaign_name,
                    group_name=group.name,
                    template_name=template['name'],
                    page_name=page['name'],
                    smtp_name=smtp.name,
                    url="http://localhost:5001"  # 指向XSS服务器
                )
                
                if campaign:
                    print(f"  ✅ 活动创建成功: {campaign_name}")
        
        # 6. 生成报告
        self._generate_setup_report(generated_content, upload_results, created_groups)
        
        print("\n🎉 完整环境设置完成！")
        print(f"📊 访问 https://localhost:3333 查看所有配置")
    
    def _generate_setup_report(self, generated_content: Dict, upload_results: Dict, groups: List):
        """生成设置报告"""
        report = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'summary': {
                'templates_generated': len(generated_content['templates']),
                'pages_generated': len(generated_content['pages']),
                'templates_uploaded': len(upload_results['templates']),
                'pages_uploaded': len(upload_results['pages']),
                'groups_created': len(groups),
                'failed_operations': len(generated_content['failed']) + len(upload_results['failed'])
            },
            'details': {
                'generated_content': generated_content,
                'upload_results': upload_results,
                'groups': [{'name': g.name, 'id': g.id, 'users': len(g.targets)} for g in groups]
            }
        }
        
        report_file = 'gophish_setup_report.json'
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"\n📋 设置报告已保存: {report_file}")
        
        # 打印摘要
        print("\n📊 设置摘要:")
        print(f"  ✅ 邮件模板: {report['summary']['templates_uploaded']}/{report['summary']['templates_generated']} 成功")
        print(f"  ✅ 钓鱼页面: {report['summary']['pages_uploaded']}/{report['summary']['pages_generated']} 成功")
        print(f"  ✅ 用户组: {report['summary']['groups_created']} 个")
        if report['summary']['failed_operations'] > 0:
            print(f"  ⚠️  失败操作: {report['summary']['failed_operations']} 个")

def main():
    """主函数"""
    import time
    
    batch_generator = BatchPhishingGenerator()
    
    print("🎯 批量钓鱼内容生成器")
    print("=" * 50)
    
    while True:
        print("\n请选择操作：")
        print("1. 分析所有真实邮件模板")
        print("2. 批量生成钓鱼内容")
        print("3. 上传生成的内容到Gophish")
        print("4. 创建完整实验环境 (推荐)")
        print("5. 查看生成场景")
        print("6. 退出")
        
        choice = input("\n请输入选择 (1-6): ").strip()
        
        if choice == '1':
            analyzed = batch_generator.analyze_all_real_emails()
            print(f"\n📊 分析完成，共处理 {len(analyzed)} 个邮件:")
            for email in analyzed:
                print(f"  📧 {email['filename']}")
                print(f"     主题: {email['subject'][:50]}...")
                print(f"     发件人: {email['sender']}")
                print(f"     类型: {email['content_type']}")
        
        elif choice == '2':
            use_ref = input("是否使用真实邮件作为参考？ (y/n, 默认y): ").strip().lower()
            use_ref = use_ref != 'n'
            
            results = batch_generator.batch_generate_templates(use_real_email_reference=use_ref)
            
            print(f"\n📊 生成完成:")
            print(f"  ✅ 邮件模板: {len(results['templates'])} 个")
            print(f"  ✅ 钓鱼页面: {len(results['pages'])} 个")
            print(f"  ❌ 失败: {len(results['failed'])} 个")
            
            if results['failed']:
                print("\n失败详情:")
                for fail in results['failed']:
                    print(f"  ❌ {fail['type']}: {fail.get('scenario', {}).get('name', 'Unknown')} - {fail['error']}")
        
        elif choice == '3':
            # 首先需要生成内容
            print("生成内容中...")
            results = batch_generator.batch_generate_templates(use_real_email_reference=True)
            
            if results['templates'] or results['pages']:
                upload_results = batch_generator.upload_to_gophish(results)
                
                print(f"\n📤 上传完成:")
                print(f"  ✅ 邮件模板: {len(upload_results['templates'])} 个")
                print(f"  ✅ 钓鱼页面: {len(upload_results['pages'])} 个")
                print(f"  ❌ 失败: {len(upload_results['failed'])} 个")
            else:
                print("❌ 没有可上传的内容")
        
        elif choice == '4':
            confirm = input("这将创建完整的实验环境，是否继续？ (y/n): ").strip().lower()
            if confirm == 'y':
                batch_generator.create_comprehensive_setup()
        
        elif choice == '5':
            scenarios = batch_generator.generate_campaign_scenarios()
            print(f"\n📋 预定义场景 ({len(scenarios)} 个):")
            for i, scenario in enumerate(scenarios, 1):
                print(f"  {i}. {scenario['name']}")
                print(f"     类型: {scenario['type']}")
                print(f"     公司: {scenario['company']}")
                print(f"     描述: {scenario['description']}")
        
        elif choice == '6':
            print("再见！")
            break
        
        else:
            print("无效选择，请重试")

if __name__ == "__main__":
    main()
