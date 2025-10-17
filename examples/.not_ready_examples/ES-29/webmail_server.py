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
        'id': 'seedemail',
        'name': 'seedemail.net',
        'container': 'mail-150-seedemail',
        'domain': 'seedemail.net',
        'smtp_port': '2525',
        'imap_port': '1430',
        'internal_ip': '10.150.0.10',
        'as_number': '150'
    },
    {
        'id': 'corporate',
        'name': 'corporate.local',
        'container': 'mail-151-corporate',
        'domain': 'corporate.local',
        'smtp_port': '2526',
        'imap_port': '1431',
        'internal_ip': '10.151.0.10',
        'as_number': '151'
    },
    {
        'id': 'smallbiz',
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

@app.route('/api/roundcube_status')
def roundcube_status():
    """检查Roundcube运行状态"""
    try:
        # 检查Roundcube容器是否运行
        success, output, error = run_command('docker ps --format "{{.Names}}\t{{.Status}}" | grep roundcube')
        
        if success and output:
            containers = []
            for line in output.strip().split('\n'):
                if line:
                    parts = line.split('\t')
                    containers.append({
                        'name': parts[0],
                        'status': parts[1] if len(parts) > 1 else 'unknown'
                    })
            
            # 检查Web界面是否可访问
            import urllib.request
            try:
                urllib.request.urlopen('http://localhost:8081', timeout=2)
                web_accessible = True
            except:
                web_accessible = False
            
            return jsonify({
                'success': True,
                'running': True,
                'containers': containers,
                'web_accessible': web_accessible,
                'url': 'http://localhost:8081'
            })
        else:
            return jsonify({
                'success': True,
                'running': False,
                'containers': [],
                'web_accessible': False
            })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

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

@app.route('/email_test')
def email_test():
    """邮件发信测试页面"""
    return render_template('email_test.html', mail_servers=MAIL_SERVERS)

@app.route('/api/check_user', methods=['POST'])
def check_user():
    """检查用户账户是否存在"""
    data = request.get_json()
    email = data.get('email', '').strip()
    server_id = data.get('server_id')

    if not email or not server_id:
        return jsonify({'success': False, 'message': '请提供邮箱地址和服务器ID'})

    # 查找对应的邮件服务器
    server = next((s for s in MAIL_SERVERS if s['id'] == server_id), None)
    if not server:
        return jsonify({'success': False, 'message': '无效的服务器ID'})

    # 检查邮箱格式
    if '@' not in email:
        return jsonify({'success': False, 'message': '邮箱格式不正确'})

    local_part, domain = email.split('@')
    if domain != server['domain']:
        return jsonify({'success': False, 'message': f'邮箱域名不匹配，应为@{server["domain"]}'})

    # 检查用户是否在服务器中存在
    try:
        # 使用docker命令检查用户是否存在
        cmd = f"docker exec {server['container']} setup email list"
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
                    'message': f'用户 {email} 存在于 {server["name"]} 服务器',
                    'user_exists': True,
                    'server_name': server['name'],
                    'server_domain': server['domain']
                })
            else:
                return jsonify({
                    'success': False,
                    'message': f'用户 {email} 不存在于 {server["name"]} 服务器',
                    'user_exists': False,
                    'available_users': users,
                    'server_name': server['name']
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
    subject = data.get('subject', 'SEED邮件系统测试邮件').strip()
    body = data.get('body', '这是一封来自SEED邮件系统的测试邮件。').strip()
    template_type = data.get('template', 'plain')  # plain, html, phishing

    if not from_email or not to_email:
        return jsonify({'success': False, 'message': '发件人和收件人邮箱不能为空'})

    # 确定发件人所在的服务器
    from_server = None
    for server in MAIL_SERVERS:
        if from_email.endswith(f'@{server["domain"]}'):
            from_server = server
            break

    if not from_server:
        return jsonify({'success': False, 'message': '无法确定发件人所在的邮件服务器'})

    # 根据模板类型生成邮件内容
    if template_type == 'html':
        # HTML邮件模板
        email_content = f"""From: {from_email}
To: {to_email}
Subject: {subject}
MIME-Version: 1.0
Content-Type: text/html; charset=UTF-8
Content-Transfer-Encoding: 7bit

<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{subject}</title>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #2c3e50;">{subject}</h2>
        <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
            {body.replace(chr(10), '<br>')}
        </div>
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
        <p style="font-size: 12px; color: #666;">
            此邮件由 SEED 邮件系统发送<br>
            发送时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </p>
    </div>
</body>
</html>"""
    elif template_type == 'phishing':
        # 钓鱼邮件模板（基于真实的MetaMask安全提醒模板）
        html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{subject}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
            line-height: 1.6;
            color: #333;
        }}
        .container {{
            max-width: 600px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        }}
        .header {{
            background: linear-gradient(135deg, #6f42c1, #e83e8c);
            color: white;
            padding: 30px 20px;
            text-align: center;
        }}
        .logo {{
            font-size: 28px;
            font-weight: bold;
            margin-bottom: 10px;
        }}
        .tagline {{
            font-size: 14px;
            opacity: 0.9;
        }}
        .content {{
            padding: 40px 30px;
        }}
        .alert {{
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 6px;
            padding: 20px;
            margin: 20px 0;
        }}
        .alert-title {{
            color: #856404;
            font-weight: bold;
            margin-bottom: 10px;
        }}
        .button {{
            display: inline-block;
            background: #007bff;
            color: white;
            padding: 15px 30px;
            text-decoration: none;
            border-radius: 6px;
            font-weight: bold;
            margin: 20px 0;
            transition: background-color 0.3s;
        }}
        .button:hover {{
            background: #0056b3;
        }}
        .footer {{
            background: #f8f9fa;
            padding: 20px;
            text-align: center;
            font-size: 12px;
            color: #666;
            border-top: 1px solid #dee2e6;
        }}
        .security-notice {{
            background: #d1ecf1;
            border: 1px solid #bee5eb;
            border-radius: 4px;
            padding: 15px;
            margin: 20px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">🔐 账户安全中心</div>
            <div class="tagline">保护您的数字资产安全</div>
        </div>

        <div class="content">
            <h2 style="color: #2c3e50; margin-bottom: 20px;">{subject}</h2>

            <div class="alert">
                <div class="alert-title">⚠️ 重要安全通知</div>
                <p>我们检测到您的账户可能存在安全风险。为了保护您的资产安全，请立即采取以下措施：</p>
            </div>

            <p>尊敬的用户：</p>

            <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                {body.replace(chr(10), '</p><p>').replace(chr(13), '')}
            </div>

            <p><strong>请注意：</strong> 如果您不及时处理，您的账户可能会受到影响。</p>

            <div style="text-align: center;">
                <a href="#" class="button">立即处理</a>
            </div>

            <div class="security-notice">
                <strong>安全提示：</strong>
                <ul style="margin: 10px 0; padding-left: 20px;">
                    <li>请勿点击可疑链接</li>
                    <li>定期更新密码</li>
                    <li>启用双因素认证</li>
                </ul>
            </div>

            <p>如果您有任何疑问，请通过官方网站联系我们。</p>

            <p style="color: #666; font-size: 14px;">
                此邮件由系统安全监控自动发送<br>
                如果您认为这是一封错误邮件，请忽略此消息
            </p>
        </div>

        <div class="footer">
            <p><strong>SEED 安全系统</strong></p>
            <p>网络安全实验室 | 浙江大学</p>
            <p>© 2024 SEED Lab. All rights reserved.</p>
            <p style="margin-top: 10px; font-size: 11px;">
                发送时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            </p>
        </div>
    </div>
</body>
</html>"""

        email_content = f"""From: {from_email}
To: {to_email}
Subject: {subject}
MIME-Version: 1.0
Content-Type: multipart/alternative; boundary="===============1574101848=="
X-Mailer: SEED Security System
Date: {datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')}

--===============1574101848==
Content-Type: text/plain; charset=UTF-8
Content-Transfer-Encoding: 7bit

{subject}

重要安全通知：

{body}

请立即处理相关安全事宜。

--
此邮件来自 SEED 安全监控系统
请勿回复此邮件

--===============1574101848==
Content-Type: text/html; charset=UTF-8
Content-Transfer-Encoding: 7bit

{html_content}

--===============1574101848==--"""
    else:
        # 纯文本邮件
        email_content = f"""From: {from_email}
To: {to_email}
Subject: {subject}
MIME-Version: 1.0
Content-Type: text/plain; charset=UTF-8
Content-Transfer-Encoding: 7bit

{body}

--
SEED 邮件系统
发送时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""

    # 使用sendmail发送邮件
    try:
        # 创建临时邮件文件
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(mode='w', suffix='.eml', delete=False) as f:
            f.write(email_content)
            temp_file = f.name

        # 使用sendmail发送
        cmd = f"cat {temp_file} | docker exec -i {from_server['container']} sendmail {to_email}"

        success, output, error = run_command(cmd)

        # 清理临时文件
        os.unlink(temp_file)

        if success:
            return jsonify({
                'success': True,
                'message': f'邮件发送成功！从 {from_email} 发送到 {to_email}',
                'details': {
                    'from': from_email,
                    'to': to_email,
                    'subject': subject,
                    'template': template_type,
                    'server': from_server['container'],
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
                    'command': cmd,
                    'email_content': email_content[:500] + '...' if len(email_content) > 500 else email_content
                }
            })

    except Exception as e:
        return jsonify({'success': False, 'message': f'发送邮件时出错: {str(e)}'})

@app.route('/api/get_mail_servers')
def get_mail_servers():
    """获取邮件服务器列表"""
    return jsonify({'servers': MAIL_SERVERS})

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
