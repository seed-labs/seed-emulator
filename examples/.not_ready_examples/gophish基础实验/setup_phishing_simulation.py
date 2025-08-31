#!/usr/bin/env python3
"""
Gophish 钓鱼后仿真系统
包含：
1. 带XSS漏洞的Web服务器
2. 带SQL注入漏洞的数据库服务器  
3. Heartbleed漏洞仿真PC环境
4. 可视化损失仪表板
"""

import os
import subprocess
import threading
import time
import sqlite3
import json
from datetime import datetime
from flask import Flask, request, render_template_string, jsonify, send_file
import sqlite3
import hashlib
import random

class PhishingSimulation:
    def __init__(self):
        self.base_dir = "/Users/zzw4257/Documents/ZJU_archieve/25-seed/gophish基础实验"
        self.setup_directories()
        
    def setup_directories(self):
        """创建必要的目录结构"""
        dirs = [
            "vulnerable_servers",
            "vulnerable_servers/web_xss", 
            "vulnerable_servers/db_sqli",
            "vulnerable_servers/heartbleed_sim",
            "dashboard",
            "templates",
            "logs"
        ]
        
        for dir_name in dirs:
            full_path = os.path.join(self.base_dir, dir_name)
            os.makedirs(full_path, exist_ok=True)
            
    def create_xss_vulnerable_server(self):
        """创建带XSS漏洞的Web服务器"""
        xss_server_code = '''
from flask import Flask, request, render_template_string
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)

# XSS 漏洞页面模板
XSS_PAGE_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>企业内部系统 - 用户反馈</title>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
        .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; margin-bottom: 20px; }
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; font-weight: bold; }
        input, textarea { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }
        button { background: #3498db; color: white; padding: 12px 20px; border: none; border-radius: 5px; cursor: pointer; }
        .comments { margin-top: 30px; }
        .comment { background: #f9f9f9; padding: 15px; margin: 10px 0; border-left: 4px solid #3498db; }
        .warning { color: #e74c3c; font-size: 12px; margin-top: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>企业内部反馈系统</h1>
            <p>您的意见对我们很重要，请留下您的宝贵建议</p>
        </div>
        
        <form method="POST">
            <div class="form-group">
                <label for="name">姓名:</label>
                <input type="text" id="name" name="name" required>
            </div>
            
            <div class="form-group">
                <label for="email">邮箱:</label>
                <input type="email" id="email" name="email" required>
            </div>
            
            <div class="form-group">
                <label for="feedback">反馈内容:</label>
                <textarea id="feedback" name="feedback" rows="5" required></textarea>
                <div class="warning">⚠️ 系统会显示您的反馈内容</div>
            </div>
            
            <button type="submit">提交反馈</button>
        </form>
        
        <div class="comments">
            <h3>最近的反馈：</h3>
            {% for comment in comments %}
            <div class="comment">
                <strong>{{ comment.name }}</strong> ({{ comment.email }}) - {{ comment.timestamp }}
                <p>{{ comment.feedback|safe }}</p>
            </div>
            {% endfor %}
        </div>
    </div>
    
    <!-- 模拟敏感信息 -->
    <script>
        // 企业内部API密钥 (模拟)
        const API_KEY = "sk-1234567890abcdef";
        const INTERNAL_SERVERS = ["db.internal.company.com", "api.internal.company.com"];
        
        function showSensitiveData() {
            console.log("Internal API Key:", API_KEY);
            console.log("Internal Servers:", INTERNAL_SERVERS);
        }
    </script>
</body>
</html>
'''

# 初始化数据库
def init_db():
    conn = sqlite3.connect('feedback.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            feedback TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            ip_address TEXT
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/', methods=['GET', 'POST'])
def feedback_form():
    if request.method == 'POST':
        name = request.form.get('name', '')
        email = request.form.get('email', '')
        feedback = request.form.get('feedback', '')  # XSS漏洞：直接使用用户输入
        
        # 记录数据
        conn = sqlite3.connect('feedback.db')
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO feedback (name, email, feedback, timestamp, ip_address) VALUES (?, ?, ?, ?, ?)',
            (name, email, feedback, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), request.remote_addr)
        )
        conn.commit()
        conn.close()
        
        # 记录XSS攻击日志
        if '<script>' in feedback.lower() or 'javascript:' in feedback.lower():
            log_attack('XSS', f"XSS攻击检测: {request.remote_addr} - {feedback[:100]}")
    
    # 获取所有反馈显示（包含XSS漏洞）
    conn = sqlite3.connect('feedback.db')
    cursor = conn.cursor()
    cursor.execute('SELECT name, email, feedback, timestamp FROM feedback ORDER BY id DESC LIMIT 10')
    comments = []
    for row in cursor.fetchall():
        comments.append({
            'name': row[0],
            'email': row[1], 
            'feedback': row[2],  # 直接输出，存在XSS漏洞
            'timestamp': row[3]
        })
    conn.close()
    
    return render_template_string(XSS_PAGE_TEMPLATE, comments=comments)

def log_attack(attack_type, details):
    """记录攻击日志"""
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'type': attack_type,
        'details': details,
        'severity': 'HIGH' if attack_type == 'XSS' else 'MEDIUM'
    }
    
    with open('../logs/attacks.log', 'a') as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + '\\n')

if __name__ == '__main__':
    init_db()
    print("🚨 XSS漏洞服务器启动在端口 5001")
    print("访问 http://localhost:5001 测试XSS漏洞")
    print("尝试在反馈中输入: <script>alert('XSS攻击成功！')</script>")
    app.run(host='0.0.0.0', port=5001, debug=True)
'''
        
        with open(os.path.join(self.base_dir, "vulnerable_servers/web_xss/xss_server.py"), 'w', encoding='utf-8') as f:
            f.write(xss_server_code)
            
    def create_sqli_vulnerable_server(self):
        """创建带SQL注入漏洞的数据库服务器"""
        sqli_server_code = '''
from flask import Flask, request, render_template_string, jsonify
import sqlite3
import os
from datetime import datetime
import json

app = Flask(__name__)

# SQL注入漏洞页面模板
SQLI_PAGE_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>员工信息查询系统</title>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
        .container { max-width: 1000px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header { color: #2c3e50; border-bottom: 2px solid #e74c3c; padding-bottom: 10px; margin-bottom: 20px; }
        .search-form { background: #ecf0f1; padding: 20px; border-radius: 5px; margin-bottom: 20px; }
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; font-weight: bold; }
        input { width: 300px; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }
        button { background: #e74c3c; color: white; padding: 12px 20px; border: none; border-radius: 5px; cursor: pointer; margin-left: 10px; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #f2f2f2; }
        .warning { color: #e74c3c; font-size: 12px; margin-top: 5px; }
        .example { background: #fff3cd; padding: 10px; border: 1px solid #ffeaa7; border-radius: 5px; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏢 员工信息管理系统</h1>
            <p>查询员工基本信息和薪资数据</p>
        </div>
        
        <div class="search-form">
            <form method="GET">
                <div class="form-group">
                    <label for="employee_id">员工ID查询:</label>
                    <input type="text" id="employee_id" name="employee_id" value="{{ search_id }}" placeholder="请输入员工ID">
                    <button type="submit">🔍 查询</button>
                </div>
                <div class="warning">⚠️ 仅允许查询自己的员工信息</div>
            </form>
            
            <div class="example">
                <strong>示例查询：</strong>
                <ul>
                    <li>员工ID: 1001, 1002, 1003</li>
                    <li>SQL注入测试: <code>1001' OR '1'='1</code></li>
                    <li>查看所有数据: <code>' UNION SELECT * FROM employees--</code></li>
                </ul>
            </div>
        </div>
        
        {% if results %}
        <h3>查询结果：</h3>
        <table>
            <tr>
                <th>员工ID</th>
                <th>姓名</th>
                <th>部门</th>
                <th>职位</th>
                <th>薪资</th>
                <th>邮箱</th>
                <th>入职日期</th>
            </tr>
            {% for row in results %}
            <tr>
                <td>{{ row[0] }}</td>
                <td>{{ row[1] }}</td>
                <td>{{ row[2] }}</td>
                <td>{{ row[3] }}</td>
                <td>¥{{ row[4] }}</td>
                <td>{{ row[5] }}</td>
                <td>{{ row[6] }}</td>
            </tr>
            {% endfor %}
        </table>
        {% endif %}
        
        {% if error %}
        <div style="color: red; background: #ffe6e6; padding: 15px; border-radius: 5px;">
            <strong>数据库错误:</strong> {{ error }}
        </div>
        {% endif %}
    </div>
</body>
</html>
'''

# 初始化员工数据库
def init_employee_db():
    conn = sqlite3.connect('employees.db')
    cursor = conn.cursor()
    
    # 创建员工表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            department TEXT NOT NULL,
            position TEXT NOT NULL,
            salary INTEGER NOT NULL,
            email TEXT NOT NULL,
            hire_date TEXT NOT NULL
        )
    ''')
    
    # 插入示例数据
    employees_data = [
        (1001, '张三', 'IT部', '软件工程师', 120000, 'zhangsan@company.com', '2022-01-15'),
        (1002, '李四', '财务部', '会计师', 85000, 'lisi@company.com', '2021-03-20'),
        (1003, '王五', '人事部', 'HR专员', 75000, 'wangwu@company.com', '2020-07-10'),
        (1004, '赵六', 'IT部', '系统管理员', 95000, 'zhaoliu@company.com', '2021-11-01'),
        (1005, '刘七', '销售部', '销售经理', 150000, 'liuqi@company.com', '2019-05-15'),
        (9999, 'admin', '管理层', '系统管理员', 300000, 'admin@company.com', '2018-01-01')
    ]
    
    cursor.executemany(
        'INSERT OR REPLACE INTO employees VALUES (?, ?, ?, ?, ?, ?, ?)',
        employees_data
    )
    
    conn.commit()
    conn.close()

@app.route('/', methods=['GET'])
def employee_search():
    search_id = request.args.get('employee_id', '')
    results = []
    error = None
    
    if search_id:
        try:
            conn = sqlite3.connect('employees.db')
            cursor = conn.cursor()
            
            # SQL注入漏洞：直接拼接用户输入到SQL查询中
            query = f"SELECT * FROM employees WHERE id = {search_id}"
            print(f"执行SQL查询: {query}")  # 用于调试
            
            cursor.execute(query)
            results = cursor.fetchall()
            conn.close()
            
            # 记录SQL注入攻击日志
            if any(keyword in search_id.lower() for keyword in ['or', 'union', 'select', '--', ';']):
                log_attack('SQL_INJECTION', f"SQL注入检测: {request.remote_addr} - {query}")
                
        except Exception as e:
            error = str(e)
            log_attack('SQL_INJECTION', f"SQL注入错误: {request.remote_addr} - {str(e)}")
    
    return render_template_string(SQLI_PAGE_TEMPLATE, 
                                 results=results, 
                                 error=error, 
                                 search_id=search_id)

def log_attack(attack_type, details):
    """记录攻击日志"""
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'type': attack_type,
        'details': details,
        'severity': 'CRITICAL' if attack_type == 'SQL_INJECTION' else 'MEDIUM'
    }
    
    with open('../logs/attacks.log', 'a') as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + '\\n')

if __name__ == '__main__':
    init_employee_db()
    print("🚨 SQL注入漏洞服务器启动在端口 5002")
    print("访问 http://localhost:5002 测试SQL注入漏洞")
    print("尝试输入: 1001' OR '1'='1")
    app.run(host='0.0.0.0', port=5002, debug=True)
'''
        
        with open(os.path.join(self.base_dir, "vulnerable_servers/db_sqli/sqli_server.py"), 'w', encoding='utf-8') as f:
            f.write(sqli_server_code)
            
    def create_heartbleed_simulation(self):
        """创建Heartbleed漏洞仿真"""
        heartbleed_code = '''
from flask import Flask, request, render_template_string, jsonify
import ssl
import socket
import threading
import time
import random
import string
from datetime import datetime
import json

app = Flask(__name__)

# Heartbleed漏洞仿真页面
HEARTBLEED_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>安全通信测试系统</title>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
        .container { max-width: 900px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header { color: #2c3e50; border-bottom: 2px solid #27ae60; padding-bottom: 10px; margin-bottom: 20px; }
        .test-section { background: #ecf0f1; padding: 20px; border-radius: 5px; margin: 15px 0; }
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; font-weight: bold; }
        input, textarea { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; max-width: 400px; }
        button { background: #27ae60; color: white; padding: 12px 20px; border: none; border-radius: 5px; cursor: pointer; margin: 5px; }
        .danger-btn { background: #e74c3c; }
        .result { background: #f9f9f9; padding: 15px; border-left: 4px solid #3498db; margin: 10px 0; }
        .memory-dump { background: #2c3e50; color: #ecf0f1; padding: 15px; border-radius: 5px; font-family: monospace; font-size: 12px; overflow-x: auto; }
        .warning { color: #e74c3c; font-size: 12px; margin-top: 5px; }
        .status { padding: 10px; margin: 10px 0; border-radius: 5px; }
        .vulnerable { background: #ffe6e6; border: 1px solid #e74c3c; color: #e74c3c; }
        .secure { background: #e8f5e8; border: 1px solid #27ae60; color: #27ae60; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔐 SSL/TLS 安全通信测试系统</h1>
            <p>测试系统的SSL/TLS连接安全性</p>
        </div>
        
        <div class="status {{ 'vulnerable' if is_vulnerable else 'secure' }}">
            <strong>系统状态:</strong> 
            {% if is_vulnerable %}
            ⚠️ 检测到Heartbleed漏洞 (CVE-2014-0160)
            {% else %}
            ✅ SSL连接安全
            {% endif %}
        </div>
        
        <div class="test-section">
            <h3>🔍 SSL连接测试</h3>
            <form method="POST" action="/test_ssl">
                <div class="form-group">
                    <label for="server">服务器地址:</label>
                    <input type="text" id="server" name="server" value="localhost:4433" placeholder="host:port">
                </div>
                <button type="submit">测试SSL连接</button>
                <button type="submit" name="heartbleed_test" value="1" class="danger-btn">🚨 执行Heartbleed测试</button>
            </form>
            <div class="warning">⚠️ Heartbleed测试可能泄露服务器内存数据</div>
        </div>
        
        {% if test_result %}
        <div class="result">
            <h4>测试结果:</h4>
            <p><strong>状态:</strong> {{ test_result.status }}</p>
            <p><strong>SSL版本:</strong> {{ test_result.ssl_version }}</p>
            <p><strong>加密套件:</strong> {{ test_result.cipher }}</p>
            {% if test_result.vulnerability %}
            <p><strong>漏洞:</strong> <span style="color: #e74c3c;">{{ test_result.vulnerability }}</span></p>
            {% endif %}
        </div>
        {% endif %}
        
        {% if memory_leak %}
        <div class="result">
            <h4>🚨 内存泄露数据 (Heartbleed攻击结果):</h4>
            <div class="memory-dump">{{ memory_leak }}</div>
            <div class="warning">⚠️ 以上数据从服务器内存中泄露，可能包含敏感信息</div>
        </div>
        {% endif %}
        
        <div class="test-section">
            <h3>📋 漏洞信息</h3>
            <p><strong>CVE-2014-0160 (Heartbleed):</strong></p>
            <ul>
                <li>影响OpenSSL 1.0.1 - 1.0.1f版本</li>
                <li>攻击者可以读取服务器内存中的敏感数据</li>
                <li>可能泄露私钥、用户密码、会话令牌等</li>
                <li>影响全球约17%的安全Web服务器</li>
            </ul>
        </div>
    </div>
</body>
</html>
'''

# 模拟服务器内存数据
FAKE_MEMORY_DATA = [
    "user_sessions: {'admin': 'sk-abc123', 'user1': 'token-xyz789'}",
    "private_key: -----BEGIN RSA PRIVATE KEY-----\\nMIIEpAIBAAKCAQEA...",
    "database_password: MyS3cur3P@ssw0rd",
    "api_keys: {'service_a': 'key_123', 'service_b': 'key_456'}",
    "user_credentials: admin:$2b$12$xyz.../user1:$2b$12$abc...",
    "internal_config: {'debug': true, 'secret_key': 'super_secret_key_123'}",
    "server_memory: HTTP/1.1 200 OK\\r\\nSet-Cookie: session=abc123",
    "payment_data: {'card': '****-****-****-1234', 'amount': 999.99}",
]

@app.route('/')
def index():
    # 随机决定是否显示漏洞状态
    is_vulnerable = random.choice([True, False])
    return render_template_string(HEARTBLEED_TEMPLATE, 
                                 is_vulnerable=is_vulnerable,
                                 test_result=None,
                                 memory_leak=None)

@app.route('/test_ssl', methods=['POST'])
def test_ssl():
    server = request.form.get('server', 'localhost:4433')
    heartbleed_test = request.form.get('heartbleed_test', False)
    
    # 模拟SSL测试结果
    test_result = {
        'status': 'Connected',
        'ssl_version': 'TLSv1.2',
        'cipher': 'ECDHE-RSA-AES256-GCM-SHA384',
        'vulnerability': None
    }
    
    memory_leak = None
    
    if heartbleed_test:
        # 模拟Heartbleed攻击
        test_result['vulnerability'] = 'Heartbleed (CVE-2014-0160) - 内存泄露漏洞'
        
        # 生成模拟的内存泄露数据
        leaked_data = []
        for _ in range(5):
            leaked_data.append(random.choice(FAKE_MEMORY_DATA))
        
        # 添加一些随机的十六进制数据
        hex_data = ''.join([f"{random.randint(0, 255):02x} " for _ in range(50)])
        leaked_data.append(f"raw_memory: {hex_data}")
        
        memory_leak = '\\n'.join(leaked_data)
        
        # 记录攻击日志
        log_attack('HEARTBLEED', f"Heartbleed攻击模拟: {request.remote_addr} - 服务器: {server}")
    
    return render_template_string(HEARTBLEED_TEMPLATE, 
                                 is_vulnerable=True,
                                 test_result=test_result,
                                 memory_leak=memory_leak)

def log_attack(attack_type, details):
    """记录攻击日志"""
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'type': attack_type,
        'details': details,
        'severity': 'CRITICAL' if attack_type == 'HEARTBLEED' else 'MEDIUM'
    }
    
    with open('../logs/attacks.log', 'a') as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + '\\n')

if __name__ == '__main__':
    print("🚨 Heartbleed漏洞仿真服务器启动在端口 5003")
    print("访问 http://localhost:5003 测试Heartbleed漏洞")
    print("点击'执行Heartbleed测试'按钮查看内存泄露")
    app.run(host='0.0.0.0', port=5003, debug=True)
'''
        
        with open(os.path.join(self.base_dir, "vulnerable_servers/heartbleed_sim/heartbleed_server.py"), 'w', encoding='utf-8') as f:
            f.write(heartbleed_code)
            
    def create_dashboard(self):
        """创建可视化损失仪表板"""
        dashboard_code = '''
from flask import Flask, render_template_string, jsonify
import json
import os
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import sqlite3

app = Flask(__name__)

# 仪表板HTML模板
DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>钓鱼攻击损失评估仪表板</title>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        .header { background: #2c3e50; color: white; padding: 20px; margin: -20px -20px 20px -20px; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .stat-card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .stat-value { font-size: 2.5em; font-weight: bold; margin-bottom: 5px; }
        .stat-label { color: #666; font-size: 0.9em; }
        .critical { color: #e74c3c; }
        .high { color: #f39c12; }
        .medium { color: #f1c40f; }
        .low { color: #27ae60; }
        .chart-container { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 20px; }
        .log-entry { background: #f9f9f9; border-left: 4px solid #3498db; padding: 15px; margin: 10px 0; }
        .attack-type { display: inline-block; padding: 4px 8px; border-radius: 3px; color: white; font-size: 0.8em; margin-right: 10px; }
        .xss { background: #e74c3c; }
        .sql-injection { background: #8e44ad; }
        .heartbleed { background: #c0392b; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #f2f2f2; }
        .refresh-btn { background: #3498db; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; margin-bottom: 20px; }
    </style>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
    <div class="header">
        <h1>🎯 钓鱼攻击损失评估仪表板</h1>
        <p>实时监控钓鱼攻击后的潜在损失和安全风险</p>
    </div>
    
    <button class="refresh-btn" onclick="location.reload()">🔄 刷新数据</button>
    
    <div class="stats-grid">
        <div class="stat-card">
            <div class="stat-value critical">{{ stats.total_attacks }}</div>
            <div class="stat-label">总攻击次数</div>
        </div>
        
        <div class="stat-card">
            <div class="stat-value high">{{ stats.xss_attacks }}</div>
            <div class="stat-label">XSS攻击</div>
        </div>
        
        <div class="stat-card">
            <div class="stat-value critical">{{ stats.sqli_attacks }}</div>
            <div class="stat-label">SQL注入攻击</div>
        </div>
        
        <div class="stat-card">
            <div class="stat-value critical">{{ stats.heartbleed_attacks }}</div>
            <div class="stat-label">Heartbleed攻击</div>
        </div>
        
        <div class="stat-card">
            <div class="stat-value high">¥{{ "{:,.0f}".format(stats.estimated_loss) }}</div>
            <div class="stat-label">估算损失(元)</div>
        </div>
        
        <div class="stat-card">
            <div class="stat-value {{ 'critical' if stats.risk_level == 'CRITICAL' else 'high' if stats.risk_level == 'HIGH' else 'medium' }}">{{ stats.risk_level }}</div>
            <div class="stat-label">风险等级</div>
        </div>
    </div>
    
    <div class="chart-container">
        <h3>攻击类型分布</h3>
        <canvas id="attackChart" width="400" height="200"></canvas>
    </div>
    
    <div class="chart-container">
        <h3>损失影响评估</h3>
        <table>
            <tr>
                <th>攻击类型</th>
                <th>攻击次数</th>
                <th>风险级别</th>
                <th>潜在损失</th>
                <th>影响范围</th>
            </tr>
            <tr>
                <td><span class="attack-type xss">XSS</span></td>
                <td>{{ stats.xss_attacks }}</td>
                <td><span class="high">HIGH</span></td>
                <td>¥{{ "{:,.0f}".format(stats.xss_attacks * 50000) }}</td>
                <td>用户数据泄露、会话劫持</td>
            </tr>
            <tr>
                <td><span class="attack-type sql-injection">SQL注入</span></td>
                <td>{{ stats.sqli_attacks }}</td>
                <td><span class="critical">CRITICAL</span></td>
                <td>¥{{ "{:,.0f}".format(stats.sqli_attacks * 200000) }}</td>
                <td>数据库完全暴露、客户信息泄露</td>
            </tr>
            <tr>
                <td><span class="attack-type heartbleed">Heartbleed</span></td>
                <td>{{ stats.heartbleed_attacks }}</td>
                <td><span class="critical">CRITICAL</span></td>
                <td>¥{{ "{:,.0f}".format(stats.heartbleed_attacks * 300000) }}</td>
                <td>私钥泄露、系统全面沦陷</td>
            </tr>
        </table>
    </div>
    
    <div class="chart-container">
        <h3>最近的攻击日志</h3>
        {% for log in recent_logs[:10] %}
        <div class="log-entry">
            <span class="attack-type {{ log.type.lower().replace('_', '-') }}">{{ log.type }}</span>
            <strong>{{ log.timestamp }}</strong> - {{ log.details }}
            <br><small>风险级别: {{ log.severity }}</small>
        </div>
        {% endfor %}
    </div>
    
    <script>
        // 攻击类型分布图表
        const ctx = document.getElementById('attackChart').getContext('2d');
        const attackChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['XSS攻击', 'SQL注入', 'Heartbleed', '其他'],
                datasets: [{
                    data: [{{ stats.xss_attacks }}, {{ stats.sqli_attacks }}, {{ stats.heartbleed_attacks }}, 1],
                    backgroundColor: [
                        '#e74c3c',
                        '#8e44ad', 
                        '#c0392b',
                        '#95a5a6'
                    ]
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
        
        // 自动刷新
        setInterval(() => {
            location.reload();
        }, 30000); // 每30秒刷新一次
    </script>
</body>
</html>
'''

def load_attack_logs():
    """加载攻击日志"""
    logs = []
    log_file = '/Users/zzw4257/Documents/ZJU_archieve/25-seed/gophish基础实验/logs/attacks.log'
    
    if os.path.exists(log_file):
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        try:
                            log_data = json.loads(line.strip())
                            logs.append(log_data)
                        except:
                            continue
        except:
            pass
    
    return sorted(logs, key=lambda x: x.get('timestamp', ''), reverse=True)

def calculate_stats(logs):
    """计算统计数据"""
    stats = {
        'total_attacks': len(logs),
        'xss_attacks': 0,
        'sqli_attacks': 0,
        'heartbleed_attacks': 0,
        'estimated_loss': 0,
        'risk_level': 'LOW'
    }
    
    for log in logs:
        attack_type = log.get('type', '')
        if attack_type == 'XSS':
            stats['xss_attacks'] += 1
            stats['estimated_loss'] += 50000  # XSS攻击估算损失5万
        elif attack_type == 'SQL_INJECTION':
            stats['sqli_attacks'] += 1
            stats['estimated_loss'] += 200000  # SQL注入估算损失20万
        elif attack_type == 'HEARTBLEED':
            stats['heartbleed_attacks'] += 1
            stats['estimated_loss'] += 300000  # Heartbleed估算损失30万
    
    # 计算风险等级
    if stats['sqli_attacks'] > 0 or stats['heartbleed_attacks'] > 0:
        stats['risk_level'] = 'CRITICAL'
    elif stats['xss_attacks'] > 3 or stats['total_attacks'] > 5:
        stats['risk_level'] = 'HIGH'
    elif stats['total_attacks'] > 0:
        stats['risk_level'] = 'MEDIUM'
    
    return stats

@app.route('/')
def dashboard():
    logs = load_attack_logs()
    stats = calculate_stats(logs)
    
    # 转换日志格式供模板使用
    recent_logs = []
    for log in logs:
        recent_logs.append({
            'type': log.get('type', ''),
            'timestamp': log.get('timestamp', ''),
            'details': log.get('details', ''),
            'severity': log.get('severity', '')
        })
    
    return render_template_string(DASHBOARD_TEMPLATE, 
                                 stats=stats, 
                                 recent_logs=recent_logs)

@app.route('/api/stats')
def api_stats():
    """API接口获取统计数据"""
    logs = load_attack_logs()
    stats = calculate_stats(logs)
    return jsonify(stats)

if __name__ == '__main__':
    print("📊 钓鱼损失评估仪表板启动在端口 5000")
    print("访问 http://localhost:5000 查看损失评估")
    app.run(host='0.0.0.0', port=5000, debug=True)
'''
        
        with open(os.path.join(self.base_dir, "dashboard/dashboard.py"), 'w', encoding='utf-8') as f:
            f.write(dashboard_code)
            
    def create_startup_script(self):
        """创建启动脚本"""
        startup_script = '''#!/bin/bash

echo "🚀 启动钓鱼后仿真系统..."

# 创建日志目录
mkdir -p logs

# 启动各个服务器
echo "启动XSS漏洞服务器..."
cd vulnerable_servers/web_xss && python3 xss_server.py &

echo "启动SQL注入漏洞服务器..."
cd ../db_sqli && python3 sqli_server.py &

echo "启动Heartbleed仿真服务器..."
cd ../heartbleed_sim && python3 heartbleed_server.py &

echo "启动损失评估仪表板..."
cd ../../dashboard && python3 dashboard.py &

echo ""
echo "🌐 所有服务已启动："
echo "  - XSS漏洞服务器: http://localhost:5001"
echo "  - SQL注入服务器: http://localhost:5002" 
echo "  - Heartbleed仿真: http://localhost:5003"
echo "  - 损失评估仪表板: http://localhost:5000"
echo "  - Gophish管理面板: https://localhost:3333"
echo ""
echo "🔧 使用说明："
echo "1. 访问 https://localhost:3333 配置Gophish钓鱼邮件"
echo "2. 配置QQ邮箱SMTP: smtp.qq.com:465"
echo "3. 发送钓鱼邮件后，引导目标访问漏洞服务器"
echo "4. 在损失评估仪表板查看攻击统计和损失评估"
echo ""
echo "按 Ctrl+C 停止所有服务"

# 等待用户中断
wait
'''
        
        with open(os.path.join(self.base_dir, "start_simulation.sh"), 'w') as f:
            f.write(startup_script)
            
        # 设置执行权限
        os.chmod(os.path.join(self.base_dir, "start_simulation.sh"), 0o755)
        
    def create_gophish_config_guide(self):
        """创建Gophish配置指南"""
        config_guide = '''
# Gophish 钓鱼平台配置指南

## 1. 访问管理界面
- URL: https://localhost:3333
- 默认用户名: admin
- 密码: 在终端启动时显示

## 2. 配置QQ邮箱发送配置
进入 "Sending Profiles" -> "New Profile"：

```
Name: QQ邮箱测试
From: 809050685@qq.com
Host: smtp.qq.com:465
Username: 809050685@qq.com
Password: xutqpejdkpfcbbhi
```

## 3. 创建钓鱼邮件模板
进入 "Email Templates" -> "New Template"：

### 模板示例1: 系统升级通知
```
Subject: 【紧急】系统安全升级通知
内容: 
尊敬的用户，

我们的系统将进行重要安全升级，请立即点击以下链接完成必要的验证：
{{.URL}}

如不及时处理，您的账户可能被暂时冻结。

IT部门
```

### 模板示例2: 财务通知
```
Subject: 工资条查看通知
内容:
您好，

本月工资条已生成，请点击链接查看详情：
{{.URL}}

财务部
```

## 4. 创建目标群组
进入 "Users & Groups" -> "New Group"：

添加测试邮箱地址

## 5. 创建钓鱼页面
进入 "Landing Pages" -> "New Page"：

可以导入或自定义登录页面，模拟：
- 企业内部系统登录
- 邮箱登录页面
- 银行登录页面

## 6. 启动钓鱼活动
进入 "Campaigns" -> "New Campaign"：
- 选择邮件模板
- 选择目标群组
- 选择钓鱼页面
- 设置发送时间

## 7. 查看结果
在 "Results" 页面可以看到：
- 邮件发送状态
- 点击链接的用户
- 输入凭据的用户
- 地理位置信息

## 漏洞服务器说明

### XSS漏洞服务器 (端口5001)
- 模拟企业反馈系统
- 存在存储型XSS漏洞
- 测试payload: <script>alert('XSS')</script>

### SQL注入服务器 (端口5002)  
- 模拟员工查询系统
- 存在SQL注入漏洞
- 测试payload: 1001' OR '1'='1

### Heartbleed仿真 (端口5003)
- 模拟SSL/TLS服务
- 模拟CVE-2014-0160漏洞
- 可查看模拟的内存泄露

### 损失评估仪表板 (端口5000)
- 实时显示攻击统计
- 计算预估损失
- 可视化风险等级

## 使用流程
1. 启动所有服务
2. 配置Gophish发送邮件
3. 受害者点击邮件链接
4. 引导受害者访问漏洞服务器
5. 在仪表板查看损失评估
'''
        
        with open(os.path.join(self.base_dir, "GOPHISH_CONFIG.md"), 'w', encoding='utf-8') as f:
            f.write(config_guide)
            
    def create_requirements_file(self):
        """创建依赖文件"""
        requirements = '''Flask==2.3.3
sqlite3
'''
        with open(os.path.join(self.base_dir, "requirements.txt"), 'w') as f:
            f.write(requirements)
            
    def run_setup(self):
        """运行完整安装"""
        print("🚀 开始创建钓鱼后仿真系统...")
        
        self.create_xss_vulnerable_server()
        print("✅ XSS漏洞服务器创建完成")
        
        self.create_sqli_vulnerable_server()
        print("✅ SQL注入漏洞服务器创建完成")
        
        self.create_heartbleed_simulation()
        print("✅ Heartbleed仿真服务器创建完成")
        
        self.create_dashboard()
        print("✅ 损失评估仪表板创建完成")
        
        self.create_startup_script()
        print("✅ 启动脚本创建完成")
        
        self.create_gophish_config_guide()
        print("✅ 配置指南创建完成")
        
        self.create_requirements_file()
        print("✅ 依赖文件创建完成")
        
        print("\n🎯 钓鱼后仿真系统创建完成！")
        print("\n📋 接下来的步骤：")
        print("1. 运行: pip3 install -r requirements.txt")
        print("2. 运行: ./start_simulation.sh")
        print("3. 访问 https://localhost:3333 配置Gophish")
        print("4. 查看 GOPHISH_CONFIG.md 了解详细配置")

if __name__ == "__main__":
    simulation = PhishingSimulation()
    simulation.run_setup()
