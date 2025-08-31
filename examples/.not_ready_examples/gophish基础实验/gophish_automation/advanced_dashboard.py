#!/usr/bin/env python
"""
高级AI钓鱼管理表盘 - 简洁现代版
更智能、更自由、更简洁的钓鱼实验管理平台
"""

import os
import json
import time
import sqlite3
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_file
from werkzeug.utils import secure_filename
import requests
from typing import Dict, List
import uuid
import tempfile

from ai_generator import AIPhishingGenerator
from gophish_automation import GophishAutomation
from batch_generator import BatchPhishingGenerator
from config import GOPHISH_HOST, MAIL_TEMPLATE_DIR

app = Flask(__name__)
app.secret_key = 'advanced_gophish_dashboard_2025'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# 初始化组件
try:
    ai_generator = AIPhishingGenerator()
    automation = GophishAutomation()
    batch_generator = BatchPhishingGenerator()
except Exception as e:
    print(f"⚠️ 组件初始化警告: {e}")
    ai_generator = None
    automation = None
    batch_generator = None

# 攻击服务器配置
ATTACK_SERVERS = {
    'xss': {'port': 5001, 'name': 'XSS跨站脚本', 'icon': '🌐', 'risk': 'medium'},
    'sqli': {'port': 5002, 'name': 'SQL注入', 'icon': '💾', 'risk': 'high'},
    'heartbleed': {'port': 5003, 'name': 'Heartbleed', 'icon': '💔', 'risk': 'medium'},
    'apt': {'port': 5004, 'name': 'APT攻击链', 'icon': '🎯', 'risk': 'high'},
    'malware': {'port': 5005, 'name': '恶意软件', 'icon': '🦠', 'risk': 'critical'},
    'redblue': {'port': 5006, 'name': '红蓝对抗', 'icon': '⚔️', 'risk': 'high'},
    'iot': {'port': 5007, 'name': 'IoT安全', 'icon': '📱', 'risk': 'medium'},
    'custom': {'port': 8080, 'name': '自定义服务', 'icon': '🔧', 'risk': 'low'}
}

def get_system_status():
    """获取简洁的系统状态"""
    status = {
        'gophish': False,
        'ai_ready': ai_generator is not None,
        'active_campaigns': 0,
        'total_templates': 0,
        'total_groups': 0,
        'services': {},
        'timestamp': datetime.now().strftime('%H:%M:%S')
    }
    
    # 检查Gophish
    try:
        if automation:
            campaigns = automation.api.campaigns.get()
            templates = automation.api.templates.get()
            groups = automation.api.groups.get()
            
            status['gophish'] = True
            status['active_campaigns'] = len([c for c in campaigns if c.status != 'Completed'])
            status['total_templates'] = len(templates)
            status['total_groups'] = len(groups)
    except:
        pass
    
    # 检查攻击服务器
    for key, server in ATTACK_SERVERS.items():
        try:
            response = requests.get(f'http://localhost:{server["port"]}', timeout=1)
            status['services'][key] = 'online'
        except:
            status['services'][key] = 'offline'
    
    return status

def get_real_email_templates():
    """获取真实邮件模板列表"""
    templates = []
    if os.path.exists(MAIL_TEMPLATE_DIR):
        for file in os.listdir(MAIL_TEMPLATE_DIR):
            if file.endswith('.eml'):
                file_path = os.path.join(MAIL_TEMPLATE_DIR, file)
                # 分析邮件主题
                subject = "未知主题"
                sender = "未知发件人"
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        lines = content.split('\n')
                        for line in lines:
                            if line.startswith('Subject:'):
                                subject = line.replace('Subject:', '').strip()
                                break
                        for line in lines:
                            if line.startswith('From:'):
                                sender = line.replace('From:', '').strip()
                                break
                except:
                    pass
                
                templates.append({
                    'filename': file,
                    'path': file_path,
                    'subject': subject[:50] + '...' if len(subject) > 50 else subject,
                    'sender': sender[:30] + '...' if len(sender) > 30 else sender,
                    'size': os.path.getsize(file_path)
                })
    
    return templates

@app.route('/')
def dashboard():
    """现代简洁主表盘"""
    system_status = get_system_status()
    real_templates = get_real_email_templates()
    
    return render_template('modern_dashboard.html',
                         system_status=system_status,
                         attack_servers=ATTACK_SERVERS,
                         real_templates=real_templates)

@app.route('/api/status')
def api_status():
    """API状态接口"""
    return jsonify(get_system_status())

@app.route('/create_group', methods=['POST'])
def create_group():
    """创建自定义用户组"""
    if not automation:
        return jsonify({'success': False, 'message': 'Gophish未初始化'})
    
    try:
        group_name = request.form.get('group_name')
        emails = request.form.get('emails', '').strip()
        
        if not group_name or not emails:
            return jsonify({'success': False, 'message': '请填写组名和邮箱地址'})
        
        # 解析邮箱列表
        email_list = [email.strip() for email in emails.replace('\n', ',').split(',') if email.strip()]
        
        if not email_list:
            return jsonify({'success': False, 'message': '请输入有效的邮箱地址'})
        
        # 创建用户列表
        users = []
        for email in email_list:
            name_parts = email.split('@')[0].replace('.', ' ').replace('_', ' ').split()
            first_name = name_parts[0] if name_parts else 'User'
            last_name = name_parts[1] if len(name_parts) > 1 else ''
            
            users.append({
                'first_name': first_name.capitalize(),
                'last_name': last_name.capitalize(),
                'email': email,
                'position': '测试用户'
            })
        
        # 创建组
        group = automation.create_user_group(group_name, users)
        
        if group:
            return jsonify({
                'success': True, 
                'message': f'用户组"{group_name}"创建成功，包含{len(users)}个用户',
                'group_id': group.id
            })
        else:
            return jsonify({'success': False, 'message': '用户组创建失败'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'创建失败: {str(e)}'})

@app.route('/generate_content', methods=['POST'])
def generate_content():
    """智能内容生成"""
    if not ai_generator:
        return jsonify({'success': False, 'message': 'AI生成器未初始化'})
    
    try:
        content_type = request.form.get('content_type')
        use_real_template = request.form.get('use_real_template') == 'true'
        reference_template = request.form.get('reference_template')
        
        # 基础参数
        scenario_type = request.form.get('scenario_type', 'security_alert')
        company_name = request.form.get('company_name', 'XX公司')
        
        reference_email = None
        if use_real_template and reference_template:
            reference_email = os.path.join(MAIL_TEMPLATE_DIR, reference_template)
        
        if content_type == 'email':
            result = ai_generator.generate_phishing_email(
                campaign_type=scenario_type,
                target_company=company_name,
                reference_email=reference_email
            )
            
            if result:
                # 生成唯一名称
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                result['name'] = f"AI_{scenario_type}_{timestamp}"
                
                # 保存到Gophish
                if automation:
                    gophish_template = automation.create_email_template(result)
                    if gophish_template:
                        return jsonify({
                            'success': True,
                            'message': f'邮件模板生成成功: {result["name"]}',
                            'template_id': gophish_template.id,
                            'preview': {
                                'subject': result['subject'],
                                'content': result['text'][:200] + '...'
                            }
                        })
                
        elif content_type == 'page':
            page_type = request.form.get('page_type', 'login')
            style = request.form.get('style', 'modern')
            advanced_attacks = request.form.get('advanced_attacks') == 'true'
            
            result = ai_generator.generate_landing_page(
                page_type=page_type,
                company_name=company_name,
                style=style,
                advanced_attacks=advanced_attacks
            )
            
            if result:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                attack_suffix = "_高级攻击演示" if advanced_attacks else ""
                result['name'] = f"AI_{page_type}_{style}{attack_suffix}_{timestamp}"
                
                # 保存到Gophish
                if automation:
                    gophish_page = automation.create_landing_page(result)
                    if gophish_page:
                        message = f'钓鱼页面生成成功: {result["name"]}'
                        if advanced_attacks:
                            message += '\n🎯 包含高级攻击演示：标签页劫持、指纹识别、Cookie窃取等'
                        
                        return jsonify({
                            'success': True,
                            'message': message,
                            'page_id': gophish_page.id,
                            'preview': f'HTML长度: {len(result["html"])} 字符',
                            'advanced_attacks': advanced_attacks
                        })
        
        return jsonify({'success': False, 'message': '内容生成失败'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'生成失败: {str(e)}'})

@app.route('/upload_template', methods=['POST'])
def upload_template():
    """上传邮件模板"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '未选择文件'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': '未选择文件'})
    
    try:
        # 支持的文件类型
        allowed_extensions = {'.eml', '.txt', '.html', '.json'}
        file_ext = os.path.splitext(file.filename)[1].lower()
        
        if file_ext not in allowed_extensions:
            return jsonify({'success': False, 'message': '不支持的文件类型'})
        
        # 保存到邮件模板目录
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"uploaded_{timestamp}_{filename}"
        
        file_path = os.path.join(MAIL_TEMPLATE_DIR, filename)
        file.save(file_path)
        
        # 如果是HTML或JSON，尝试转换为邮件模板
        if file_ext in {'.html', '.json'}:
            content = file.read().decode('utf-8', errors='ignore')
            
            if file_ext == '.json':
                # JSON格式的模板
                try:
                    template_data = json.loads(content)
                    if automation and 'name' in template_data and 'subject' in template_data:
                        gophish_template = automation.create_email_template(template_data)
                        if gophish_template:
                            return jsonify({
                                'success': True,
                                'message': f'模板上传并创建成功: {template_data["name"]}',
                                'template_id': gophish_template.id
                            })
                except:
                    pass
            
            elif file_ext == '.html':
                # HTML模板
                template_data = {
                    'name': f'上传模板_{timestamp}',
                    'subject': '重要通知',
                    'html': content,
                    'text': '请查看HTML版本邮件'
                }
                
                if automation:
                    gophish_template = automation.create_email_template(template_data)
                    if gophish_template:
                        return jsonify({
                            'success': True,
                            'message': f'HTML模板上传成功: {template_data["name"]}',
                            'template_id': gophish_template.id
                        })
        
        return jsonify({
            'success': True,
            'message': f'文件上传成功: {filename}',
            'filename': filename
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'上传失败: {str(e)}'})

@app.route('/launch_campaign', methods=['POST'])
def launch_campaign():
    """启动自定义钓鱼活动"""
    if not automation:
        return jsonify({'success': False, 'message': 'Gophish未初始化'})
    
    try:
        campaign_name = request.form.get('campaign_name')
        group_id = request.form.get('group_id')
        template_id = request.form.get('template_id')
        page_id = request.form.get('page_id')
        attack_server = request.form.get('attack_server', 'xss')
        send_immediately = request.form.get('send_immediately') == 'true'
        
        if not all([campaign_name, group_id, template_id, page_id]):
            return jsonify({'success': False, 'message': '请填写所有必要字段'})
        
        # 获取资源名称
        groups = automation.api.groups.get()
        templates = automation.api.templates.get()
        pages = automation.api.pages.get()
        smtp_profiles = automation.api.smtp.get()
        
        group_name = next((g.name for g in groups if str(g.id) == group_id), None)
        template_name = next((t.name for t in templates if str(t.id) == template_id), None)
        page_name = next((p.name for p in pages if str(p.id) == page_id), None)
        
        if not group_name or not template_name or not page_name:
            return jsonify({'success': False, 'message': '找不到指定的资源'})
        
        if not smtp_profiles:
            return jsonify({'success': False, 'message': '未配置SMTP发送配置'})
        
        # 构建钓鱼URL
        server_config = ATTACK_SERVERS.get(attack_server, ATTACK_SERVERS['custom'])
        phishing_url = f"http://localhost:{server_config['port']}"
        
        # 创建活动
        campaign = automation.create_campaign(
            campaign_name=campaign_name,
            group_name=group_name,
            template_name=template_name,
            page_name=page_name,
            smtp_name=smtp_profiles[0].name,
            url=phishing_url
        )
        
        if campaign:
            return jsonify({
                'success': True,
                'message': f'钓鱼活动"{campaign_name}"创建成功！',
                'campaign_id': campaign.id,
                'target_url': phishing_url,
                'attack_type': server_config['name']
            })
        else:
            return jsonify({'success': False, 'message': '活动创建失败'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'启动失败: {str(e)}'})

@app.route('/get_resources')
def get_resources():
    """获取Gophish资源列表"""
    if not automation:
        return jsonify({'groups': [], 'templates': [], 'pages': []})
    
    try:
        resources = automation.list_all_resources()
        return jsonify(resources)
    except:
        return jsonify({'groups': [], 'templates': [], 'pages': []})

@app.route('/analyze_real_email', methods=['POST'])
def analyze_real_email():
    """分析真实邮件模板"""
    if not ai_generator:
        return jsonify({'success': False, 'message': 'AI生成器未初始化'})
    
    filename = request.form.get('filename')
    if not filename:
        return jsonify({'success': False, 'message': '未指定文件'})
    
    file_path = os.path.join(MAIL_TEMPLATE_DIR, filename)
    if not os.path.exists(file_path):
        return jsonify({'success': False, 'message': '文件不存在'})
    
    try:
        analysis = ai_generator.analyze_real_email(file_path)
        if analysis:
            return jsonify({
                'success': True,
                'analysis': {
                    'subject': analysis['subject'],
                    'sender': analysis['sender'],
                    'content_type': analysis['content_type'],
                    'preview': analysis['body'][:300] + '...' if len(analysis['body']) > 300 else analysis['body']
                }
            })
        else:
            return jsonify({'success': False, 'message': '邮件分析失败'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'分析失败: {str(e)}'})

@app.route('/send_real_email', methods=['POST'])
def send_real_email():
    """直接发送真实邮件模板"""
    if not automation:
        return jsonify({'success': False, 'message': 'Gophish未初始化'})
    
    try:
        filename = request.form.get('filename')
        group_id = request.form.get('group_id')
        attack_server = request.form.get('attack_server', 'xss')
        campaign_name = request.form.get('campaign_name')
        
        if not all([filename, group_id, campaign_name]):
            return jsonify({'success': False, 'message': '请填写所有必要字段'})
        
        file_path = os.path.join(MAIL_TEMPLATE_DIR, filename)
        if not os.path.exists(file_path):
            return jsonify({'success': False, 'message': '邮件文件不存在'})
        
        # 解析真实邮件
        analysis = ai_generator.analyze_real_email(file_path)
        if not analysis:
            return jsonify({'success': False, 'message': '邮件解析失败'})
        
        # 生成唯一模板名称
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_filename = filename.replace('.eml', '').replace(' ', '_')[:30]
        
        # 为特殊邮件创建更具描述性的名称
        if 'metamask' in filename.lower() or '监控' in filename:
            template_name = f"真实邮件_MetaMask安全警告_{timestamp}"
        elif 'aws' in filename.lower():
            template_name = f"真实邮件_AWS通知_{timestamp}"
        elif 'google' in filename.lower():
            template_name = f"真实邮件_Google安全_{timestamp}"
        else:
            template_name = f"真实邮件_{safe_filename}_{timestamp}"
        
        # 准备模板数据
        template_data = {
            'name': template_name,
            'subject': analysis['subject'],
            'text': analysis['body'],
            'html': analysis['body'] if analysis['content_type'] == 'html' else '',
            'from_address': analysis['sender']
        }
        
        # 如果是HTML内容，需要处理{{.URL}}占位符
        if analysis['content_type'] == 'html':
            # 在HTML中添加钓鱼链接，替换原有的验证链接
            html_content = analysis['body']
            # 查找现有链接并替换为{{.URL}}
            import re
            # 替换各种可能的链接格式
            html_content = re.sub(r'href="[^"]*"', 'href="{{.URL}}"', html_content)
            template_data['html'] = html_content
            template_data['text'] = f"请查看HTML版本邮件，或点击此链接: {{{{.URL}}}}"
        else:
            # 在文本中添加钓鱼链接
            text_content = analysis['body']
            if '{{.URL}}' not in text_content:
                text_content += f"\n\n立即验证: {{{{.URL}}}}"
            template_data['text'] = text_content
        
        # 创建邮件模板
        gophish_template = automation.create_email_template(template_data)
        if not gophish_template:
            return jsonify({'success': False, 'message': '邮件模板创建失败'})
        
        # 创建简单的钓鱼页面
        page_data = {
            'name': f"真实邮件页面_{timestamp}",
            'html': f'''
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>账户验证</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 50px auto; max-width: 400px; }}
                    .container {{ background: #f9f9f9; padding: 30px; border-radius: 8px; }}
                    input {{ width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ddd; }}
                    button {{ width: 100%; padding: 12px; background: #ff6600; color: white; border: none; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h2>🔒 账户安全验证</h2>
                    <p>基于真实邮件: {filename}</p>
                    <form method="post">
                        <input type="email" name="email" placeholder="邮箱地址" required>
                        <input type="password" name="password" placeholder="密码" required>
                        <button type="submit">验证账户</button>
                    </form>
                </div>
                {{{{.Tracker}}}}
            </body>
            </html>
            ''',
            'capture_credentials': True,
            'capture_passwords': True
        }
        
        gophish_page = automation.create_landing_page(page_data)
        if not gophish_page:
            return jsonify({'success': False, 'message': '钓鱼页面创建失败'})
        
        # 获取用户组和SMTP配置
        groups = automation.api.groups.get()
        smtp_profiles = automation.api.smtp.get()
        
        group_name = next((g.name for g in groups if str(g.id) == group_id), None)
        if not group_name or not smtp_profiles:
            return jsonify({'success': False, 'message': '找不到用户组或SMTP配置'})
        
        # 构建钓鱼URL
        server_config = ATTACK_SERVERS.get(attack_server, ATTACK_SERVERS['custom'])
        phishing_url = f"http://localhost:{server_config['port']}"
        
        # 创建钓鱼活动
        campaign = automation.create_campaign(
            campaign_name=campaign_name,
            group_name=group_name,
            template_name=gophish_template.name,
            page_name=gophish_page.name,
            smtp_name=smtp_profiles[0].name,
            url=phishing_url
        )
        
        if campaign:
            return jsonify({
                'success': True,
                'message': f'真实邮件活动"{campaign_name}"创建成功！',
                'details': {
                    'campaign_id': campaign.id,
                    'template_name': gophish_template.name,
                    'page_name': gophish_page.name,
                    'target_url': phishing_url,
                    'attack_type': server_config['name'],
                    'email_type': '真实邮件' + (' (MetaMask钓鱼)' if 'metamask' in filename.lower() else '')
                }
            })
        else:
            return jsonify({'success': False, 'message': '活动创建失败'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'发送失败: {str(e)}'})

@app.route('/quick_attack')
def quick_attack():
    """快速攻击页面"""
    system_status = get_system_status()
    return render_template('quick_attack.html',
                         system_status=system_status,
                         attack_servers=ATTACK_SERVERS)

@app.route('/batch_operation', methods=['POST'])
def batch_operation():
    """批量操作"""
    operation = request.form.get('operation')
    
    if operation == 'create_demo_environment':
        try:
            if batch_generator:
                batch_generator.create_comprehensive_setup()
                return jsonify({'success': True, 'message': '演示环境创建成功！'})
            else:
                return jsonify({'success': False, 'message': '批量生成器未初始化'})
        except Exception as e:
            return jsonify({'success': False, 'message': f'创建失败: {str(e)}'})
    
    elif operation == 'generate_multiple_templates':
        count = int(request.form.get('count', 3))
        try:
            if not ai_generator:
                return jsonify({'success': False, 'message': 'AI生成器未初始化'})
            
            scenarios = ['security_alert', 'system_update', 'account_verification', 'urgent_action', 'reward_notification']
            companies = ['Google', 'Microsoft', 'AWS', '企业内部', 'Apple']
            
            created_templates = []
            for i in range(min(count, 5)):  # 限制最多5个
                scenario = scenarios[i % len(scenarios)]
                company = companies[i % len(companies)]
                
                template = ai_generator.generate_phishing_email(
                    campaign_type=scenario,
                    target_company=company
                )
                
                if template and automation:
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    template['name'] = f"批量生成_{scenario}_{timestamp}_{i+1}"
                    
                    gophish_template = automation.create_email_template(template)
                    if gophish_template:
                        created_templates.append(template['name'])
            
            if created_templates:
                return jsonify({
                    'success': True,
                    'message': f'成功生成{len(created_templates)}个模板',
                    'templates': created_templates
                })
            else:
                return jsonify({'success': False, 'message': '未能生成任何模板'})
                
        except Exception as e:
            return jsonify({'success': False, 'message': f'批量生成失败: {str(e)}'})
    
    return jsonify({'success': False, 'message': '未知操作'})

if __name__ == '__main__':
    print("🎯 启动高级AI钓鱼管理表盘")
    print("=" * 50)
    print("📍 访问地址: http://localhost:6789")
    print("🎨 界面特色: 现代简洁设计")
    print("🔧 功能特色:")
    print("  • 自定义用户组创建")
    print("  • 邮件模板上传")
    print("  • 真实邮件模板集成")
    print("  • 灵活攻击服务器选择")
    print("  • 智能批量操作")
    print("  • 实时状态监控")
    
    app.run(host='0.0.0.0', port=6789, debug=True)
