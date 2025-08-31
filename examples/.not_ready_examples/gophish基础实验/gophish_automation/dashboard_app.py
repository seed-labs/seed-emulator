#!/usr/bin/env python
"""
Gophish AI自动化管理表盘
集成所有功能的Web前端界面
"""

import os
import json
import time
import sqlite3
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from werkzeug.utils import secure_filename
import requests
from typing import Dict, List

from ai_generator import AIPhishingGenerator
from gophish_automation import GophishAutomation
from batch_generator import BatchPhishingGenerator
from config import GOPHISH_HOST, MAIL_TEMPLATE_DIR

app = Flask(__name__)
app.secret_key = 'gophish_dashboard_secret_key_2025'

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

# 预定义测试目标
RECOMMENDED_TARGETS = [
    {
        'email': 'zzw4257@gmail.com',
        'name': '测试用户1',
        'position': '系统管理员',
        'priority': 'high',
        'description': '主要测试目标'
    },
    {
        'email': '3230106267@zju.edu.cn', 
        'name': '测试用户2',
        'position': '学生',
        'priority': 'medium',
        'description': '教育环境测试'
    },
    {
        'email': '809050685@qq.com',
        'name': '测试用户3', 
        'position': '员工',
        'priority': 'medium',
        'description': 'QQ邮箱测试'
    }
]

def get_system_status():
    """获取系统状态"""
    status = {
        'gophish': False,
        'ai_generator': ai_generator is not None,
        'automation': automation is not None,
        'services': {},
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # 检查Gophish状态
    try:
        if automation:
            campaigns = automation.api.campaigns.get()
            status['gophish'] = True
            status['campaigns_count'] = len(campaigns)
    except:
        pass
    
    # 检查各个服务状态
    services = [
        ('dashboard', 5888, '损失评估仪表板'),
        ('xss_server', 5001, 'XSS漏洞服务器'),
        ('sqli_server', 5002, 'SQL注入服务器'),  
        ('heartbleed_server', 5003, 'Heartbleed仿真'),
        ('apt_simulation', 5004, 'APT攻击链'),
        ('malware_sandbox', 5005, '恶意软件沙箱'),
        ('red_blue_platform', 5006, '红蓝对抗平台'),
        ('iot_security', 5007, 'IoT安全实验室')
    ]
    
    for service_name, port, description in services:
        try:
            response = requests.get(f'http://localhost:{port}', timeout=2)
            status['services'][service_name] = {
                'status': 'online',
                'port': port,
                'description': description,
                'url': f'http://localhost:{port}'
            }
        except:
            status['services'][service_name] = {
                'status': 'offline',
                'port': port,
                'description': description,
                'url': f'http://localhost:{port}'
            }
    
    return status

def get_file_inventory():
    """获取文件清单"""
    inventory = {
        'gophish_automation': [],
        'mail_templates': [],
        'generated_content': [],
        'reports': [],
        'malware_samples': [],
        'red_blue_data': []
    }
    
    # Gophish自动化文件
    automation_dir = '/Users/zzw4257/Documents/ZJU_archieve/25-seed/gophish基础实验/gophish_automation'
    if os.path.exists(automation_dir):
        for file in os.listdir(automation_dir):
            if file.endswith('.py') or file.endswith('.md'):
                file_path = os.path.join(automation_dir, file)
                inventory['gophish_automation'].append({
                    'name': file,
                    'path': file_path,
                    'size': os.path.getsize(file_path) if os.path.exists(file_path) else 0,
                    'modified': datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M') if os.path.exists(file_path) else 'Unknown'
                })
    
    # 邮件模板
    if os.path.exists(MAIL_TEMPLATE_DIR):
        for file in os.listdir(MAIL_TEMPLATE_DIR):
            if file.endswith('.eml'):
                file_path = os.path.join(MAIL_TEMPLATE_DIR, file)
                inventory['mail_templates'].append({
                    'name': file,
                    'path': file_path,
                    'size': os.path.getsize(file_path),
                    'modified': datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M')
                })
    
    # 恶意软件样本
    malware_dir = '/Users/zzw4257/Documents/ZJU_archieve/25-seed/gophish基础实验/malware_analysis'
    if os.path.exists(malware_dir):
        for root, dirs, files in os.walk(malware_dir):
            for file in files:
                if file.endswith(('.py', '.db', '.json', '.txt')):
                    file_path = os.path.join(root, file)
                    inventory['malware_samples'].append({
                        'name': file,
                        'path': file_path,
                        'directory': os.path.relpath(root, malware_dir),
                        'size': os.path.getsize(file_path),
                        'modified': datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M')
                    })
    
    # 红蓝对抗数据
    red_blue_dir = '/Users/zzw4257/Documents/ZJU_archieve/25-seed/gophish基础实验/red_blue_teams'
    if os.path.exists(red_blue_dir):
        for file in os.listdir(red_blue_dir):
            if not file.startswith('.') and not file == '__pycache__':
                file_path = os.path.join(red_blue_dir, file)
                if os.path.isfile(file_path):
                    inventory['red_blue_data'].append({
                        'name': file,
                        'path': file_path,
                        'size': os.path.getsize(file_path),
                        'modified': datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M')
                    })
    
    return inventory

def get_gophish_data():
    """获取Gophish完整数据"""
    if not automation:
        return {}
    
    try:
        data = {
            'campaigns': [],
            'groups': [],
            'templates': [],
            'pages': [],
            'smtp_profiles': [],
            'results_summary': {}
        }
        
        # 获取所有资源
        resources = automation.list_all_resources()
        
        for resource_type, items in resources.items():
            if resource_type in data:
                data[resource_type] = items
        
        # 获取活动结果摘要
        results = automation.get_campaign_results()
        for campaign_id, campaign_data in results.items():
            data['results_summary'][campaign_id] = campaign_data['summary']
        
        return data
    except Exception as e:
        print(f"获取Gophish数据失败: {e}")
        return {}

def get_vulnerability_stats():
    """获取漏洞利用统计"""
    stats = {
        'xss_attacks': 0,
        'sqli_attacks': 0, 
        'heartbleed_attacks': 0,
        'total_victims': 0,
        'estimated_loss': 0
    }
    
    # 读取损失评估数据
    try:
        dashboard_db = '/Users/zzw4257/Documents/ZJU_archieve/25-seed/gophish基础实验/dashboard/attack_logs.db'
        if os.path.exists(dashboard_db):
            conn = sqlite3.connect(dashboard_db)
            cursor = conn.cursor()
            
            # 统计各类攻击
            cursor.execute("SELECT attack_type, COUNT(*) FROM attack_logs GROUP BY attack_type")
            for attack_type, count in cursor.fetchall():
                if 'xss' in attack_type.lower():
                    stats['xss_attacks'] = count
                elif 'sql' in attack_type.lower():
                    stats['sqli_attacks'] = count
                elif 'heartbleed' in attack_type.lower():
                    stats['heartbleed_attacks'] = count
            
            # 计算总受害者和损失
            cursor.execute("SELECT COUNT(DISTINCT victim_email) FROM attack_logs")
            stats['total_victims'] = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT SUM(estimated_loss) FROM attack_logs")
            stats['estimated_loss'] = cursor.fetchone()[0] or 0
            
            conn.close()
    except Exception as e:
        print(f"读取漏洞统计失败: {e}")
    
    return stats

@app.route('/')
def dashboard():
    """主表盘页面"""
    system_status = get_system_status()
    file_inventory = get_file_inventory()
    gophish_data = get_gophish_data()
    vulnerability_stats = get_vulnerability_stats()
    
    return render_template('dashboard.html',
                         system_status=system_status,
                         file_inventory=file_inventory,
                         gophish_data=gophish_data,
                         vulnerability_stats=vulnerability_stats,
                         recommended_targets=RECOMMENDED_TARGETS)

@app.route('/api/system_status')
def api_system_status():
    """系统状态API"""
    return jsonify(get_system_status())

@app.route('/api/refresh_data')
def api_refresh_data():
    """刷新数据API"""
    return jsonify({
        'system_status': get_system_status(),
        'gophish_data': get_gophish_data(),
        'vulnerability_stats': get_vulnerability_stats(),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/generate_content', methods=['POST'])
def generate_content():
    """生成AI内容"""
    if not ai_generator:
        flash('AI生成器未初始化', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        content_type = request.form.get('content_type')
        scenario_type = request.form.get('scenario_type', 'security_alert')
        company_name = request.form.get('company_name', 'XX公司')
        
        if content_type == 'email':
            result = ai_generator.generate_phishing_email(
                campaign_type=scenario_type,
                target_company=company_name
            )
            if result:
                # 保存到Gophish
                if automation:
                    automation.create_email_template(result)
                flash(f'邮件模板生成成功: {result["name"]}', 'success')
            else:
                flash('邮件模板生成失败', 'error')
                
        elif content_type == 'page':
            page_type = request.form.get('page_type', 'login')
            style = request.form.get('style', 'corporate')
            
            result = ai_generator.generate_landing_page(
                page_type=page_type,
                company_name=company_name,
                style=style
            )
            if result:
                # 保存到Gophish
                if automation:
                    automation.create_landing_page(result)
                flash(f'钓鱼页面生成成功: {result["name"]}', 'success')
            else:
                flash('钓鱼页面生成失败', 'error')
    
    except Exception as e:
        flash(f'生成失败: {str(e)}', 'error')
    
    return redirect(url_for('dashboard'))

@app.route('/batch_setup', methods=['POST'])
def batch_setup():
    """批量设置"""
    if not batch_generator:
        flash('批量生成器未初始化', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        # 运行完整环境设置
        batch_generator.create_comprehensive_setup()
        flash('批量设置完成！请查看Gophish管理界面', 'success')
    except Exception as e:
        flash(f'批量设置失败: {str(e)}', 'error')
    
    return redirect(url_for('dashboard'))

@app.route('/send_phishing_emails', methods=['POST'])
def send_phishing_emails():
    """发送钓鱼邮件"""
    if not automation:
        flash('自动化工具未初始化', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        # 创建推荐目标用户组
        target_users = []
        for target in RECOMMENDED_TARGETS:
            target_users.append({
                'first_name': target['name'].split('测试用户')[0] if '测试用户' in target['name'] else target['name'],
                'last_name': target['name'].split('测试用户')[1] if '测试用户' in target['name'] else '',
                'email': target['email'],
                'position': target['position']
            })
        
        # 创建用户组
        group = automation.create_user_group("推荐测试目标组", target_users)
        
        if group:
            # 获取现有的模板和页面
            templates = automation.api.templates.get()
            pages = automation.api.pages.get()
            smtp_profiles = automation.api.smtp.get()
            
            if templates and pages and smtp_profiles:
                # 创建钓鱼活动
                campaign = automation.create_campaign(
                    campaign_name=f"批量钓鱼测试_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    group_name=group.name,
                    template_name=templates[0].name,
                    page_name=pages[0].name,
                    smtp_name=smtp_profiles[0].name,
                    url="http://localhost:5001"  # 指向XSS服务器
                )
                
                if campaign:
                    flash(f'钓鱼活动创建成功！已向{len(target_users)}个目标发送邮件', 'success')
                else:
                    flash('钓鱼活动创建失败', 'error')
            else:
                flash('缺少必要的模板、页面或SMTP配置', 'error')
        else:
            flash('用户组创建失败', 'error')
            
    except Exception as e:
        flash(f'发送失败: {str(e)}', 'error')
    
    return redirect(url_for('dashboard'))

@app.route('/view_file/<path:filepath>')
def view_file(filepath):
    """查看文件内容"""
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            return render_template('file_viewer.html', 
                                 filename=os.path.basename(filepath),
                                 filepath=filepath,
                                 content=content)
        else:
            flash('文件不存在', 'error')
            return redirect(url_for('dashboard'))
    except Exception as e:
        flash(f'文件读取失败: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

@app.route('/vulnerability_dashboard')
def vulnerability_dashboard():
    """漏洞利用仪表板"""
    vulnerability_stats = get_vulnerability_stats()
    
    # 获取详细攻击日志
    attack_logs = []
    try:
        dashboard_db = '/Users/zzw4257/Documents/ZJU_archieve/25-seed/gophish基础实验/dashboard/attack_logs.db'
        if os.path.exists(dashboard_db):
            conn = sqlite3.connect(dashboard_db)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT timestamp, attack_type, victim_email, victim_data, 
                       estimated_loss, success FROM attack_logs 
                ORDER BY timestamp DESC LIMIT 50
            """)
            
            for row in cursor.fetchall():
                attack_logs.append({
                    'timestamp': row[0],
                    'attack_type': row[1],
                    'victim_email': row[2],
                    'victim_data': row[3],
                    'estimated_loss': row[4],
                    'success': row[5]
                })
            
            conn.close()
    except Exception as e:
        print(f"读取攻击日志失败: {e}")
    
    return render_template('vulnerability_dashboard.html',
                         vulnerability_stats=vulnerability_stats,
                         attack_logs=attack_logs)

if __name__ == '__main__':
    # 创建模板目录
    os.makedirs('templates', exist_ok=True)
    
    print("🎯 启动Gophish AI自动化管理表盘")
    print("📍 访问地址: http://localhost:6789")
    print("🔧 功能包括:")
    print("  • 系统状态监控")
    print("  • 文件清单管理") 
    print("  • AI内容生成")
    print("  • 批量邮件发送")
    print("  • 漏洞利用可视化")
    
    app.run(host='0.0.0.0', port=6789, debug=True)
