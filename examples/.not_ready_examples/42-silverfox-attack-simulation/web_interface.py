#!/usr/bin/env python3
"""
银狐木马攻击仿真复现实验 - Web管理界面
端口: 4257
功能: 统一管理攻击链仿真、监控状态、展示结果
"""

import os
import sys
import json
import yaml
import time
import subprocess
import threading
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file
from werkzeug.serving import make_server
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask应用配置
app = Flask(__name__)
app.secret_key = 'silverfox_simulation_2025'

# 全局变量
SIMULATION_STATUS = {
    'running': False,
    'current_stage': None,
    'stages_completed': 0,
    'total_stages': 6,
    'start_time': None,
    'errors': [],
    'logs': []
}

SIMULATION_RESULTS = {
    'attack_success_rate': 0,
    'targets_compromised': 0,
    'data_exfiltrated': 0,
    'detection_evasion_rate': 0
}

class SimulationManager:
    """仿真管理器"""
    
    def __init__(self):
        self.config_path = os.path.join(os.path.dirname(__file__), 'config')
        self.results_path = os.path.join(os.path.dirname(__file__), 'results')
        self.attack_config = self.load_attack_config()
        self.simulation_thread = None
        
        # 确保结果目录存在
        os.makedirs(self.results_path, exist_ok=True)
        os.makedirs(os.path.join(self.results_path, 'logs'), exist_ok=True)
        os.makedirs(os.path.join(self.results_path, 'reports'), exist_ok=True)
        
    def load_attack_config(self):
        """加载攻击链配置"""
        config_file = os.path.join(self.config_path, 'attack_chain_config.yaml')
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"无法加载攻击链配置: {e}")
            return None
    
    def get_simulation_status(self):
        """获取仿真状态"""
        return SIMULATION_STATUS.copy()
    
    def get_simulation_results(self):
        """获取仿真结果"""
        return SIMULATION_RESULTS.copy()
    
    def start_simulation(self, test_mode=False):
        """启动攻击链仿真"""
        if SIMULATION_STATUS['running']:
            return False, "仿真已在运行中"
        
        # 重置状态
        SIMULATION_STATUS.update({
            'running': True,
            'current_stage': None,
            'stages_completed': 0,
            'start_time': datetime.now().isoformat(),
            'errors': [],
            'logs': []
        })
        
        # 启动仿真线程
        if test_mode:
            self.simulation_thread = threading.Thread(target=self._run_test_simulation)
        else:
            self.simulation_thread = threading.Thread(target=self._run_full_simulation)
        
        self.simulation_thread.daemon = True
        self.simulation_thread.start()
        
        return True, "仿真已启动"
    
    def stop_simulation(self):
        """停止攻击链仿真"""
        SIMULATION_STATUS['running'] = False
        return True, "仿真已停止"
    
    def _run_test_simulation(self):
        """运行测试仿真 (环境外测试)"""
        logger.info("开始运行测试仿真")
        
        # 模拟测试阶段
        test_stages = [
            "环境检查",
            "配置验证", 
            "网络连通性测试",
            "Web界面测试",
            "集成工具测试"
        ]
        
        for i, stage in enumerate(test_stages):
            if not SIMULATION_STATUS['running']:
                break
                
            SIMULATION_STATUS['current_stage'] = stage
            SIMULATION_STATUS['logs'].append({
                'timestamp': datetime.now().isoformat(),
                'level': 'INFO',
                'message': f"正在执行: {stage}"
            })
            
            # 模拟执行时间
            time.sleep(2)
            
            SIMULATION_STATUS['stages_completed'] = i + 1
            SIMULATION_STATUS['logs'].append({
                'timestamp': datetime.now().isoformat(),
                'level': 'SUCCESS',
                'message': f"{stage} - 完成"
            })
        
        # 完成测试
        SIMULATION_STATUS['running'] = False
        SIMULATION_STATUS['current_stage'] = "测试完成"
        logger.info("测试仿真完成")
    
    def _run_full_simulation(self):
        """运行完整攻击链仿真"""
        logger.info("开始运行完整攻击链仿真")
        
        if not self.attack_config:
            SIMULATION_STATUS['errors'].append("无法加载攻击链配置")
            SIMULATION_STATUS['running'] = False
            return
        
        stages = self.attack_config.get('stages', [])
        SIMULATION_STATUS['total_stages'] = len(stages)
        
        for i, stage in enumerate(stages):
            if not SIMULATION_STATUS['running']:
                break
            
            stage_name = stage.get('display_name', stage.get('name'))
            SIMULATION_STATUS['current_stage'] = stage_name
            
            self._log_message('INFO', f"开始执行阶段: {stage_name}")
            
            # 执行阶段中的所有动作
            actions = stage.get('actions', [])
            for action in actions:
                if not SIMULATION_STATUS['running']:
                    break
                
                action_desc = action.get('description')
                self._log_message('INFO', f"  执行动作: {action_desc}")
                
                # 执行具体命令 (这里先用模拟)
                success = self._execute_action(action)
                
                if success:
                    self._log_message('SUCCESS', f"  {action_desc} - 成功")
                else:
                    self._log_message('ERROR', f"  {action_desc} - 失败")
                    SIMULATION_STATUS['errors'].append(f"{stage_name}: {action_desc} 执行失败")
            
            SIMULATION_STATUS['stages_completed'] = i + 1
            self._log_message('SUCCESS', f"阶段完成: {stage_name}")
            
            # 更新结果统计
            self._update_results(stage)
        
        # 完成仿真
        SIMULATION_STATUS['running'] = False
        SIMULATION_STATUS['current_stage'] = "仿真完成"
        self._log_message('INFO', "攻击链仿真完成")
    
    def _execute_action(self, action):
        """执行具体动作 (目前为模拟执行)"""
        # 模拟执行时间
        time.sleep(1)
        
        # 这里应该实际执行command中的命令
        # 目前返回模拟结果
        import random
        return random.choice([True, True, True, False])  # 75%成功率
    
    def _update_results(self, stage):
        """更新仿真结果统计"""
        stage_name = stage.get('name')
        
        # 模拟结果更新
        if stage_name == 'initial_access':
            SIMULATION_RESULTS['attack_success_rate'] += 20
        elif stage_name == 'lateral_movement':
            SIMULATION_RESULTS['targets_compromised'] += 2
        elif stage_name == 'collection':
            SIMULATION_RESULTS['data_exfiltrated'] += 1
        
        # 限制最大值
        SIMULATION_RESULTS['attack_success_rate'] = min(SIMULATION_RESULTS['attack_success_rate'], 100)
        SIMULATION_RESULTS['targets_compromised'] = min(SIMULATION_RESULTS['targets_compromised'], 5)
        SIMULATION_RESULTS['detection_evasion_rate'] = min(SIMULATION_RESULTS['detection_evasion_rate'] + 15, 100)
    
    def _log_message(self, level, message):
        """记录日志消息"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'level': level,
            'message': message
        }
        SIMULATION_STATUS['logs'].append(log_entry)
        
        # 保持日志数量在合理范围内
        if len(SIMULATION_STATUS['logs']) > 100:
            SIMULATION_STATUS['logs'] = SIMULATION_STATUS['logs'][-100:]
    
    def generate_report(self):
        """生成仿真报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = os.path.join(self.results_path, 'reports', f'simulation_report_{timestamp}.json')
        
        report_data = {
            'timestamp': timestamp,
            'simulation_status': SIMULATION_STATUS.copy(),
            'simulation_results': SIMULATION_RESULTS.copy(),
            'configuration': self.attack_config
        }
        
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)
            return report_file
        except Exception as e:
            logger.error(f"生成报告失败: {e}")
            return None

# 创建仿真管理器实例
simulation_manager = SimulationManager()

@app.route('/')
def index():
    """主页"""
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    """仿真控制台"""
    status = simulation_manager.get_simulation_status()
    results = simulation_manager.get_simulation_results()
    return render_template('dashboard.html', status=status, results=results)

@app.route('/api/status')
def api_status():
    """获取仿真状态API"""
    status = simulation_manager.get_simulation_status()
    results = simulation_manager.get_simulation_results()
    return jsonify({
        'status': status,
        'results': results
    })

@app.route('/api/start_simulation', methods=['POST'])
def api_start_simulation():
    """启动仿真API"""
    test_mode = request.json.get('test_mode', False)
    success, message = simulation_manager.start_simulation(test_mode)
    return jsonify({
        'success': success,
        'message': message
    })

@app.route('/api/stop_simulation', methods=['POST'])
def api_stop_simulation():
    """停止仿真API"""
    success, message = simulation_manager.stop_simulation()
    return jsonify({
        'success': success,
        'message': message
    })

@app.route('/api/generate_report', methods=['POST'])
def api_generate_report():
    """生成报告API"""
    report_file = simulation_manager.generate_report()
    if report_file:
        return jsonify({
            'success': True,
            'report_file': os.path.basename(report_file)
        })
    else:
        return jsonify({
            'success': False,
            'message': '报告生成失败'
        })

@app.route('/logs')
def logs():
    """日志查看页面"""
    return render_template('logs.html')

@app.route('/api/logs')
def api_logs():
    """获取日志API"""
    return jsonify(SIMULATION_STATUS['logs'])

@app.route('/results')
def results():
    """结果展示页面"""
    results = simulation_manager.get_simulation_results()
    return render_template('results.html', results=results)

@app.route('/config')
def config():
    """配置管理页面"""
    config_data = simulation_manager.attack_config
    return render_template('config.html', config=config_data)

@app.route('/overview')
def overview():
    """系统总览页面"""
    # 检查相关服务状态
    services_status = check_services_status()
    return render_template('overview.html', services=services_status)

def check_services_status():
    """检查相关服务状态"""
    services = {
        'seed_email_29': {'name': '基础邮件系统(29)', 'port': 5000, 'status': 'unknown'},
        'seed_email_29_1': {'name': '真实网络邮件(29-1)', 'port': 5001, 'status': 'unknown'},
        'seed_email_30': {'name': 'AI钓鱼系统(30)', 'port': 5002, 'status': 'unknown'},
        'gophish': {'name': 'Gophish钓鱼平台', 'port': 3333, 'status': 'unknown'},
        'system_overview': {'name': '系统总览面板', 'port': 4257, 'status': 'running'}  # 当前服务
    }
    
    # 简单的端口检查
    import socket
    for service_key, service in services.items():
        if service_key == 'system_overview':
            continue
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', service['port']))
            sock.close()
            service['status'] = 'running' if result == 0 else 'stopped'
        except:
            service['status'] = 'error'
    
    return services

if __name__ == '__main__':
    print("🦊 银狐木马攻击仟真复现实验")
    print("=" * 50)
    print(f"访问地址: http://localhost:4257")
    print(f"仿真控制台: http://localhost:4257/dashboard")
    print(f"系统总览: http://localhost:4257/overview")
    print(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    # 启动Web服务器
    try:
        app.run(host='0.0.0.0', port=4257, debug=False, threaded=True)
    except KeyboardInterrupt:
        print("\n程序已停止")
    except Exception as e:
        print(f"启动失败: {e}")