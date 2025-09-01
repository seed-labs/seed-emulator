#!/usr/bin/env python3
"""
SEED邮件系统 - 真实版Web管理界面 (29-1-email-system)
提供真实邮件服务商管理和DNS系统测试功能
"""

from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
try:
    from flask_caching import Cache
except ImportError:
    Cache = None
import subprocess
import json
import os
import time
try:
    import psutil
except ImportError:
    psutil = None
from datetime import datetime

app = Flask(__name__)
# 缓存配置
if Cache:
    cache_config = {
        'CACHE_TYPE': 'simple',
        'CACHE_DEFAULT_TIMEOUT': 300
    }
    cache = Cache(config=cache_config)
    cache.init_app(app)
else:
    cache = None


# 真实邮件服务商配置
REAL_MAIL_PROVIDERS = [
    {
        'name': 'QQ邮箱',
        'domain': 'qq.com',
        'as_number': 200,
        'location': '深圳 (广州IX)',
        'container_prefix': 'hnode_200',
        'description': '腾讯QQ邮箱服务',
        'external_ports': {'smtp': 2520, 'imap': 1420},
        'color': 'primary'
    },
    {
        'name': '163邮箱',
        'domain': '163.com',
        'as_number': 201,
        'location': '杭州 (上海IX)',
        'container_prefix': 'hnode_201',
        'description': '网易163邮箱服务',
        'external_ports': {'smtp': 2521, 'imap': 1421},
        'color': 'success'
    },
    {
        'name': 'Gmail',
        'domain': 'gmail.com',
        'as_number': 202,
        'location': '海外 (全球IX)',
        'container_prefix': 'hnode_202',
        'description': 'Google Gmail服务',
        'external_ports': {'smtp': 2522, 'imap': 1422},
        'color': 'warning'
    },
    {
        'name': 'Outlook',
        'domain': 'outlook.com',
        'as_number': 203,
        'location': '海外 (全球IX)',
        'container_prefix': 'hnode_203',
        'description': 'Microsoft Outlook服务',
        'external_ports': {'smtp': 2523, 'imap': 1423},
        'color': 'info'
    },
    {
        'name': 'Yahoo邮箱',
        'domain': 'yahoo.com',
        'as_number': 204,
        'location': '海外 (全球IX)',
        'container_prefix': 'hnode_204',
        'description': 'Yahoo邮箱服务',
        'external_ports': {'smtp': 2524, 'imap': 1424},
        'color': 'secondary'
    },
    {
        'name': '企业邮箱',
        'domain': 'enterprise.cn',
        'as_number': 205,
        'location': '企业网络',
        'container_prefix': 'hnode_205',
        'description': '企业内部邮箱服务',
        'external_ports': {'smtp': 2525, 'imap': 1425},
        'color': 'dark'
    }
]

# Internet Exchange配置
INTERNET_EXCHANGES = [
    {'name': 'Beijing-IX', 'id': 100, 'location': '北京', 'color': 'danger'},
    {'name': 'Shanghai-IX', 'id': 101, 'location': '上海', 'color': 'primary'},
    {'name': 'Guangzhou-IX', 'id': 102, 'location': '广州', 'color': 'success'},
    {'name': 'Global-IX', 'id': 103, 'location': '国际', 'color': 'warning'}
]

# ISP配置
ISP_PROVIDERS = [
    {'name': '中国电信', 'as': 2, 'coverage': '全国', 'ix_connections': [100, 101, 102, 103]},
    {'name': '中国联通', 'as': 3, 'coverage': '北方主导', 'ix_connections': [100, 101]},
    {'name': '中国移动', 'as': 4, 'coverage': '移动网络', 'ix_connections': [100, 102]}
]

def run_command(cmd):
    """执行系统命令"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "命令执行超时"
    except Exception as e:
        return False, "", str(e)

def get_container_status():
    """获取容器状态"""
    success, output, error = run_command('docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(hnode_|brdnode_|rs_ix)"')
    containers = []
    
    if success and output:
        lines = output.strip().split('\n')
        for line in lines[1:]:  # 跳过表头
            parts = line.split('\t')
            if len(parts) >= 2:
                containers.append({
                    'Name': parts[0],
                    'Status': parts[1],
                    'Ports': parts[2] if len(parts) > 2 else ''
                })
    
    return containers

def get_network_topology():
    """获取网络拓扑信息"""
    topology = {
        'total_containers': 0,
        'running_containers': 0,
        'mail_servers': 0,
        'routers': 0,
        'exchanges': 0
    }
    
    containers = get_container_status()
    topology['total_containers'] = len(containers)
    
    for container in containers:
        if 'running' in container['Status'].lower():
            topology['running_containers'] += 1
        
        if 'hnode_' in container['Name']:
            topology['mail_servers'] += 1
        elif 'brdnode_' in container['Name']:
            topology['routers'] += 1
        elif 'rs_ix_' in container['Name']:
            topology['exchanges'] += 1
    
    return topology

@app.route('/')
def index():
    """主页"""
    topology = get_network_topology()
    
    return render_template('index.html', 
                         mail_providers=REAL_MAIL_PROVIDERS,
                         internet_exchanges=INTERNET_EXCHANGES,
                         isp_providers=ISP_PROVIDERS,
                         topology=topology)

@app.route('/provider/<int:as_number>')
def provider_detail(as_number):
    """邮件服务商详情页"""
    provider = next((p for p in REAL_MAIL_PROVIDERS if p['as_number'] == as_number), None)
    if not provider:
        return "邮件服务商不存在", 404
    
    # 获取该服务商的容器信息
    containers = get_container_status()
    provider_containers = [c for c in containers if provider['container_prefix'] in c['Name']]
    
    # 获取邮件账户 (模拟)
    accounts = get_mail_accounts(provider['domain'])
    
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    return render_template('provider_detail.html',
                         provider=provider,
                         containers=provider_containers,
                         accounts=accounts,
                         current_time=current_time)

@app.route('/network_topology')
def network_topology():
    """网络拓扑页面"""
    containers = get_container_status()
    topology = get_network_topology()
    
    return render_template('network_topology.html',
                         containers=containers,
                         topology=topology,
                         internet_exchanges=INTERNET_EXCHANGES,
                         isp_providers=ISP_PROVIDERS)

@app.route('/dns_system')
def dns_system():
    """DNS系统测试页面"""
    return render_template('dns_system.html',
                         mail_providers=REAL_MAIL_PROVIDERS)

def get_mail_accounts(domain):
    """获取邮件账户列表"""
    # 模拟邮件账户数据
    common_accounts = {
        'qq.com': ['admin@qq.com', 'service@qq.com', 'noreply@qq.com'],
        '163.com': ['admin@163.com', 'service@163.com', 'support@163.com'],
        'gmail.com': ['admin@gmail.com', 'test@gmail.com', 'demo@gmail.com'],
        'outlook.com': ['admin@outlook.com', 'info@outlook.com', 'support@outlook.com'],
        'yahoo.com': ['admin@yahoo.com', 'service@yahoo.com', 'help@yahoo.com'],
        'enterprise.cn': ['admin@enterprise.cn', 'hr@enterprise.cn', 'it@enterprise.cn']
    }
    
    return common_accounts.get(domain, [])

@app.route('/test_dns', methods=['POST'])
def test_dns():
    """测试DNS解析"""
    domain = request.json.get('domain', '')
    
    if not domain:
        return jsonify({'success': False, 'message': '请提供域名'})
    
    # 测试A记录
    success_a, output_a, error_a = run_command(f'nslookup {domain}')
    
    # 测试MX记录
    success_mx, output_mx, error_mx = run_command(f'nslookup -type=mx {domain}')
    
    result = {
        'success': True,
        'domain': domain,
        'a_record': {
            'success': success_a,
            'output': output_a,
            'error': error_a
        },
        'mx_record': {
            'success': success_mx,
            'output': output_mx,
            'error': error_mx
        }
    }
    
    return jsonify(result)

@app.route('/test_connectivity', methods=['POST'])
def test_connectivity():
    """测试网络连通性"""
    target = request.json.get('target', '')
    
    if not target:
        return jsonify({'success': False, 'message': '请提供测试目标'})
    
    success, output, error = run_command(f'ping -c 3 {target}')
    
    return jsonify({
        'success': success,
        'target': target,
        'output': output,
        'error': error
    })

@app.route('/send_cross_provider_email', methods=['POST'])
def send_cross_provider_email():
    """发送跨服务商邮件测试"""
    from_provider = request.json.get('from_provider')
    to_provider = request.json.get('to_provider')
    subject = request.json.get('subject', '跨服务商邮件测试')
    body = request.json.get('body', '这是一封跨服务商的测试邮件')
    
    # 构造测试邮件命令
    from_domain = next((p['domain'] for p in REAL_MAIL_PROVIDERS if p['as_number'] == from_provider), '')
    to_domain = next((p['domain'] for p in REAL_MAIL_PROVIDERS if p['as_number'] == to_provider), '')
    
    if not from_domain or not to_domain:
        return jsonify({'success': False, 'message': '无效的服务商'})
    
    # 模拟邮件发送测试
    test_result = {
        'success': True,
        'message': f'已模拟从 {from_domain} 发送邮件到 {to_domain}',
        'details': {
            'from': f'test@{from_domain}',
            'to': f'test@{to_domain}',
            'subject': subject,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    }
    
    return jsonify(test_result)

@app.route('/api/system_status')
def system_status():
    """系统状态API"""
    topology = get_network_topology()
    containers = get_container_status()
    
    # 计算运行时间
    uptime = time.time() - app.start_time if hasattr(app, 'start_time') else 0
    
    status = {
        'topology': topology,
        'containers': len(containers),
        'uptime': f"{int(uptime // 60)}分{int(uptime % 60)}秒",
        'version': '1.0.0',
        'project': 'SEED邮件系统 29-1-email-system (真实版)',
        'features': ['DNS系统', '真实服务商', '多IX架构', '跨网测试'],
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    return jsonify(status)

@app.route('/project_overview')
def project_overview():
    """项目概述页面"""
    return render_template('project_overview_29_1.html',
                         mail_providers=REAL_MAIL_PROVIDERS,
                         internet_exchanges=INTERNET_EXCHANGES,
                         isp_providers=ISP_PROVIDERS)


@app.errorhandler(404)
def not_found_error(error):
    return render_template('error.html', 
                         error_code=404, 
                         error_message='页面未找到'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', 
                         error_code=500, 
                         error_message='服务器内部错误'), 500

@app.errorhandler(Exception)
def handle_exception(e):
    # 记录错误日志
    app.logger.error(f'未处理的异常: {str(e)}')
    
    # 返回友好的错误信息
    if app.debug:
        return str(e), 500
    else:
        return render_template('error.html', 
                             error_code=500, 
                             error_message='系统遇到了问题，请稍后重试'), 500


import psutil
import logging
from logging.handlers import RotatingFileHandler

# 配置日志
if not app.debug:
    handler = RotatingFileHandler('seed_email.log', maxBytes=10240000, backupCount=10)
    handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    handler.setLevel(logging.INFO)
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('SEED邮件系统启动')

@app.route('/api/system_health')
def system_health():
    """系统健康检查"""
    try:
        health_data = {
            'timestamp': datetime.now().isoformat(),
            'status': 'healthy',
            'system': {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': psutil.disk_usage('/').percent,
                'uptime': time.time() - app.start_time if hasattr(app, 'start_time') else 0
            },
            'services': {
                'web_server': True,
                'docker': check_docker_status(),
                'database': check_database_status()
            }
        }
        
        # 健康状态判断
        if health_data['system']['cpu_percent'] > 90:
            health_data['status'] = 'warning'
        if health_data['system']['memory_percent'] > 85:
            health_data['status'] = 'critical'
        
        return jsonify(health_data)
    except Exception as e:
        app.logger.error(f'健康检查失败: {str(e)}')
        return jsonify({'status': 'error', 'message': str(e)}), 500

def check_docker_status():
    """检查Docker状态"""
    try:
        result = subprocess.run(['docker', 'ps'], capture_output=True, timeout=5)
        return result.returncode == 0
    except:
        return False

def check_database_status():
    """检查数据库状态"""
    # 这里可以添加数据库连接检查
    return True

@app.route('/email_test')
def email_test():
    """邮件发信测试页面"""
    return render_template('email_test_29_1.html', mail_providers=REAL_MAIL_PROVIDERS)

@app.route('/api/check_user', methods=['POST'])
def check_user():
    """检查用户账户是否存在"""
    data = request.get_json()
    email = data.get('email', '').strip()
    provider_asn = data.get('provider_asn')

    if not email or not provider_asn:
        return jsonify({'success': False, 'message': '请提供邮箱地址和服务商ASN'})

    # 查找对应的邮件服务商
    provider = next((p for p in REAL_MAIL_PROVIDERS if p['as_number'] == provider_asn), None)
    if not provider:
        return jsonify({'success': False, 'message': '无效的服务商ASN'})

    # 检查邮箱格式
    if '@' not in email:
        return jsonify({'success': False, 'message': '邮箱格式不正确'})

    local_part, domain = email.split('@')
    if domain != provider['domain']:
        return jsonify({'success': False, 'message': f'邮箱域名不匹配，应为@{provider["domain"]}'})

    # 检查用户是否在服务器中存在
    try:
        # 根据域名构造容器名称
        if provider['domain'] == 'qq.com':
            container_name = 'mail-qq-tencent'
        elif provider['domain'] == '163.com':
            container_name = 'mail-163-netease'
        elif provider['domain'] == 'gmail.com':
            container_name = 'mail-gmail-google'
        elif provider['domain'] == 'outlook.com':
            container_name = 'mail-outlook-microsoft'
        elif provider['domain'] == 'company.cn':
            container_name = 'mail-company-aliyun'
        elif provider['domain'] == 'startup.net':
            container_name = 'mail-startup-selfhosted'
        else:
            return jsonify({'success': False, 'message': f'不支持的域名: {provider["domain"]}'})

        # 使用docker命令检查用户是否存在
        cmd = f"docker exec {container_name} setup email list"
        success, output, error = run_command(cmd)

        if success:
            # 解析用户列表
            users = []
            for line in output.split('\n'):
                if line.strip() and '*' in line:
                    user_email = line.split('*')[-1].split('(')[0].strip()
                    if user_email:
                        users.append(user_email)

            if email in users:
                return jsonify({
                    'success': True,
                    'message': f'用户 {email} 存在于 {provider["name"]} 服务器',
                    'user_exists': True,
                    'provider': provider
                })
            else:
                return jsonify({
                    'success': False,
                    'message': f'用户 {email} 不存在于 {provider["name"]} 服务器',
                    'user_exists': False,
                    'available_users': users
                })
        else:
            return jsonify({'success': False, 'message': f'无法连接到邮件服务器: {error}'})

    except Exception as e:
        return jsonify({'success': False, 'message': f'检查用户时出错: {str(e)}'})

@app.route('/api/send_test_email', methods=['POST'])
def send_test_email():
    """发送测试邮件"""
    data = request.get_json()
    from_email = data.get('from_email', '').strip()
    to_email = data.get('to_email', '').strip()
    subject = data.get('subject', 'SEED真实邮件系统测试邮件').strip()
    body = data.get('body', '这是一封来自SEED真实邮件系统的测试邮件。').strip()

    if not from_email or not to_email:
        return jsonify({'success': False, 'message': '发件人和收件人邮箱不能为空'})

    # 确定发件人所在的服务器
    from_provider = None
    for provider in REAL_MAIL_PROVIDERS:
        if from_email.endswith(f'@{provider["domain"]}'):
            from_provider = provider
            break

    if not from_provider:
        return jsonify({'success': False, 'message': '无法确定发件人所在的邮件服务器'})

    # 根据域名构造容器名称
    if from_provider['domain'] == 'qq.com':
        container_name = 'mail-qq-tencent'
    elif from_provider['domain'] == '163.com':
        container_name = 'mail-163-netease'
    elif from_provider['domain'] == 'gmail.com':
        container_name = 'mail-gmail-google'
    elif from_provider['domain'] == 'outlook.com':
        container_name = 'mail-outlook-microsoft'
    elif from_provider['domain'] == 'company.cn':
        container_name = 'mail-company-aliyun'
    elif from_provider['domain'] == 'startup.net':
        container_name = 'mail-startup-selfhosted'
    else:
        return jsonify({'success': False, 'message': f'不支持的域名: {from_provider["domain"]}'})

    # 使用sendmail发送测试邮件
    try:
        cmd = f"""echo "Subject: {subject}
From: {from_email}
To: {to_email}

{body}" | docker exec -i {container_name} sendmail {to_email}"""

        success, output, error = run_command(cmd)

        if success:
            return jsonify({
                'success': True,
                'message': f'邮件发送成功！从 {from_email} 发送到 {to_email}',
                'details': {
                    'from': from_email,
                    'to': to_email,
                    'subject': subject,
                    'server': container_name,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'output': output
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': f'邮件发送失败: {error}',
                'details': {
                    'error_output': error,
                    'command': cmd
                }
            })

    except Exception as e:
        return jsonify({'success': False, 'message': f'发送邮件时出错: {str(e)}'})

@app.route('/api/get_mail_providers')
def get_mail_providers():
    """获取邮件服务商列表"""
    return jsonify({'providers': REAL_MAIL_PROVIDERS})

if __name__ == '__main__':
    # 记录启动时间
    app.start_time = time.time()
    
    print("""
    ╭─────────────────────────────────────────────────────────────╮
    │             SEED 邮件系统 真实版 Web 管理界面                 │
    │                29-1-email-system 真实网络                   │
    ╰─────────────────────────────────────────────────────────────╯
    
    🌐 访问地址: http://localhost:5001
    📧 真实邮件服务商管理 (QQ/163/Gmail/Outlook等)
    🌍 DNS系统测试和验证
    🔗 跨服务商邮件传输测试
    📊 网络拓扑可视化
    📖 项目概述: http://localhost:5001/project_overview
    
    """)
    app.run(host='0.0.0.0', port=5001, debug=True)
