#!/usr/bin/env python
"""
SQL注入漏洞数据库服务器
模拟员工信息查询系统，存在SQL注入漏洞
"""

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
"""

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
    
    log_file = '../../logs/attacks.log'
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')

if __name__ == '__main__':
    init_employee_db()
    print("🚨 SQL注入漏洞服务器启动在端口 5002")
    print("访问 http://localhost:5002 测试SQL注入漏洞")
    print("尝试输入: 1001' OR '1'='1")
    app.run(host='0.0.0.0', port=5002, debug=True)
