#!/usr/bin/env python3
"""
SEED邮件系统 - Roundcube集成脚本
为29-email-system添加完整的Webmail功能
"""

import os
import yaml
import subprocess

def create_roundcube_compose():
    """创建Roundcube的docker-compose配置"""
    
    compose_config = {
        'version': '3.8',
        'services': {
            'roundcube': {
                'image': 'roundcube/roundcubemail:latest',
                'container_name': 'seed-roundcube',
                'restart': 'unless-stopped',
                'ports': ['8000:80'],
                'environment': {
                    'ROUNDCUBEMAIL_DEFAULT_HOST': 'ssl://mail.seedemail.net',
                    'ROUNDCUBEMAIL_DEFAULT_PORT': '993',
                    'ROUNDCUBEMAIL_SMTP_SERVER': 'tls://mail.seedemail.net',
                    'ROUNDCUBEMAIL_SMTP_PORT': '587',
                    'ROUNDCUBEMAIL_UPLOAD_MAX_FILESIZE': '5M',
                    'ROUNDCUBEMAIL_DB_TYPE': 'sqlite',
                    'ROUNDCUBEMAIL_SKIN': 'elastic',
                    'ROUNDCUBEMAIL_PLUGINS': 'archive,zipdownload,managesieve'
                },
                'volumes': [
                    './roundcube-data:/var/www/html',
                    './roundcube-db:/var/roundcube/db'
                ],
                'networks': ['seed-mail-network']
            },
            
            'nginx-proxy': {
                'image': 'nginx:alpine',
                'container_name': 'seed-mail-proxy',
                'ports': ['8081:80'],
                'volumes': ['./nginx.conf:/etc/nginx/nginx.conf:ro'],
                'depends_on': ['roundcube'],
                'networks': ['seed-mail-network']
            }
        },
        
        'networks': {
            'seed-mail-network': {
                'external': True,
                'name': 'output_default'  # 连接到SEED的网络
            }
        },
        
        'volumes': {
            'roundcube-data': {},
            'roundcube-db': {}
        }
    }
    
    with open('docker-compose-roundcube.yml', 'w') as f:
        yaml.dump(compose_config, f, default_flow_style=False)
    
    print("✅ Roundcube compose配置已创建")

def create_nginx_config():
    """创建Nginx代理配置"""
    
    nginx_config = """
events {
    worker_connections 1024;
}

http {
    upstream roundcube {
        server roundcube:80;
    }
    
    upstream seed-webui {
        server host.docker.internal:5000;
    }
    
    server {
        listen 80;
        server_name localhost;
        
        # Roundcube webmail
        location /webmail/ {
            proxy_pass http://roundcube/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
        
        # SEED管理界面
        location / {
            proxy_pass http://seed-webui/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
        
        # 健康检查
        location /health {
            access_log off;
            return 200 "healthy";
            add_header Content-Type text/plain;
        }
    }
}
"""
    
    with open('nginx.conf', 'w') as f:
        f.write(nginx_config)
    
    print("✅ Nginx配置已创建")

def create_roundcube_config():
    """创建Roundcube详细配置"""
    
    # 创建配置目录
    os.makedirs('roundcube-config', exist_ok=True)
    
    config_php = """<?php
/*
 * SEED邮件系统 Roundcube配置
 */

$config = array();

// 数据库配置
$config['db_dsnw'] = 'sqlite:////var/roundcube/db/sqlite.db?mode=0646';

// IMAP配置
$config['default_host'] = array(
    'ssl://localhost' => 'SEED邮件系统 (本地)',
    'ssl://mail.seedemail.net' => 'SeedEmail.net',
    'ssl://mail.corporate.local' => 'Corporate Local', 
    'ssl://mail.smallbiz.org' => 'Small Business'
);

$config['default_port'] = 993;
$config['imap_conn_options'] = array(
    'ssl' => array(
        'verify_peer' => false,
        'verify_peer_name' => false,
        'allow_self_signed' => true
    )
);

// SMTP配置
$config['smtp_server'] = 'tls://localhost';
$config['smtp_port'] = 587;
$config['smtp_user'] = '%u';
$config['smtp_pass'] = '%p';

$config['smtp_conn_options'] = array(
    'ssl' => array(
        'verify_peer' => false,
        'verify_peer_name' => false,
        'allow_self_signed' => true
    )
);

// 界面配置
$config['skin'] = 'elastic';
$config['language'] = 'zh_CN';
$config['date_format'] = 'Y-m-d';
$config['time_format'] = 'H:i';

// 功能配置
$config['enable_installer'] = false;
$config['auto_create_user'] = true;
$config['check_all_folders'] = true;

// 插件
$config['plugins'] = array(
    'archive',
    'zipdownload',
    'managesieve'
);

// 上传限制
$config['max_message_size'] = '5M';

// 日志
$config['log_driver'] = 'stdout';
$config['log_level'] = RCUBE_LOG_WARNING;

// 安全
$config['force_https'] = false;
$config['use_https'] = false;
$config['login_autocomplete'] = 2;

// 会话
$config['session_lifetime'] = 60; // 60分钟

return $config;
?>"""
    
    with open('roundcube-config/config.inc.php', 'w') as f:
        f.write(config_php)
    
    print("✅ Roundcube配置文件已创建")

def update_webmail_server():
    """更新webmail_server.py以集成Roundcube"""
    
    # 读取现有文件
    with open('webmail_server.py', 'r') as f:
        content = f.read()
    
    # 添加Roundcube集成路由
    roundcube_routes = """

@app.route('/roundcube')
def roundcube_redirect():
    \"\"\"重定向到Roundcube webmail\"\"\"
    return redirect('http://localhost:8081/webmail/', code=302)

@app.route('/webmail')
def webmail_redirect():
    \"\"\"重定向到Roundcube webmail\"\"\"
    return redirect('http://localhost:8081/webmail/', code=302)

@app.route('/start_roundcube', methods=['POST'])
def start_roundcube():
    \"\"\"启动Roundcube服务\"\"\"
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
    \"\"\"停止Roundcube服务\"\"\"
    try:
        success, output, error = run_command('docker-compose -f docker-compose-roundcube.yml down')
        
        if success:
            return jsonify({'success': True, 'message': 'Roundcube webmail已停止'})
        else:
            return jsonify({'success': False, 'message': f'停止失败: {error}'})
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'停止错误: {str(e)}'})
"""
    
    # 在最后的 if __name__ == '__main__': 之前插入新路由
    insertion_point = content.find("if __name__ == '__main__':")
    if insertion_point != -1:
        new_content = content[:insertion_point] + roundcube_routes + "\n" + content[insertion_point:]
        
        with open('webmail_server.py', 'w') as f:
            f.write(new_content)
        
        print("✅ webmail_server.py已更新，添加Roundcube集成")
    else:
        print("⚠️  未能自动更新webmail_server.py，请手动添加Roundcube路由")

def update_templates():
    """更新模板以添加Roundcube链接"""
    
    # 读取index.html模板
    try:
        with open('templates/index.html', 'r') as f:
            content = f.read()
        
        # 在卡片区域添加Roundcube卡片
        roundcube_card = """
                    <div class="col-md-4">
                        <div class="card border-info">
                            <div class="card-header bg-info text-white">
                                <h6 class="mb-0">📧 Roundcube Webmail</h6>
                            </div>
                            <div class="card-body">
                                <p class="card-text">完整的Web邮件客户端</p>
                                <div class="d-grid gap-2">
                                    <button class="btn btn-info" onclick="startRoundcube()">启动 Roundcube</button>
                                    <a href="http://localhost:8081/webmail/" target="_blank" class="btn btn-outline-info">
                                        访问 Webmail
                                    </a>
                                    <button class="btn btn-outline-secondary" onclick="stopRoundcube()">停止服务</button>
                                </div>
                            </div>
                        </div>
                    </div>"""
        
        # 查找合适的插入位置 (在邮件服务器卡片后)
        insertion_point = content.find('</div>\n                </div>\n            </div>')
        if insertion_point != -1:
            new_content = content[:insertion_point] + roundcube_card + content[insertion_point:]
            
            # 添加JavaScript函数
            js_functions = """
    
    // Roundcube控制函数
    function startRoundcube() {
        fetch('/start_roundcube', {method: 'POST'})
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showAlert(data.message, 'success');
                setTimeout(() => {
                    window.open('http://localhost:8081/webmail/', '_blank');
                }, 2000);
            } else {
                showAlert(data.message, 'danger');
            }
        })
        .catch(error => showAlert('请求失败: ' + error, 'danger'));
    }
    
    function stopRoundcube() {
        if (confirm('确定要停止Roundcube服务吗？')) {
            fetch('/stop_roundcube', {method: 'POST'})
            .then(response => response.json())
            .then(data => {
                showAlert(data.message, data.success ? 'success' : 'danger');
            })
            .catch(error => showAlert('请求失败: ' + error, 'danger'));
        }
    }"""
            
            # 在</script>之前添加JavaScript
            script_end = new_content.rfind('</script>')
            if script_end != -1:
                new_content = new_content[:script_end] + js_functions + new_content[script_end:]
            
            with open('templates/index.html', 'w') as f:
                f.write(new_content)
            
            print("✅ index.html模板已更新")
        else:
            print("⚠️  未能自动更新模板，请手动添加Roundcube卡片")
    
    except Exception as e:
        print(f"❌ 更新模板失败: {e}")

def main():
    """主函数"""
    print("🚀====================================================================🚀")
    print("           SEED邮件系统 - Roundcube集成工具")
    print("           为29-email-system添加完整Webmail功能")
    print("🚀====================================================================🚀")
    print("")
    
    print("📦 创建Roundcube集成文件...")
    
    # 创建配置文件
    create_roundcube_compose()
    create_nginx_config()
    create_roundcube_config()
    
    print("")
    print("🔧 更新现有代码...")
    
    # 更新代码
    update_webmail_server()
    update_templates()
    
    print("")
    print("📋 集成完成说明:")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("")
    print("🎯 访问地址:")
    print("  📧 SEED管理界面: http://localhost:5000")
    print("  📮 Roundcube Webmail: http://localhost:8081/webmail/")
    print("  🔗 统一入口: http://localhost:8081/")
    print("")
    print("🔐 预设测试账户:")
    print("  📧 alice@seedemail.net (密码: password123)")
    print("  📧 bob@seedemail.net (密码: password123)")
    print("  📧 admin@corporate.local (密码: admin123)")
    print("  📧 info@smallbiz.org (密码: info123)")
    print("")
    print("⚙️  启动步骤:")
    print("1. 重启SEED Web界面: pkill -f webmail_server && python3 webmail_server.py")
    print("2. 启动Roundcube: docker-compose -f docker-compose-roundcube.yml up -d")
    print("3. 访问统一界面: http://localhost:8081/")
    print("")
    print("💡 使用说明:")
    print("- 使用SEED界面进行系统管理和账户创建")
    print("- 使用Roundcube进行完整的邮件收发")
    print("- 两个界面通过Nginx代理统一访问")
    print("")
    print("🚀====================================================================🚀")
    print("                    Roundcube集成完成")
    print("🚀====================================================================🚀")

if __name__ == '__main__':
    main()
