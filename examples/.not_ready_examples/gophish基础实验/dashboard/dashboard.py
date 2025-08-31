#!/usr/bin/env python
"""
钓鱼攻击损失评估仪表板
实时显示攻击统计和潜在损失
"""

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
"""

def load_attack_logs():
    """加载攻击日志"""
    logs = []
    log_file = '../logs/attacks.log'
    
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
    print("📊 钓鱼损失评估仪表板启动在端口 5888")
    print("访问 http://localhost:5888 查看损失评估")
    app.run(host='0.0.0.0', port=5888, debug=True)
