#!/usr/bin/env python
"""
高级网络安全实验室 - APT攻击链仿真系统
基于MITRE ATT&CK框架的完整攻击链模拟
"""

import os
import json
import time
import random
import sqlite3
import threading
import subprocess
from datetime import datetime, timedelta
from flask import Flask, request, render_template_string, jsonify, session
import requests
import hashlib
import base64

class APTSimulator:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.attack_chain = []
        self.current_stage = 0
        self.compromised_assets = []
        self.stolen_data = []
        self.c2_sessions = []
        
        # MITRE ATT&CK 战术映射
        self.attack_tactics = {
            "reconnaissance": "侦察",
            "initial_access": "初始访问", 
            "execution": "执行",
            "persistence": "持久化",
            "privilege_escalation": "权限提升",
            "defense_evasion": "防御规避",
            "credential_access": "凭证访问",
            "discovery": "发现",
            "lateral_movement": "横向移动",
            "collection": "收集",
            "command_control": "命令控制",
            "exfiltration": "渗出"
        }
        
        self.setup_database()
        
    def setup_database(self):
        """初始化APT攻击链数据库"""
        conn = sqlite3.connect('apt_simulation.db')
        cursor = conn.cursor()
        
        # 攻击链表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS attack_chain (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                tactic TEXT NOT NULL,
                technique TEXT NOT NULL,
                description TEXT NOT NULL,
                target_asset TEXT,
                success INTEGER DEFAULT 0,
                impact_score INTEGER DEFAULT 0,
                detection_probability REAL DEFAULT 0.0
            )
        ''')
        
        # 资产表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS assets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asset_name TEXT NOT NULL,
                asset_type TEXT NOT NULL,
                ip_address TEXT,
                os_type TEXT,
                criticality TEXT,
                compromised INTEGER DEFAULT 0,
                compromise_time TEXT
            )
        ''')
        
        # 凭证表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS credentials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                password TEXT NOT NULL,
                domain TEXT,
                privilege_level TEXT,
                source_asset TEXT,
                discovery_time TEXT
            )
        ''')
        
        # 插入模拟资产数据
        assets_data = [
            ('DMZ-WEB-01', 'Web服务器', '192.168.1.100', 'Ubuntu 20.04', 'HIGH', 0, None),
            ('DMZ-MAIL-01', '邮件服务器', '192.168.1.101', 'CentOS 8', 'HIGH', 0, None),
            ('INT-DC-01', '域控制器', '10.0.1.10', 'Windows Server 2019', 'CRITICAL', 0, None),
            ('INT-FILE-01', '文件服务器', '10.0.1.20', 'Windows Server 2016', 'HIGH', 0, None),
            ('INT-DB-01', '数据库服务器', '10.0.1.30', 'Ubuntu 18.04', 'CRITICAL', 0, None),
            ('INT-WS-01', '工作站-财务', '10.0.2.100', 'Windows 10', 'MEDIUM', 0, None),
            ('INT-WS-02', '工作站-HR', '10.0.2.101', 'Windows 10', 'MEDIUM', 0, None),
            ('INT-WS-03', '工作站-IT', '10.0.2.102', 'Windows 10', 'HIGH', 0, None)
        ]
        
        cursor.executemany(
            'INSERT OR IGNORE INTO assets (asset_name, asset_type, ip_address, os_type, criticality, compromised, compromise_time) VALUES (?, ?, ?, ?, ?, ?, ?)',
            assets_data
        )
        
        conn.commit()
        conn.close()

app = Flask(__name__)
app.secret_key = 'apt_simulation_key_2025'
apt_sim = APTSimulator()

# APT攻击链仿真页面模板
APT_DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>APT攻击链仿真系统</title>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #0a0a0a; color: #00ff00; }
        .header { background: #1a1a1a; color: #00ff00; padding: 20px; margin: -20px -20px 20px -20px; border-bottom: 2px solid #00ff00; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }
        .panel { background: #1a1a1a; padding: 20px; border-radius: 10px; border: 1px solid #333; }
        .attack-stage { background: #2a1a1a; padding: 15px; margin: 10px 0; border-left: 4px solid #ff6b6b; border-radius: 5px; }
        .stage-completed { border-left-color: #51cf66; background: #1a2a1a; }
        .stage-current { border-left-color: #ffd43b; background: #2a2a1a; animation: pulse 2s infinite; }
        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.7; } 100% { opacity: 1; } }
        .asset-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; }
        .asset { background: #2a2a2a; padding: 15px; border-radius: 5px; border: 1px solid #444; text-align: center; }
        .asset-compromised { background: #3a1a1a; border-color: #ff6b6b; }
        .asset-critical { border-color: #ff8787; }
        .asset-high { border-color: #ffd43b; }
        .asset-medium { border-color: #69db7c; }
        .btn { background: #ff6b6b; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; margin: 5px; }
        .btn:hover { background: #ff5252; }
        .btn-success { background: #51cf66; }
        .btn-warning { background: #ffd43b; color: #000; }
        .log-entry { background: #2a2a2a; padding: 10px; margin: 5px 0; border-left: 3px solid #666; font-family: monospace; font-size: 12px; }
        .log-success { border-left-color: #51cf66; }
        .log-warning { border-left-color: #ffd43b; }
        .log-error { border-left-color: #ff6b6b; }
        .progress-bar { background: #333; height: 20px; border-radius: 10px; overflow: hidden; margin: 10px 0; }
        .progress-fill { background: linear-gradient(90deg, #ff6b6b, #ffd43b, #51cf66); height: 100%; transition: width 0.5s; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 10px; margin-bottom: 20px; }
        .stat-card { background: #2a2a2a; padding: 15px; border-radius: 5px; text-align: center; }
        .stat-value { font-size: 24px; font-weight: bold; margin-bottom: 5px; }
        .stat-label { font-size: 12px; opacity: 0.8; }
    </style>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
    <div class="header">
        <h1>🎯 APT攻击链仿真系统</h1>
        <p>基于MITRE ATT&CK框架的高级持续性威胁模拟</p>
    </div>
    
    <div class="stats">
        <div class="stat-card">
            <div class="stat-value" style="color: #ff6b6b;">{{ stats.compromised_assets }}</div>
            <div class="stat-label">被感染资产</div>
        </div>
        <div class="stat-card">
            <div class="stat-value" style="color: #ffd43b;">{{ stats.attack_stages }}</div>
            <div class="stat-label">攻击阶段</div>
        </div>
        <div class="stat-card">
            <div class="stat-value" style="color: #51cf66;">{{ stats.stolen_credentials }}</div>
            <div class="stat-label">窃取凭证</div>
        </div>
        <div class="stat-card">
            <div class="stat-value" style="color: #69db7c;">{{ stats.data_exfiltrated }}</div>
            <div class="stat-label">外泄数据(MB)</div>
        </div>
    </div>
    
    <div class="panel">
        <h3>🎮 攻击控制面板</h3>
        <button class="btn" onclick="startAttackChain()">🚀 启动APT攻击</button>
        <button class="btn btn-warning" onclick="nextStage()">⏭️ 下一阶段</button>
        <button class="btn btn-success" onclick="pauseAttack()">⏸️ 暂停攻击</button>
        <button class="btn" onclick="resetSimulation()">🔄 重置仿真</button>
        
        <div class="progress-bar">
            <div class="progress-fill" style="width: {{ progress }}%"></div>
        </div>
        <p>攻击进度: {{ progress }}% (阶段 {{ current_stage }}/12)</p>
    </div>
    
    <div class="grid">
        <div class="panel">
            <h3>🎯 MITRE ATT&CK 攻击链</h3>
            {% for i, stage in enumerate(attack_stages) %}
            <div class="attack-stage {{ 'stage-completed' if i < current_stage else 'stage-current' if i == current_stage else '' }}">
                <strong>{{ stage.tactic }}</strong> - {{ stage.technique }}
                <br><small>{{ stage.description }}</small>
                {% if i < current_stage %}
                <span style="color: #51cf66; float: right;">✅ 完成</span>
                {% elif i == current_stage %}
                <span style="color: #ffd43b; float: right;">🔄 进行中</span>
                {% endif %}
            </div>
            {% endfor %}
        </div>
        
        <div class="panel">
            <h3>🏢 网络资产态势</h3>
            <div class="asset-grid">
                {% for asset in assets %}
                <div class="asset {{ 'asset-compromised' if asset.compromised else '' }} asset-{{ asset.criticality.lower() }}">
                    <strong>{{ asset.asset_name }}</strong>
                    <br>{{ asset.asset_type }}
                    <br><small>{{ asset.ip_address }}</small>
                    <br><small>{{ asset.os_type }}</small>
                    {% if asset.compromised %}
                    <div style="color: #ff6b6b; margin-top: 5px;">🚨 已感染</div>
                    {% endif %}
                </div>
                {% endfor %}
            </div>
        </div>
    </div>
    
    <div class="panel">
        <h3>📋 实时攻击日志</h3>
        <div id="attack-logs" style="max-height: 300px; overflow-y: auto;">
            {% for log in recent_logs %}
            <div class="log-entry log-{{ log.type }}">
                <strong>{{ log.timestamp }}</strong> [{{ log.tactic }}] {{ log.description }}
                {% if log.target_asset %}
                <span style="color: #ffd43b;">目标: {{ log.target_asset }}</span>
                {% endif %}
            </div>
            {% endfor %}
        </div>
    </div>
    
    <script>
        let attackRunning = false;
        let currentStage = {{ current_stage }};
        
        async function startAttackChain() {
            if (attackRunning) return;
            attackRunning = true;
            
            try {
                const response = await fetch('/api/start_attack', { method: 'POST' });
                const result = await response.json();
                if (result.success) {
                    addLog('info', '攻击链已启动');
                    autoProgressAttack();
                }
            } catch (error) {
                addLog('error', '启动攻击失败: ' + error);
            }
        }
        
        async function nextStage() {
            try {
                const response = await fetch('/api/next_stage', { method: 'POST' });
                const result = await response.json();
                if (result.success) {
                    currentStage = result.stage;
                    addLog('success', '进入下一阶段: ' + result.tactic);
                    location.reload();
                }
            } catch (error) {
                addLog('error', '阶段推进失败: ' + error);
            }
        }
        
        async function pauseAttack() {
            attackRunning = false;
            addLog('warning', '攻击已暂停');
        }
        
        async function resetSimulation() {
            try {
                const response = await fetch('/api/reset', { method: 'POST' });
                const result = await response.json();
                if (result.success) {
                    addLog('info', '仿真已重置');
                    location.reload();
                }
            } catch (error) {
                addLog('error', '重置失败: ' + error);
            }
        }
        
        function autoProgressAttack() {
            if (!attackRunning || currentStage >= 12) return;
            
            setTimeout(() => {
                if (attackRunning) {
                    nextStage();
                    setTimeout(() => autoProgressAttack(), 3000);
                }
            }, 2000 + Math.random() * 3000);
        }
        
        function addLog(type, message) {
            const logsContainer = document.getElementById('attack-logs');
            const logEntry = document.createElement('div');
            logEntry.className = `log-entry log-${type}`;
            logEntry.innerHTML = `<strong>${new Date().toLocaleTimeString()}</strong> ${message}`;
            logsContainer.insertBefore(logEntry, logsContainer.firstChild);
            
            // 限制日志数量
            while (logsContainer.children.length > 50) {
                logsContainer.removeChild(logsContainer.lastChild);
            }
        }
        
        // 定时刷新数据
        setInterval(() => {
            if (!attackRunning) return;
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    // 更新统计数据
                    document.querySelectorAll('.stat-value').forEach((elem, index) => {
                        const values = [data.compromised_assets, data.attack_stages, data.stolen_credentials, data.data_exfiltrated];
                        if (values[index] !== undefined) {
                            elem.textContent = values[index];
                        }
                    });
                });
        }, 5000);
    </script>
</body>
</html>
"""

@app.route('/')
def apt_dashboard():
    """APT攻击链仿真主界面"""
    conn = sqlite3.connect('apt_simulation.db')
    cursor = conn.cursor()
    
    # 获取攻击阶段数据
    attack_stages = [
        {"tactic": "侦察", "technique": "T1589", "description": "收集目标组织公开信息"},
        {"tactic": "初始访问", "technique": "T1566", "description": "钓鱼邮件投递恶意附件"},
        {"tactic": "执行", "technique": "T1059", "description": "PowerShell恶意脚本执行"},
        {"tactic": "持久化", "technique": "T1053", "description": "创建计划任务维持访问"},
        {"tactic": "权限提升", "technique": "T1055", "description": "进程注入获取高权限"},
        {"tactic": "防御规避", "technique": "T1562", "description": "禁用安全工具和日志"},
        {"tactic": "凭证访问", "technique": "T1003", "description": "提取内存中的密码哈希"},
        {"tactic": "发现", "technique": "T1083", "description": "文件和目录发现"},
        {"tactic": "横向移动", "technique": "T1021", "description": "远程桌面协议横向移动"},
        {"tactic": "收集", "technique": "T1005", "description": "收集本地系统敏感数据"},
        {"tactic": "命令控制", "technique": "T1071", "description": "HTTPS隧道C2通信"},
        {"tactic": "渗出", "technique": "T1041", "description": "通过C2通道外泄数据"}
    ]
    
    # 获取资产状态
    cursor.execute('SELECT * FROM assets')
    assets = cursor.fetchall()
    asset_list = []
    for asset in assets:
        asset_list.append({
            'asset_name': asset[1],
            'asset_type': asset[2], 
            'ip_address': asset[3],
            'os_type': asset[4],
            'criticality': asset[5],
            'compromised': asset[6]
        })
    
    # 获取攻击日志
    cursor.execute('SELECT * FROM attack_chain ORDER BY id DESC LIMIT 20')
    logs = cursor.fetchall()
    recent_logs = []
    for log in logs:
        recent_logs.append({
            'timestamp': log[1],
            'tactic': log[2],
            'description': log[4],
            'target_asset': log[5],
            'type': 'success' if log[6] else 'warning'
        })
    
    # 计算统计数据
    cursor.execute('SELECT COUNT(*) FROM assets WHERE compromised = 1')
    compromised_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM attack_chain')
    stages_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM credentials')
    creds_count = cursor.fetchone()[0]
    
    stats = {
        'compromised_assets': compromised_count,
        'attack_stages': min(stages_count, 12),
        'stolen_credentials': creds_count,
        'data_exfiltrated': random.randint(100, 500)
    }
    
    current_stage = session.get('current_stage', 0)
    progress = (current_stage / 12) * 100
    
    conn.close()
    
    return render_template_string(APT_DASHBOARD_TEMPLATE,
                                 attack_stages=attack_stages,
                                 assets=asset_list,
                                 recent_logs=recent_logs,
                                 stats=stats,
                                 current_stage=current_stage,
                                 progress=progress,
                                 enumerate=enumerate)

@app.route('/api/start_attack', methods=['POST'])
def start_attack():
    """启动APT攻击链"""
    session['current_stage'] = 0
    session['attack_started'] = True
    
    # 记录攻击开始
    log_attack_event("reconnaissance", "T1589", "APT攻击链启动 - 开始收集目标信息", None, True, 10)
    
    return jsonify({"success": True, "message": "APT攻击链已启动"})

@app.route('/api/next_stage', methods=['POST'])
def next_stage():
    """推进到下一个攻击阶段"""
    current_stage = session.get('current_stage', 0)
    
    if current_stage >= 12:
        return jsonify({"success": False, "message": "攻击链已完成"})
    
    # 攻击阶段定义
    stages = [
        ("reconnaissance", "T1589", "主动扫描目标网络基础设施", "DMZ-WEB-01"),
        ("initial_access", "T1566", "钓鱼邮件成功投递到目标邮箱", "DMZ-MAIL-01"),
        ("execution", "T1059", "恶意宏代码在用户工作站执行", "INT-WS-01"),
        ("persistence", "T1053", "在工作站创建持久化后门", "INT-WS-01"),
        ("privilege_escalation", "T1055", "利用本地提权漏洞获取管理员权限", "INT-WS-01"),
        ("defense_evasion", "T1562", "禁用Windows Defender和日志记录", "INT-WS-01"),
        ("credential_access", "T1003", "从LSASS进程提取密码哈希", "INT-WS-01"),
        ("discovery", "T1083", "发现网络共享和敏感文件位置", "INT-FILE-01"),
        ("lateral_movement", "T1021", "使用窃取凭证登录域控制器", "INT-DC-01"),
        ("collection", "T1005", "收集财务数据和客户信息", "INT-DB-01"),
        ("command_control", "T1071", "建立加密C2隧道", None),
        ("exfiltration", "T1041", "外泄50GB敏感商业数据", None)
    ]
    
    if current_stage < len(stages):
        stage = stages[current_stage]
        tactic, technique, description, target = stage
        
        # 模拟攻击成功概率
        success = random.random() > 0.1  # 90%成功率
        impact = random.randint(20, 80)
        
        # 记录攻击事件
        log_attack_event(tactic, technique, description, target, success, impact)
        
        # 更新资产状态
        if target and success:
            compromise_asset(target)
            
        # 模拟凭证窃取
        if tactic == "credential_access" and success:
            steal_credentials(target)
        
        current_stage += 1
        session['current_stage'] = current_stage
        
        return jsonify({
            "success": True, 
            "stage": current_stage,
            "tactic": tactic,
            "description": description
        })
    
    return jsonify({"success": False, "message": "攻击链已完成"})

@app.route('/api/reset', methods=['POST'])
def reset_simulation():
    """重置仿真环境"""
    conn = sqlite3.connect('apt_simulation.db')
    cursor = conn.cursor()
    
    # 清空攻击链记录
    cursor.execute('DELETE FROM attack_chain')
    
    # 重置资产状态
    cursor.execute('UPDATE assets SET compromised = 0, compromise_time = NULL')
    
    # 清空凭证
    cursor.execute('DELETE FROM credentials')
    
    conn.commit()
    conn.close()
    
    # 重置会话
    session.clear()
    
    return jsonify({"success": True, "message": "仿真环境已重置"})

@app.route('/api/status')
def get_status():
    """获取当前攻击状态"""
    conn = sqlite3.connect('apt_simulation.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM assets WHERE compromised = 1')
    compromised_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM attack_chain')
    stages_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM credentials')
    creds_count = cursor.fetchone()[0]
    
    conn.close()
    
    return jsonify({
        "compromised_assets": compromised_count,
        "attack_stages": min(stages_count, 12),
        "stolen_credentials": creds_count,
        "data_exfiltrated": random.randint(100, 500)
    })

def log_attack_event(tactic, technique, description, target_asset, success, impact_score):
    """记录攻击事件"""
    conn = sqlite3.connect('apt_simulation.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO attack_chain (timestamp, tactic, technique, description, target_asset, success, impact_score, detection_probability)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        datetime.now().isoformat(),
        tactic,
        technique, 
        description,
        target_asset,
        1 if success else 0,
        impact_score,
        random.random()
    ))
    
    conn.commit()
    conn.close()

def compromise_asset(asset_name):
    """标记资产为已感染"""
    conn = sqlite3.connect('apt_simulation.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE assets SET compromised = 1, compromise_time = ? WHERE asset_name = ?
    ''', (datetime.now().isoformat(), asset_name))
    
    conn.commit()
    conn.close()

def steal_credentials(source_asset):
    """模拟凭证窃取"""
    fake_credentials = [
        ("administrator", "P@ssw0rd123", "CORP", "admin", source_asset),
        ("john.smith", "Summer2024!", "CORP", "user", source_asset),
        ("service_account", "Svc_P@ss2024", "CORP", "service", source_asset),
        ("backup_admin", "Backup#2024", "CORP", "admin", source_asset)
    ]
    
    conn = sqlite3.connect('apt_simulation.db')
    cursor = conn.cursor()
    
    # 随机窃取1-3个凭证
    stolen = random.sample(fake_credentials, random.randint(1, 3))
    
    for cred in stolen:
        cursor.execute('''
            INSERT INTO credentials (username, password, domain, privilege_level, source_asset, discovery_time)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (*cred, datetime.now().isoformat()))
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    print("🚀 启动APT攻击链仿真系统...")
    print("访问 http://localhost:5004 开始APT攻击仿真")
    print("")
    print("🎯 支持的攻击技术:")
    print("  - MITRE ATT&CK框架完整覆盖")
    print("  - 12阶段攻击链模拟")
    print("  - 实时资产感染状态")
    print("  - 凭证窃取和横向移动")
    print("  - 数据外泄损失评估")
    
    app.run(host='0.0.0.0', port=5004, debug=True)
