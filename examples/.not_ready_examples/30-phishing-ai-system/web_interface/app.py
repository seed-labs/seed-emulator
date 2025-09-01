#!/usr/bin/env python3
"""
SEED 钓鱼攻击与AI防护系统 - Web管理界面
30项目的统一控制台和监控面板
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import requests
import json
import os
import subprocess
from datetime import datetime
import sqlite3

app = Flask(__name__)
app.secret_key = 'seed-phishing-ai-30'

# 配置
OLLAMA_API = "http://ollama:11434"
GOPHISH_API = "http://gophish:3333/api"
PHISHING_DETECTOR_API = "http://phishing-detector:8000"
IMAGE_ANALYZER_API = "http://image-analyzer:8000"
BEHAVIOR_ANALYZER_API = "http://behavior-analyzer:8000"

class SeedPhishingSystem:
    """SEED钓鱼系统管理器"""
    
    def __init__(self):
        self.init_database()
    
    def init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect('seed_phishing.db')
        cursor = conn.cursor()
        
        # 创建攻击活动表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS campaigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                targets_count INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0,
                ai_enhanced BOOLEAN DEFAULT FALSE
            )
        ''')
        
        # 创建检测记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS detections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                detection_type TEXT NOT NULL,
                content TEXT,
                risk_score REAL,
                detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ai_model TEXT,
                result TEXT
            )
        ''')
        
        # 创建用户行为表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_behaviors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                action TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                risk_level TEXT,
                details TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def call_ai_api(self, service_url, endpoint, data):
        """调用AI服务API"""
        try:
            response = requests.post(f"{service_url}/{endpoint}", json=data, timeout=30)
            return response.json() if response.status_code == 200 else None
        except Exception as e:
            print(f"API调用失败: {e}")
            return None
    
    def generate_phishing_email(self, target_profile, scenario):
        """生成钓鱼邮件"""
        prompt = f"""
        创建一个针对以下目标的钓鱼邮件:
        目标信息: {target_profile}
        攻击场景: {scenario}
        
        要求:
        1. 邮件内容要具有说服力和紧迫感
        2. 使用适当的社会工程学技巧
        3. 包含可信的发件人信息
        4. 添加钓鱼链接或附件
        
        请生成邮件主题、发件人、正文内容。
        """
        
        ollama_data = {
            "model": "qwen2:7b",
            "prompt": prompt,
            "stream": False
        }
        
        result = self.call_ai_api(OLLAMA_API, "api/generate", ollama_data)
        return result.get('response') if result else "AI生成失败"
    
    def detect_phishing_email(self, email_content):
        """检测钓鱼邮件"""
        detection_data = {
            "content": email_content,
            "features": ["sender", "links", "urgency", "grammar"]
        }
        
        result = self.call_ai_api(PHISHING_DETECTOR_API, "detect", detection_data)
        
        # 记录检测结果
        if result:
            conn = sqlite3.connect('seed_phishing.db')
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO detections (detection_type, content, risk_score, ai_model, result)
                VALUES (?, ?, ?, ?, ?)
            ''', ('email', email_content[:500], result.get('risk_score', 0), 'phishing_detector', json.dumps(result)))
            conn.commit()
            conn.close()
        
        return result
    
    def analyze_user_behavior(self, user_actions):
        """分析用户行为"""
        behavior_data = {
            "actions": user_actions,
            "features": ["frequency", "timing", "sequence", "anomaly"]
        }
        
        result = self.call_ai_api(BEHAVIOR_ANALYZER_API, "analyze", behavior_data)
        return result
    
    def get_system_stats(self):
        """获取系统统计信息"""
        conn = sqlite3.connect('seed_phishing.db')
        cursor = conn.cursor()
        
        # 获取活动统计
        cursor.execute('SELECT COUNT(*) FROM campaigns')
        total_campaigns = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM campaigns WHERE status = "active"')
        active_campaigns = cursor.fetchone()[0]
        
        # 获取检测统计
        cursor.execute('SELECT COUNT(*) FROM detections WHERE detection_type = "email"')
        email_detections = cursor.fetchone()[0]
        
        cursor.execute('SELECT AVG(risk_score) FROM detections WHERE risk_score > 0')
        avg_risk_score = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return {
            'total_campaigns': total_campaigns,
            'active_campaigns': active_campaigns,
            'email_detections': email_detections,
            'avg_risk_score': round(avg_risk_score, 2),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

# 初始化系统
system = SeedPhishingSystem()

@app.route('/')
def dashboard():
    """主仪表板"""
    stats = system.get_system_stats()
    return render_template('dashboard.html', stats=stats)

@app.route('/phishing_generator')
def phishing_generator():
    """钓鱼邮件生成器"""
    return render_template('phishing_generator.html')

@app.route('/api/generate_phishing', methods=['POST'])
def api_generate_phishing():
    """API: 生成钓鱼邮件"""
    data = request.get_json()
    
    target_profile = data.get('target_profile', '')
    scenario = data.get('scenario', 'general')
    
    generated_email = system.generate_phishing_email(target_profile, scenario)
    
    return jsonify({
        'success': True,
        'email_content': generated_email,
        'generated_at': datetime.now().isoformat()
    })

@app.route('/detector')
def detector():
    """钓鱼检测器"""
    return render_template('detector.html')

@app.route('/api/detect_phishing', methods=['POST'])
def api_detect_phishing():
    """API: 检测钓鱼邮件"""
    data = request.get_json()
    
    email_content = data.get('content', '')
    
    if not email_content:
        return jsonify({'success': False, 'error': '邮件内容不能为空'})
    
    detection_result = system.detect_phishing_email(email_content)
    
    if detection_result:
        return jsonify({
            'success': True,
            'detection_result': detection_result
        })
    else:
        return jsonify({
            'success': False,
            'error': 'AI检测服务不可用'
        })

@app.route('/campaigns')
def campaigns():
    """攻击活动管理"""
    conn = sqlite3.connect('seed_phishing.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, name, type, status, created_at, targets_count, success_count, ai_enhanced 
        FROM campaigns ORDER BY created_at DESC
    ''')
    
    campaigns_data = []
    for row in cursor.fetchall():
        campaigns_data.append({
            'id': row[0],
            'name': row[1],
            'type': row[2],
            'status': row[3],
            'created_at': row[4],
            'targets_count': row[5],
            'success_count': row[6],
            'ai_enhanced': row[7],
            'success_rate': f"{(row[6]/row[5]*100):.1f}%" if row[5] > 0 else "0%"
        })
    
    conn.close()
    return render_template('campaigns.html', campaigns=campaigns_data)

@app.route('/api/create_campaign', methods=['POST'])
def api_create_campaign():
    """API: 创建攻击活动"""
    data = request.get_json()
    
    conn = sqlite3.connect('seed_phishing.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO campaigns (name, type, status, targets_count, ai_enhanced)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        data.get('name'),
        data.get('type'), 
        'created',
        data.get('targets_count', 0),
        data.get('ai_enhanced', False)
    ))
    
    conn.commit()
    campaign_id = cursor.lastrowid
    conn.close()
    
    return jsonify({
        'success': True,
        'campaign_id': campaign_id,
        'message': '攻击活动创建成功'
    })

@app.route('/behavior_analysis')
def behavior_analysis():
    """用户行为分析"""
    return render_template('behavior_analysis.html')

@app.route('/api/analyze_behavior', methods=['POST'])
def api_analyze_behavior():
    """API: 分析用户行为"""
    data = request.get_json()
    
    user_actions = data.get('actions', [])
    
    analysis_result = system.analyze_user_behavior(user_actions)
    
    return jsonify({
        'success': True,
        'analysis_result': analysis_result
    })

@app.route('/ai_models')
def ai_models():
    """AI模型管理"""
    # 检查AI服务状态
    ai_services = {
        'ollama': check_service_health(OLLAMA_API),
        'phishing_detector': check_service_health(PHISHING_DETECTOR_API),
        'image_analyzer': check_service_health(IMAGE_ANALYZER_API),
        'behavior_analyzer': check_service_health(BEHAVIOR_ANALYZER_API)
    }
    
    return render_template('ai_models.html', ai_services=ai_services)

def check_service_health(service_url):
    """检查服务健康状态"""
    try:
        response = requests.get(f"{service_url}/health", timeout=5)
        return {
            'status': 'healthy' if response.status_code == 200 else 'unhealthy',
            'response_time': response.elapsed.total_seconds()
        }
    except:
        return {
            'status': 'unreachable',
            'response_time': None
        }

@app.route('/attack_scenarios')
def attack_scenarios():
    """攻击场景管理"""
    scenarios = [
        {
            'name': 'CEO诈骗攻击',
            'type': 'social_engineering',
            'difficulty': 4,
            'ai_enhanced': True,
            'description': '模拟CEO发送的紧急转账请求邮件'
        },
        {
            'name': '供应链攻击',
            'type': 'supply_chain',
            'difficulty': 5,
            'ai_enhanced': True,
            'description': '通过伪造的软件更新进行攻击'
        },
        {
            'name': 'HR招聘诈骗',
            'type': 'credential_harvesting',
            'difficulty': 3,
            'ai_enhanced': True,
            'description': '伪造招聘网站收集个人信息'
        },
        {
            'name': '技术支持诈骗',
            'type': 'technical_support_scam',
            'difficulty': 2,
            'ai_enhanced': True,
            'description': '虚假的安全警报要求用户操作'
        },
        {
            'name': '内部威胁模拟',
            'type': 'insider_threat',
            'difficulty': 4,
            'ai_enhanced': True,
            'description': '模拟内部员工的恶意行为'
        },
        {
            'name': '金融钓鱼攻击',
            'type': 'financial_fraud',
            'difficulty': 4,
            'ai_enhanced': True,
            'description': '伪造银行网站窃取登录凭据'
        }
    ]
    
    return render_template('attack_scenarios.html', scenarios=scenarios)

@app.route('/api/system_status')
def api_system_status():
    """API: 系统状态"""
    stats = system.get_system_stats()
    
    # 添加AI服务状态
    ai_status = {
        'ollama': check_service_health(OLLAMA_API),
        'phishing_detector': check_service_health(PHISHING_DETECTOR_API),
        'image_analyzer': check_service_health(IMAGE_ANALYZER_API),
        'behavior_analyzer': check_service_health(BEHAVIOR_ANALYZER_API)
    }
    
    healthy_services = sum(1 for service in ai_status.values() if service['status'] == 'healthy')
    
    return jsonify({
        'success': True,
        'stats': stats,
        'ai_services': ai_status,
        'ai_health': f"{healthy_services}/4"
    })

if __name__ == '__main__':
    print("""
    ╭─────────────────────────────────────────────────────────────╮
    │           SEED 钓鱼攻击与AI防护系统 Web界面                  │
    │                30-phishing-ai-system                       │
    ╰─────────────────────────────────────────────────────────────╯
    
    🌐 访问地址: http://localhost:5000
    
    🎯 功能模块:
    📊 系统仪表板 - 实时监控和统计
    🎣 钓鱼生成器 - AI驱动的钓鱼邮件生成
    🛡️ 安全检测器 - 智能钓鱼邮件检测
    📈 行为分析 - 用户行为异常检测
    🎭 攻击场景 - 预设攻击场景管理
    🤖 AI模型 - AI服务状态和管理
    
    🔧 AI服务集成:
    - Ollama LLM (Qwen2-7B)
    - 钓鱼检测AI (BERT)
    - 图像分析AI (CLIP)
    - 行为分析AI (Isolation Forest)
    
    ⚠️ 仅用于授权的安全教育和研究
    """)
    
    app.run(host='0.0.0.0', port=5000, debug=True)
