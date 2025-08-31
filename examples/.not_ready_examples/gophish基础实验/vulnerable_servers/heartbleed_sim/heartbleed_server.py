#!/usr/bin/env python
"""
Heartbleed漏洞仿真服务器
模拟CVE-2014-0160漏洞，展示内存泄露风险
"""

from flask import Flask, request, render_template_string, jsonify
import ssl
import socket
import threading
import time
import random
import string
from datetime import datetime
import json
import os

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
"""

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
    
    log_file = '../../logs/attacks.log'
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')

if __name__ == '__main__':
    print("🚨 Heartbleed漏洞仿真服务器启动在端口 5003")
    print("访问 http://localhost:5003 测试Heartbleed漏洞")
    print("点击'执行Heartbleed测试'按钮查看内存泄露")
    app.run(host='0.0.0.0', port=5003, debug=True)
