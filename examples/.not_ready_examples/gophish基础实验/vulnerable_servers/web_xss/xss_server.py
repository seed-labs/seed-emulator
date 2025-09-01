#!/usr/bin/env python
"""
XSS漏洞Web服务器
模拟企业内部反馈系统，存在存储型XSS漏洞
"""

from flask import Flask, request, render_template_string
import sqlite3
import os
from datetime import datetime
import json

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
"""

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
    
    log_file = '../../logs/attacks.log'
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')

if __name__ == '__main__':
    init_db()
    print("🚨 XSS漏洞服务器启动在端口 5004")
    print("访问 http://localhost:5004 测试XSS漏洞")
    print("尝试在反馈中输入: <script>alert('XSS攻击成功！')</script>")
    app.run(host='0.0.0.0', port=5004, debug=True)
