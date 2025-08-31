#!/usr/bin/env python3
"""
SEED 邮件系统 - Web管理界面
简洁的邮件分发和测试界面
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
try:
    from flask_caching import Cache
except ImportError:
    Cache = None
import subprocess
import re
import html
from werkzeug.utils import secure_filename
from functools import wraps

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


def validate_input(input_str, max_length=1000, allowed_chars=None):
    """输入验证函数"""
    if not input_str:
        return False
    
    if len(input_str) > max_length:
        return False
    
    # 检查危险字符
    dangerous_patterns = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'vbscript:',
        r'on\w+\s*=',
        r'<iframe[^>]*>.*?</iframe>',
        r'sql.*union.*select',
        r'drop\s+table',
        r'delete\s+from',
        r'insert\s+into'
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, input_str, re.IGNORECASE):
            return False
    
    return True

def sanitize_input(input_str):
    """清理用户输入"""
    if not input_str:
        return ""
    
    # HTML转义
    sanitized = html.escape(input_str)
    
    # 移除潜在危险字符
    sanitized = re.sub(r'[<>"\'`;]', '', sanitized)
    
    return sanitized.strip()

def require_valid_input(f):
    """装饰器：验证输入"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method == 'POST':
            if request.is_json:
                data = request.get_json()
                for key, value in data.items():
                    if isinstance(value, str):
                        if not validate_input(value):
                            return jsonify({'success': False, 'message': '无效输入'}), 400
                        data[key] = sanitize_input(value)
            else:
                for key, value in request.form.items():
                    if not validate_input(value):
                        return jsonify({'success': False, 'message': '无效输入'}), 400
        return f(*args, **kwargs)
    return decorated_function

app.secret_key = 'seed-email-test-29'

# 邮件服务器配置
MAIL_SERVERS = [
    {
        'name': 'seedemail.net',
        'container': 'mail-150-seedemail',
        'domain': 'seedemail.net',
        'smtp_port': '2525',
        'imap_port': '1430',
        'internal_ip': '10.150.0.10',
        'as_number': '150'
    },
    {
        'name': 'corporate.local',
        'container': 'mail-151-corporate', 
        'domain': 'corporate.local',
        'smtp_port': '2526',
        'imap_port': '1431',
        'internal_ip': '10.151.0.10',
        'as_number': '151'
    },
    {
        'name': 'smallbiz.org',
        'container': 'mail-152-smallbiz',
        'domain': 'smallbiz.org', 
        'smtp_port': '2527',
        'imap_port': '1432',
        'internal_ip': '10.152.0.10',
        'as_number': '152'
    }
]

def run_command(cmd):
    """执行系统命令"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timeout"
    except Exception as e:
        return False, "", str(e)

def get_container_status():
    """获取所有容器状态"""
    success, output, error = run_command("cd output && docker-compose ps --format json")
    if not success:
        return []
    
    containers = []
    for line in output.strip().split('\n'):
        if line.strip():
            try:
                container = json.loads(line)
                containers.append(container)
            except json.JSONDecodeError:
                continue
    return containers

def get_mail_accounts(container_name):
    """获取邮件账户列表"""
    success, output, error = run_command(f"docker exec {container_name} setup email list 2>/dev/null")
    if not success:
        return []
    
    accounts = []
    for line in output.split('\n'):
        if '@' in line and '(' in line:
            # 解析格式: * alice@seedemail.net ( 0 / ~ ) [0%]
            email = line.split('*')[-1].split('(')[0].strip()
            if email and '@' in email:
                accounts.append(email)
    return accounts

@app.route('/')
def index():
    """主页 - 系统概览"""
    containers = get_container_status()
    mail_containers = [c for c in containers if 'mail-' in c.get('Name', '')]
    
    # 获取系统状态
    system_info = {
        'total_containers': len(containers),
        'mail_servers': len(mail_containers),
        'running_containers': len([c for c in containers if c.get('State') == 'running']),
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    return render_template('index.html', 
                         mail_servers=MAIL_SERVERS,
                         containers=mail_containers,
                         system_info=system_info)

@app.route('/server/<server_name>')
def server_detail(server_name):
    """邮件服务器详情页"""
    server = next((s for s in MAIL_SERVERS if s['name'] == server_name), None)
    if not server:
        flash(f'邮件服务器 {server_name} 不存在', 'error')
        return redirect(url_for('index'))
    
    # 获取邮件账户
    accounts = get_mail_accounts(server['container'])
    
    # 获取容器状态
    containers = get_container_status()
    container_status = next((c for c in containers if server['container'] in c.get('Name', '')), None)
    
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    return render_template('server_detail.html',
                         server=server,
                         accounts=accounts,
                         container_status=container_status,
                         current_time=current_time)

@require_valid_input
@app.route('/create_account', methods=['POST'])
def create_account():
    """创建邮件账户"""
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'success': False, 'message': '邮箱和密码不能为空'})
    
    # 确定容器名称
    domain = email.split('@')[-1]
    server = next((s for s in MAIL_SERVERS if s['domain'] == domain), None)
    if not server:
        return jsonify({'success': False, 'message': f'不支持的域名: {domain}'})
    
    # 创建账户
    cmd = f'printf "{password}\\n{password}\\n" | docker exec -i {server["container"]} setup email add {email}'
    success, output, error = run_command(cmd)
    
    if success:
        return jsonify({'success': True, 'message': f'账户 {email} 创建成功'})
    else:
        return jsonify({'success': False, 'message': f'创建失败: {error}'})

@app.route('/delete_account', methods=['POST'])
def delete_account():
    """删除邮件账户"""
    data = request.get_json()
    email = data.get('email')
    
    if not email:
        return jsonify({'success': False, 'message': '邮箱地址不能为空'})
    
    # 确定容器名称
    domain = email.split('@')[-1]
    server = next((s for s in MAIL_SERVERS if s['domain'] == domain), None)
    if not server:
        return jsonify({'success': False, 'message': f'不支持的域名: {domain}'})
    
    # 删除账户
    cmd = f'docker exec {server["container"]} setup email del {email}'
    success, output, error = run_command(cmd)
    
    if success:
        return jsonify({'success': True, 'message': f'账户 {email} 删除成功'})
    else:
        return jsonify({'success': False, 'message': f'删除失败: {error}'})

@require_valid_input
@app.route('/test_connectivity', methods=['POST'])
def test_connectivity():
    """测试网络连通性"""
    data = request.get_json()
    target = data.get('target', '10.100.0.2')
    
    # 从客户端容器测试连通性
    cmd = f'docker exec as160h-host_0-10.160.0.71 ping -c 2 {target}'
    success, output, error = run_command(cmd)
    
    return jsonify({
        'success': success,
        'output': output,
        'error': error,
        'target': target
    })

@require_valid_input
@app.route('/send_test_email', methods=['POST'])
def send_test_email():
    """发送测试邮件"""
    data = request.get_json()
    from_email = data.get('from_email')
    to_email = data.get('to_email') 
    subject = data.get('subject', 'SEED测试邮件')
    body = data.get('body', '这是来自SEED邮件系统的测试邮件')
    
    if not from_email or not to_email:
        return jsonify({'success': False, 'message': '发件人和收件人不能为空'})
    
    # 确定SMTP服务器
    from_domain = from_email.split('@')[-1]
    server = next((s for s in MAIL_SERVERS if s['domain'] == from_domain), None)
    if not server:
        return jsonify({'success': False, 'message': f'不支持的发件域名: {from_domain}'})
    
    # 使用swaks发送测试邮件 (如果容器内有安装)
    cmd = f'''docker exec {server["container"]} sh -c "
        echo 'Subject: {subject}
        
        {body}' | sendmail {to_email}
    " '''
    
    success, output, error = run_command(cmd)
    
    if success:
        return jsonify({'success': True, 'message': f'测试邮件已发送: {from_email} -> {to_email}'})
    else:
        return jsonify({'success': False, 'message': f'发送失败: {error}'})

@app.route('/api/status')
def api_status():
    """API状态接口"""
    containers = get_container_status()
    mail_containers = [c for c in containers if 'mail-' in c.get('Name', '')]
    
    status = {
        'total_containers': len(containers),
        'mail_servers': len(mail_containers), 
        'running_containers': len([c for c in containers if c.get('State') == 'running']),
        'servers': []
    }
    
    for server in MAIL_SERVERS:
        container_status = next((c for c in containers if server['container'] in c.get('Name', '')), None)
        accounts = get_mail_accounts(server['container'])
        
        status['servers'].append({
            'name': server['name'],
            'domain': server['domain'],
            'status': container_status.get('State') if container_status else 'unknown',
            'accounts_count': len(accounts),
            'ports': {
                'smtp': server['smtp_port'],
                'imap': server['imap_port']
            }
        })
    
    return jsonify(status)



@app.route('/roundcube')
def roundcube_redirect():
    """重定向到Roundcube webmail"""
    return redirect('http://localhost:8081/webmail/', code=302)

@app.route('/webmail')
def webmail_redirect():
    """重定向到Roundcube webmail"""
    return redirect('http://localhost:8081/webmail/', code=302)

@app.route('/start_roundcube', methods=['POST'])
def start_roundcube():
    """启动Roundcube服务"""
    try:
        # 检查docker-compose文件是否存在
        if not os.path.exists('docker-compose-roundcube.yml'):
            return jsonify({'success': False, 'message': 'Roundcube配置文件不存在，请先运行集成脚本'})
        
        # 启动Roundcube
        success, output, error = run_command('docker-compose -f docker-compose-roundcube.yml up -d')
        
        if success:
            return jsonify({'success': True, 'message': 'Roundcube webmail已启动，访问: http://localhost:8081/webmail/'})
        else:
            return jsonify({'success': False, 'message': f'启动失败: {error}'})
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'启动错误: {str(e)}'})

@app.route('/stop_roundcube', methods=['POST'])
def stop_roundcube():
    """停止Roundcube服务"""
    try:
        success, output, error = run_command('docker-compose -f docker-compose-roundcube.yml down')
        
        if success:
            return jsonify({'success': True, 'message': 'Roundcube webmail已停止'})
        else:
            return jsonify({'success': False, 'message': f'停止失败: {error}'})
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'停止错误: {str(e)}'})

@app.route('/project_overview')
def project_overview():
    """项目概述页面"""
    return render_template('project_overview.html')

@app.route('/api/system_info')
def system_info():
    """系统信息API"""
    try:
        containers = get_container_status()
        mail_containers = [c for c in containers if 'mail-' in c.get('Name', '')]
        
        # 获取运行时间
        try:
            import psutil
        except ImportError:
            psutil = None
        uptime = time.time() - app.start_time if hasattr(app, 'start_time') else 0
        
        status = {
            'mail_servers': len(mail_containers),
            'total_containers': len(containers),
            'uptime': f"{int(uptime // 60)}分{int(uptime % 60)}秒",
            'version': '1.0.0',
            'project': 'SEED邮件系统 29-email-system',
            'framework': 'SEED-Emulator + Flask',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': str(e)})


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

if __name__ == '__main__':
    # 记录启动时间
    app.start_time = time.time()
    
    print("""
    ╭─────────────────────────────────────────────────────────────╮
    │                SEED 邮件系统 Web 管理界面                      │
    │                   29-email-system 测试网络                   │
    ╰─────────────────────────────────────────────────────────────╯
    
    🌐 访问地址: http://localhost:5000
    📧 邮件服务器管理和测试界面
    🔧 网络连通性测试
    📊 系统状态监控
    📖 项目概述: http://localhost:5000/project_overview
    
    """)
    app.run(host='0.0.0.0', port=5000, debug=True)
