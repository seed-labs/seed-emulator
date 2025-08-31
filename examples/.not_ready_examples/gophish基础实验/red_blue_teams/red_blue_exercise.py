#!/usr/bin/env python
"""
红蓝对抗演练平台
实时攻防对抗演练系统
基于MITRE ATT&CK框架的红蓝军对战
"""

import os
import json
import time
import random
import sqlite3
import threading
from datetime import datetime, timedelta
from flask import Flask, request, render_template_string, jsonify, session, redirect
import hashlib
import uuid

class RedBlueExercise:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.exercises = {}
        self.active_sessions = {}
        self.setup_database()
        
    def setup_database(self):
        """初始化红蓝对抗数据库"""
        conn = sqlite3.connect('red_blue_exercise.db')
        cursor = conn.cursor()
        
        # 演练会话表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS exercise_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                red_team_size INTEGER DEFAULT 1,
                blue_team_size INTEGER DEFAULT 1,
                start_time TEXT,
                end_time TEXT,
                status TEXT DEFAULT 'preparing',
                scenario TEXT,
                target_network TEXT,
                success_criteria TEXT
            )
        ''')
        
        # 团队成员表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS team_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                team_type TEXT NOT NULL,
                role TEXT,
                join_time TEXT NOT NULL,
                score INTEGER DEFAULT 0,
                achievements TEXT,
                FOREIGN KEY (session_id) REFERENCES exercise_sessions (session_id)
            )
        ''')
        
        # 攻击行动表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS attack_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                team_type TEXT NOT NULL,
                user_id TEXT NOT NULL,
                action_type TEXT NOT NULL,
                target TEXT,
                technique TEXT,
                description TEXT,
                timestamp TEXT NOT NULL,
                success INTEGER DEFAULT 0,
                points INTEGER DEFAULT 0,
                evidence TEXT,
                FOREIGN KEY (session_id) REFERENCES exercise_sessions (session_id)
            )
        ''')
        
        # 防御行动表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS defense_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                action_type TEXT NOT NULL,
                target TEXT,
                detection_rule TEXT,
                description TEXT,
                timestamp TEXT NOT NULL,
                effectiveness INTEGER DEFAULT 0,
                points INTEGER DEFAULT 0,
                false_positive INTEGER DEFAULT 0,
                FOREIGN KEY (session_id) REFERENCES exercise_sessions (session_id)
            )
        ''')
        
        # 网络资产表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS network_assets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                asset_name TEXT NOT NULL,
                asset_type TEXT NOT NULL,
                ip_address TEXT,
                os_type TEXT,
                services TEXT,
                vulnerabilities TEXT,
                compromised INTEGER DEFAULT 0,
                compromise_time TEXT,
                owner_team TEXT,
                FOREIGN KEY (session_id) REFERENCES exercise_sessions (session_id)
            )
        ''')
        
        conn.commit()
        conn.close()

app = Flask(__name__)
app.secret_key = 'red_blue_exercise_2025'
exercise_manager = RedBlueExercise()

# 红蓝对抗主页面模板
RED_BLUE_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>红蓝对抗演练平台</title>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #0d1117; color: #c9d1d9; }
        .header { background: linear-gradient(135deg, #dc2626, #2563eb); color: white; padding: 20px; margin: -20px -20px 20px -20px; text-align: center; }
        .container { max-width: 1400px; margin: 0 auto; }
        .team-selector { display: flex; justify-content: center; gap: 20px; margin: 20px 0; }
        .team-button { padding: 15px 30px; border: none; border-radius: 10px; font-size: 18px; font-weight: bold; cursor: pointer; transition: all 0.3s; }
        .red-team { background: #dc2626; color: white; }
        .red-team:hover { background: #b91c1c; transform: scale(1.05); }
        .blue-team { background: #2563eb; color: white; }
        .blue-team:hover { background: #1d4ed8; transform: scale(1.05); }
        .spectator { background: #6b7280; color: white; }
        .spectator:hover { background: #4b5563; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin: 20px 0; }
        .full-width { grid-column: 1 / -1; }
        .panel { background: #161b22; padding: 20px; border-radius: 10px; border: 1px solid #30363d; }
        .red-panel { border-left: 4px solid #dc2626; }
        .blue-panel { border-left: 4px solid #2563eb; }
        .score-board { display: grid; grid-template-columns: 1fr auto 1fr; gap: 20px; align-items: center; text-align: center; }
        .score-red { background: #dc2626; color: white; padding: 20px; border-radius: 10px; }
        .score-blue { background: #2563eb; color: white; padding: 20px; border-radius: 10px; }
        .score-vs { font-size: 48px; font-weight: bold; color: #f0f6ff; }
        .action-log { max-height: 400px; overflow-y: auto; background: #0d1117; padding: 15px; border-radius: 5px; font-family: monospace; font-size: 12px; }
        .log-red { border-left: 3px solid #dc2626; padding-left: 10px; margin: 5px 0; }
        .log-blue { border-left: 3px solid #2563eb; padding-left: 10px; margin: 5px 0; }
        .log-system { border-left: 3px solid #6b7280; padding-left: 10px; margin: 5px 0; }
        .network-map { background: #0d1117; padding: 20px; border-radius: 10px; height: 300px; position: relative; overflow: hidden; }
        .asset-node { position: absolute; width: 80px; height: 60px; background: #30363d; border: 2px solid #58a6ff; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 10px; text-align: center; cursor: pointer; }
        .asset-compromised { border-color: #da3633; background: #2d1b18; }
        .asset-defended { border-color: #2ea043; background: #1b2e1f; }
        .btn { background: #238636; color: white; padding: 8px 16px; border: none; border-radius: 5px; cursor: pointer; margin: 3px; font-size: 12px; }
        .btn-red { background: #da3633; }
        .btn-blue { background: #0969da; }
        .btn:hover { opacity: 0.8; }
        .technique-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; }
        .technique-card { background: #21262d; padding: 15px; border-radius: 8px; border: 1px solid #30363d; cursor: pointer; transition: all 0.3s; }
        .technique-card:hover { border-color: #58a6ff; transform: translateY(-2px); }
        .technique-available { border-left: 4px solid #2ea043; }
        .technique-used { border-left: 4px solid #da3633; opacity: 0.6; }
        .timer { font-size: 48px; font-weight: bold; text-align: center; margin: 20px 0; }
        .timer-running { color: #2ea043; }
        .timer-warning { color: #fb8500; }
        .timer-critical { color: #da3633; }
        .achievement { background: #ffd60a; color: #000; padding: 5px 10px; border-radius: 15px; font-size: 11px; margin: 2px; display: inline-block; }
    </style>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⚔️ 红蓝对抗演练平台</h1>
            <p>实时攻防对抗 • 技能提升 • 战术评估</p>
        </div>
        
        {% if not session.get('user_team') %}
        <div class="panel">
            <h2 style="text-align: center;">选择您的阵营</h2>
            <div class="team-selector">
                <button class="team-button red-team" onclick="joinTeam('red')">
                    🔴 红队 (攻击方)<br><small>渗透测试 • 漏洞利用 • 社会工程学</small>
                </button>
                <button class="team-button blue-team" onclick="joinTeam('blue')">
                    🔵 蓝队 (防御方)<br><small>威胁检测 • 事件响应 • 安全加固</small>
                </button>
                <button class="team-button spectator" onclick="joinTeam('spectator')">
                    👁️ 观察者<br><small>观看对战 • 学习技巧</small>
                </button>
            </div>
        </div>
        {% else %}
        
        <div class="score-board">
            <div class="score-red">
                <h2>🔴 红队</h2>
                <div style="font-size: 36px;">{{ scores.red_score }}</div>
                <div>{{ scores.red_members }} 名成员</div>
            </div>
            <div class="score-vs">VS</div>
            <div class="score-blue">
                <h2>🔵 蓝队</h2>
                <div style="font-size: 36px;">{{ scores.blue_score }}</div>
                <div>{{ scores.blue_members }} 名成员</div>
            </div>
        </div>
        
        <div class="timer timer-{{ timer_status }}">
            ⏱️ {{ time_remaining }}
        </div>
        
        <div class="grid">
            {% if session.get('user_team') == 'red' %}
            <div class="panel red-panel">
                <h3>🔴 红队行动面板</h3>
                <div class="technique-grid">
                    {% for technique in red_techniques %}
                    <div class="technique-card technique-{{ 'used' if technique.used else 'available' }}" 
                         onclick="executeAttack('{{ technique.id }}')">
                        <strong>{{ technique.name }}</strong>
                        <br><small>{{ technique.description }}</small>
                        <br><span style="color: #ffd60a;">{{ technique.points }}分</span>
                    </div>
                    {% endfor %}
                </div>
                
                <h4>🎯 当前目标</h4>
                <div>
                    <button class="btn btn-red" onclick="scanNetwork()">🔍 网络扫描</button>
                    <button class="btn btn-red" onclick="exploitVuln()">💥 漏洞利用</button>
                    <button class="btn btn-red" onclick="lateralMove()">➡️ 横向移动</button>
                    <button class="btn btn-red" onclick="exfilData()">📤 数据外泄</button>
                </div>
            </div>
            {% elif session.get('user_team') == 'blue' %}
            <div class="panel blue-panel">
                <h3>🔵 蓝队防御面板</h3>
                <div class="technique-grid">
                    {% for technique in blue_techniques %}
                    <div class="technique-card technique-{{ 'used' if technique.used else 'available' }}" 
                         onclick="executeDefense('{{ technique.id }}')">
                        <strong>{{ technique.name }}</strong>
                        <br><small>{{ technique.description }}</small>
                        <br><span style="color: #2ea043;">{{ technique.points }}分</span>
                    </div>
                    {% endfor %}
                </div>
                
                <h4>🛡️ 防御行动</h4>
                <div>
                    <button class="btn btn-blue" onclick="deployHoneypot()">🍯 部署蜜罐</button>
                    <button class="btn btn-blue" onclick="blockIP()">🚫 IP封禁</button>
                    <button class="btn btn-blue" onclick="updateRules()">📋 更新规则</button>
                    <button class="btn btn-blue" onclick="incidentResponse()">🚨 事件响应</button>
                </div>
            </div>
            {% endif %}
            
            <div class="panel">
                <h3>🗺️ 网络态势图</h3>
                <div class="network-map" id="networkMap">
                    {% for asset in network_assets %}
                    <div class="asset-node asset-{{ asset.status }}" 
                         style="left: {{ asset.x }}px; top: {{ asset.y }}px;"
                         onclick="selectAsset('{{ asset.id }}')">
                        {{ asset.name }}<br>{{ asset.ip }}
                    </div>
                    {% endfor %}
                </div>
            </div>
        </div>
        
        <div class="grid">
            <div class="panel">
                <h3>📋 实时行动日志</h3>
                <div class="action-log" id="actionLog">
                    {% for log in action_logs %}
                    <div class="log-{{ log.team }}">
                        <strong>{{ log.timestamp }}</strong> [{{ log.team.upper() }}] {{ log.action }}
                        {% if log.points > 0 %}
                        <span style="color: #ffd60a;">+{{ log.points }}分</span>
                        {% endif %}
                    </div>
                    {% endfor %}
                </div>
            </div>
            
            <div class="panel">
                <h3>🏆 成就系统</h3>
                <div id="achievements">
                    {% for achievement in user_achievements %}
                    <span class="achievement">{{ achievement }}</span>
                    {% endfor %}
                </div>
                
                <h4>📊 个人统计</h4>
                <div>
                    <p>总分: <strong>{{ user_stats.total_score }}</strong></p>
                    <p>成功行动: <strong>{{ user_stats.successful_actions }}</strong></p>
                    <p>失败行动: <strong>{{ user_stats.failed_actions }}</strong></p>
                    <p>排名: <strong>#{{ user_stats.rank }}</strong></p>
                </div>
            </div>
        </div>
        
        {% endif %}
    </div>
    
    <script>
        function joinTeam(team) {
            fetch('/api/join_team', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ team: team })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    location.reload();
                } else {
                    alert('加入团队失败: ' + data.error);
                }
            });
        }
        
        function executeAttack(techniqueId) {
            fetch('/api/execute_attack', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ technique_id: techniqueId })
            })
            .then(response => response.json())
            .then(data => {
                addLogEntry('red', data.message, data.points || 0);
                updateScore();
            });
        }
        
        function executeDefense(techniqueId) {
            fetch('/api/execute_defense', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ technique_id: techniqueId })
            })
            .then(response => response.json())
            .then(data => {
                addLogEntry('blue', data.message, data.points || 0);
                updateScore();
            });
        }
        
        function scanNetwork() {
            executeAttack('recon');
        }
        
        function exploitVuln() {
            executeAttack('exploit');
        }
        
        function lateralMove() {
            executeAttack('lateral');
        }
        
        function exfilData() {
            executeAttack('exfiltration');
        }
        
        function deployHoneypot() {
            executeDefense('honeypot');
        }
        
        function blockIP() {
            executeDefense('ip_block');
        }
        
        function updateRules() {
            executeDefense('rule_update');
        }
        
        function incidentResponse() {
            executeDefense('incident');
        }
        
        function selectAsset(assetId) {
            console.log('选择资产:', assetId);
            // 显示资产详情
        }
        
        function addLogEntry(team, message, points) {
            const logContainer = document.getElementById('actionLog');
            const logEntry = document.createElement('div');
            logEntry.className = `log-${team}`;
            logEntry.innerHTML = `<strong>${new Date().toLocaleTimeString()}</strong> [${team.toUpperCase()}] ${message}`;
            if (points > 0) {
                logEntry.innerHTML += ` <span style="color: #ffd60a;">+${points}分</span>`;
            }
            logContainer.insertBefore(logEntry, logContainer.firstChild);
            
            // 限制日志数量
            while (logContainer.children.length > 50) {
                logContainer.removeChild(logContainer.lastChild);
            }
        }
        
        function updateScore() {
            fetch('/api/get_scores')
                .then(response => response.json())
                .then(data => {
                    // 更新分数显示
                    location.reload(); // 简单重载，实际项目中可以动态更新
                });
        }
        
        // 定时更新数据
        setInterval(() => {
            fetch('/api/get_status')
                .then(response => response.json())
                .then(data => {
                    // 更新状态信息
                    if (data.new_actions) {
                        location.reload();
                    }
                });
        }, 5000);
        
        // 模拟网络连线动画
        function animateNetworkConnections() {
            // 这里可以添加网络连接的动画效果
        }
        
        setInterval(animateNetworkConnections, 2000);
    </script>
</body>
</html>
"""

@app.route('/')
def exercise_dashboard():
    """红蓝对抗演练主界面"""
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
    
    if 'session_id' not in session:
        session['session_id'] = 'default_session'
    
    user_team = session.get('user_team')
    
    if not user_team:
        return render_template_string(RED_BLUE_TEMPLATE)
    
    # 获取分数信息
    scores = get_team_scores()
    
    # 模拟技术列表
    red_techniques = [
        {"id": "recon", "name": "侦察扫描", "description": "网络和端口扫描", "points": 10, "used": False},
        {"id": "phishing", "name": "钓鱼攻击", "description": "发送钓鱼邮件", "points": 20, "used": False},
        {"id": "exploit", "name": "漏洞利用", "description": "利用已知漏洞", "points": 30, "used": False},
        {"id": "privilege", "name": "权限提升", "description": "获取更高权限", "points": 25, "used": False},
        {"id": "lateral", "name": "横向移动", "description": "在网络中移动", "points": 35, "used": False},
        {"id": "persistence", "name": "持久化", "description": "维持系统访问", "points": 20, "used": False}
    ]
    
    blue_techniques = [
        {"id": "monitoring", "name": "监控部署", "description": "部署监控系统", "points": 15, "used": False},
        {"id": "honeypot", "name": "蜜罐部署", "description": "布置诱捕系统", "points": 20, "used": False},
        {"id": "forensics", "name": "取证分析", "description": "证据收集分析", "points": 25, "used": False},
        {"id": "incident", "name": "事件响应", "description": "安全事件处理", "points": 30, "used": False},
        {"id": "threat_hunt", "name": "威胁狩猎", "description": "主动威胁发现", "points": 35, "used": False},
        {"id": "recovery", "name": "系统恢复", "description": "受损系统恢复", "points": 40, "used": False}
    ]
    
    # 模拟网络资产
    network_assets = [
        {"id": "web_server", "name": "Web服务器", "ip": "192.168.1.100", "status": "normal", "x": 50, "y": 50},
        {"id": "db_server", "name": "数据库", "ip": "192.168.1.101", "status": "normal", "x": 200, "y": 50},
        {"id": "dc_server", "name": "域控制器", "ip": "192.168.1.10", "status": "normal", "x": 350, "y": 50},
        {"id": "workstation1", "name": "工作站1", "ip": "192.168.1.200", "status": "normal", "x": 50, "y": 150},
        {"id": "workstation2", "name": "工作站2", "ip": "192.168.1.201", "status": "normal", "x": 200, "y": 150},
        {"id": "firewall", "name": "防火墙", "ip": "192.168.1.1", "status": "defended", "x": 350, "y": 150}
    ]
    
    # 模拟行动日志
    action_logs = [
        {"timestamp": "14:32:15", "team": "red", "action": "对192.168.1.100执行端口扫描", "points": 10},
        {"timestamp": "14:31:45", "team": "blue", "action": "在数据库服务器部署蜜罐", "points": 20},
        {"timestamp": "14:30:22", "team": "red", "action": "发现Web服务器SQL注入漏洞", "points": 30},
        {"timestamp": "14:29:18", "team": "blue", "action": "更新入侵检测规则", "points": 15}
    ]
    
    # 模拟用户成就
    user_achievements = ["首次扫描", "发现漏洞", "成功利用"]
    
    # 模拟用户统计
    user_stats = {
        "total_score": random.randint(50, 200),
        "successful_actions": random.randint(3, 10),
        "failed_actions": random.randint(0, 3),
        "rank": random.randint(1, 8)
    }
    
    return render_template_string(RED_BLUE_TEMPLATE,
                                 scores=scores,
                                 timer_status="running",
                                 time_remaining="45:23",
                                 red_techniques=red_techniques,
                                 blue_techniques=blue_techniques,
                                 network_assets=network_assets,
                                 action_logs=action_logs,
                                 user_achievements=user_achievements,
                                 user_stats=user_stats)

@app.route('/api/join_team', methods=['POST'])
def join_team():
    """加入团队"""
    data = request.json
    team = data.get('team')
    
    if team not in ['red', 'blue', 'spectator']:
        return jsonify({"success": False, "error": "无效的团队"})
    
    session['user_team'] = team
    
    # 记录到数据库
    conn = sqlite3.connect('red_blue_exercise.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO team_members (session_id, user_id, team_type, role, join_time)
        VALUES (?, ?, ?, ?, ?)
    ''', (session.get('session_id'), session.get('user_id'), team, 'member', datetime.now().isoformat()))
    
    conn.commit()
    conn.close()
    
    return jsonify({"success": True, "team": team})

@app.route('/api/execute_attack', methods=['POST'])
def execute_attack():
    """执行攻击行动"""
    data = request.json
    technique_id = data.get('technique_id')
    
    if session.get('user_team') != 'red':
        return jsonify({"success": False, "error": "权限不足"})
    
    # 模拟攻击结果
    attack_techniques = {
        'recon': {'success_rate': 0.9, 'points': 10, 'message': '网络扫描完成，发现3个开放端口'},
        'phishing': {'success_rate': 0.7, 'points': 20, 'message': '钓鱼邮件发送成功，等待用户点击'},
        'exploit': {'success_rate': 0.6, 'points': 30, 'message': 'SQL注入攻击成功，获取数据库访问权限'},
        'privilege': {'success_rate': 0.5, 'points': 25, 'message': '权限提升成功，获得管理员权限'},
        'lateral': {'success_rate': 0.4, 'points': 35, 'message': '横向移动成功，控制域控制器'},
        'persistence': {'success_rate': 0.8, 'points': 20, 'message': '后门植入成功，维持系统访问'}
    }
    
    technique = attack_techniques.get(technique_id)
    if not technique:
        return jsonify({"success": False, "error": "未知攻击技术"})
    
    success = random.random() < technique['success_rate']
    points = technique['points'] if success else 0
    
    # 记录攻击行动
    log_action('red', technique_id, technique['message'], success, points)
    
    if success:
        return jsonify({
            "success": True, 
            "message": technique['message'],
            "points": points
        })
    else:
        return jsonify({
            "success": True,
            "message": "攻击被检测并阻止",
            "points": 0
        })

@app.route('/api/execute_defense', methods=['POST'])
def execute_defense():
    """执行防御行动"""
    data = request.json
    technique_id = data.get('technique_id')
    
    if session.get('user_team') != 'blue':
        return jsonify({"success": False, "error": "权限不足"})
    
    # 模拟防御结果
    defense_techniques = {
        'monitoring': {'success_rate': 0.8, 'points': 15, 'message': '监控系统部署完成，开始实时分析'},
        'honeypot': {'success_rate': 0.9, 'points': 20, 'message': '蜜罐部署成功，诱捕攻击者'},
        'forensics': {'success_rate': 0.7, 'points': 25, 'message': '取证分析完成，发现攻击痕迹'},
        'incident': {'success_rate': 0.8, 'points': 30, 'message': '事件响应启动，隔离受感染系统'},
        'threat_hunt': {'success_rate': 0.6, 'points': 35, 'message': '威胁狩猎发现高级持续性威胁'},
        'recovery': {'success_rate': 0.9, 'points': 40, 'message': '系统恢复完成，服务正常运行'}
    }
    
    technique = defense_techniques.get(technique_id)
    if not technique:
        return jsonify({"success": False, "error": "未知防御技术"})
    
    success = random.random() < technique['success_rate']
    points = technique['points'] if success else 0
    
    # 记录防御行动
    log_action('blue', technique_id, technique['message'], success, points)
    
    if success:
        return jsonify({
            "success": True,
            "message": technique['message'], 
            "points": points
        })
    else:
        return jsonify({
            "success": True,
            "message": "防御措施部署失败",
            "points": 0
        })

@app.route('/api/get_scores')
def get_scores():
    """获取团队分数"""
    return jsonify(get_team_scores())

@app.route('/api/get_status')
def get_status():
    """获取演练状态"""
    return jsonify({
        "status": "running",
        "new_actions": False,
        "time_remaining": "45:23"
    })

def get_team_scores():
    """计算团队分数"""
    conn = sqlite3.connect('red_blue_exercise.db')
    cursor = conn.cursor()
    
    # 计算红队分数
    cursor.execute('''
        SELECT COALESCE(SUM(points), 0) FROM attack_actions 
        WHERE session_id = ? AND team_type = 'red'
    ''', (session.get('session_id'),))
    red_score = cursor.fetchone()[0]
    
    # 计算蓝队分数
    cursor.execute('''
        SELECT COALESCE(SUM(points), 0) FROM defense_actions 
        WHERE session_id = ?
    ''', (session.get('session_id'),))
    blue_score = cursor.fetchone()[0]
    
    # 统计团队成员数量
    cursor.execute('''
        SELECT COUNT(*) FROM team_members 
        WHERE session_id = ? AND team_type = 'red'
    ''', (session.get('session_id'),))
    red_members = cursor.fetchone()[0]
    
    cursor.execute('''
        SELECT COUNT(*) FROM team_members 
        WHERE session_id = ? AND team_type = 'blue'
    ''', (session.get('session_id'),))
    blue_members = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        "red_score": red_score,
        "blue_score": blue_score,
        "red_members": red_members,
        "blue_members": blue_members
    }

def log_action(team_type, action_type, description, success, points):
    """记录行动到数据库"""
    conn = sqlite3.connect('red_blue_exercise.db')
    cursor = conn.cursor()
    
    if team_type == 'red':
        cursor.execute('''
            INSERT INTO attack_actions (session_id, team_type, user_id, action_type, description, timestamp, success, points)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (session.get('session_id'), team_type, session.get('user_id'), 
              action_type, description, datetime.now().isoformat(), 
              1 if success else 0, points))
    else:
        cursor.execute('''
            INSERT INTO defense_actions (session_id, user_id, action_type, description, timestamp, effectiveness, points)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (session.get('session_id'), session.get('user_id'),
              action_type, description, datetime.now().isoformat(),
              1 if success else 0, points))
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    print("⚔️ 启动红蓝对抗演练平台...")
    print("访问 http://localhost:5006 参加红蓝对抗")
    print("")
    print("🎮 平台特色:")
    print("  - 实时红蓝对抗")
    print("  - MITRE ATT&CK技术库")
    print("  - 分数和排名系统")
    print("  - 网络态势可视化")
    print("  - 成就和徽章系统")
    print("  - 团队协作功能")
    
    app.run(host='0.0.0.0', port=5006, debug=True)
