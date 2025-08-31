#!/usr/bin/env python3
"""
SEED邮件系统综合总览应用
端口: 4257
整合29、29-1、30、31项目的所有功能和信息
"""

import os
import json
import subprocess
import time
from datetime import datetime
from flask import Flask, render_template, jsonify, request
from pathlib import Path

app = Flask(__name__,
           template_folder='templates',
           static_folder='static')

# 项目根目录
PROJECT_ROOT = Path(__file__).parent
SEED_ROOT = PROJECT_ROOT.parent.parent

# 项目信息配置
PROJECTS_INFO = {
    "29": {
        "name": "29基础邮件系统",
        "description": "基于Docker Mailserver的基础邮件系统",
        "port": 5000,
        "features": ["基础邮件服务器", "DNS系统", "Web界面", "邮件测试"],
        "tech_stack": ["Docker", "Flask", "Postfix", "Dovecot"],
        "status": "✅ 完成"
    },
    "29-1": {
        "name": "29-1真实邮件系统",
        "description": "多提供商真实邮件系统仿真",
        "port": 5001,
        "features": ["多邮件提供商", "真实DNS", "高级网络拓扑", "邮件路由"],
        "tech_stack": ["SEED-Emulator", "Docker", "Flask", "BIND9"],
        "status": "✅ 完成"
    },
    "30": {
        "name": "30 AI钓鱼系统",
        "description": "集成AI的智能钓鱼攻击系统",
        "port": 5002,
        "features": ["Gophish集成", "Ollama AI", "AI检测", "钓鱼模板"],
        "tech_stack": ["Gophish", "Ollama", "Python", "Flask"],
        "status": "✅ 完成"
    },
    "31": {
        "name": "31高级钓鱼系统",
        "description": "OpenAI集成的高级APT钓鱼系统",
        "port": 5003,
        "features": ["OpenAI GPT-4", "APT模拟", "规避技术", "威胁分析"],
        "tech_stack": ["OpenAI API", "Flask", "SEED-Emulator", "Python"],
        "status": "✅ 完成"
    }
}

@app.route('/')
def index():
    """主页面"""
    return render_template('system_overview.html',
                         projects=PROJECTS_INFO,
                         current_time=datetime.now())

@app.route('/test-tabs')
def test_tabs():
    """标签页测试页面"""
    return render_template('test_tabs.html')

@app.route('/test-bootstrap')
def test_bootstrap():
    """Bootstrap修复测试页面"""
    return render_template('test_bootstrap_fix.html')

@app.route('/api/system_status')
def api_system_status():
    """系统状态API"""
    try:
        # 检查各项目状态
        status_info = {}

        for project_id, project_info in PROJECTS_INFO.items():
            port = project_info['port']
            status_info[project_id] = check_service_status(port)

        # Docker状态
        docker_status = check_docker_status()

        # 网络状态
        network_status = check_network_status()

        return jsonify({
            'projects': status_info,
            'docker': docker_status,
            'network': network_status,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/start_project/<project_id>')
def api_start_project(project_id):
    """启动项目API"""
    try:
        if project_id not in PROJECTS_INFO:
            return jsonify({'success': False, 'error': '项目不存在'})

        # 执行启动命令
        if project_id == "29":
            cmd = "cd /home/parallels/seed-email-system/examples/.not_ready_examples && seed-29"
        elif project_id == "29-1":
            cmd = "cd /home/parallels/seed-email-system/examples/.not_ready_examples && seed-29-1"
        elif project_id == "30":
            cmd = "cd /home/parallels/seed-email-system/examples/.not_ready_examples && seed-30"
        elif project_id == "31":
            cmd = "cd /home/parallels/seed-email-system/examples/.not_ready_examples && seed-31"
        else:
            return jsonify({'success': False, 'error': '不支持的项目'})

        # 后台启动项目
        subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        return jsonify({'success': True, 'message': f'正在启动项目 {project_id}'})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/stop_all')
def api_stop_all():
    """停止所有项目"""
    try:
        cmd = "cd /home/parallels/seed-email-system/examples/.not_ready_examples && seed-stop"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

        return jsonify({
            'success': result.returncode == 0,
            'message': '正在停止所有项目'
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/cleanup')
def api_cleanup():
    """系统清理"""
    try:
        cmd = "cd /home/parallels/seed-email-system/examples/.not_ready_examples && ./force_cleanup.sh"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

        return jsonify({
            'success': result.returncode == 0,
            'message': '正在清理系统'
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/project_info/<project_id>')
def api_project_info(project_id):
    """获取项目详细信息"""
    try:
        if project_id not in PROJECTS_INFO:
            return jsonify({'error': '项目不存在'}), 404

        # 获取项目结构信息
        project_path = PROJECT_ROOT / project_id
        if not project_path.exists():
            project_path = PROJECT_ROOT / f"{project_id}-email-system"
        if not project_path.exists():
            project_path = PROJECT_ROOT / f"{project_id}-phishing-ai-system"
        if not project_path.exists():
            project_path = PROJECT_ROOT / f"{project_id}-advanced-phishing-system"

        file_structure = get_directory_structure(project_path) if project_path.exists() else []

        # 获取README内容
        readme_content = ""
        readme_path = project_path / "README.md"
        if readme_path.exists():
            with open(readme_path, 'r', encoding='utf-8') as f:
                readme_content = f.read()

        return jsonify({
            'info': PROJECTS_INFO[project_id],
            'structure': file_structure,
            'readme': readme_content,
            'path': str(project_path)
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/code_preview/<path:file_path>')
def api_code_preview(file_path):
    """代码预览API"""
    try:
        full_path = PROJECT_ROOT / file_path
        if not full_path.exists():
            return jsonify({'error': '文件不存在'}), 404

        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()

        return jsonify({
            'content': content,
            'path': str(full_path),
            'size': len(content),
            'lines': len(content.split('\n'))
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/run_test/<project_id>')
def api_run_test(project_id):
    """运行项目测试"""
    try:
        if project_id not in PROJECTS_INFO:
            return jsonify({'success': False, 'error': '项目不存在'})

        # 运行相应的测试脚本
        test_cmd = f"cd /home/parallels/seed-email-system/examples/.not_ready_examples && python3 comprehensive_test.py --project {project_id}"

        # 后台运行测试
        subprocess.Popen(test_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        return jsonify({'success': True, 'message': f'正在运行 {project_id} 项目测试'})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

def check_service_status(port):
    """检查服务状态"""
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('localhost', port))
        sock.close()
        return 'online' if result == 0 else 'offline'
    except:
        return 'unknown'

def check_docker_status():
    """检查Docker状态"""
    try:
        result = subprocess.run(['docker', 'ps'], capture_output=True, text=True)
        container_count = len(result.stdout.strip().split('\n')) - 1 if result.stdout.strip() else 0

        seed_containers = []
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if any(keyword in line.lower() for keyword in ['seed', 'mail', 'gophish', 'ollama']):
                    seed_containers.append(line.split()[-1] if line.split() else 'unknown')

        return {
            'running': result.returncode == 0,
            'containers': container_count,
            'seed_containers': seed_containers
        }
    except:
        return {'running': False, 'containers': 0, 'seed_containers': []}

def check_network_status():
    """检查网络状态"""
    try:
        # 检查关键端口
        ports = [2525, 2526, 2527, 5000, 5001, 5002, 5003, 8080, 8081]
        port_status = {}

        for port in ports:
            status = check_service_status(port)
            port_status[str(port)] = status

        return port_status
    except:
        return {}

def get_directory_structure(path):
    """获取目录结构"""
    if not path.exists():
        return []

    structure = []
    try:
        for item in path.rglob('*'):
            if item.is_file() and not any(part.startswith('.') for part in item.parts):
                rel_path = item.relative_to(path)
                structure.append({
                    'path': str(rel_path),
                    'type': 'file',
                    'size': item.stat().st_size,
                    'extension': item.suffix
                })
    except:
        pass

    return structure

if __name__ == '__main__':
    print("🚀 启动SEED邮件系统综合总览")
    print("=" * 50)
    print("🌐 访问地址: http://localhost:4257")
    print("📊 系统总览: 整合29/29-1/30/31项目")
    print("🎯 功能特点:")
    print("  • 实时项目状态监控")
    print("  • 一键项目启动/停止")
    print("  • 代码结构浏览")
    print("  • 技术文档查看")
    print("  • 自动化测试")
    print("=" * 50)

    app.run(host='0.0.0.0', port=4257, debug=True)
