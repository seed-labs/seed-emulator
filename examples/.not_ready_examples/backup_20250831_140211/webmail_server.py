#!/usr/bin/env python3
"""
SEED邮件系统 - 真实版Web管理界面 (29-1-email-system)
提供真实邮件服务商管理和DNS系统测试功能
"""

from flask import Flask
try:
    from flask_caching import Cache
except ImportError:
    Cache = None, render_template, jsonify, request, redirect
import subprocess
import json
import os
import time
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
