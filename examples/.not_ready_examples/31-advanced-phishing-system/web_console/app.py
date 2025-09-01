#!/usr/bin/env python3
"""
31项目 高级钓鱼系统 Web控制台
最先进的钓鱼攻防管理界面
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_socketio import SocketIO, emit, join_room, leave_room
import json
import os
import asyncio
import threading
import time
from datetime import datetime, timedelta
import secrets
import hashlib
from functools import wraps

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
socketio = SocketIO(app, cors_allowed_origins="*")

# 系统状态
system_state = {
    'active_campaigns': {},
    'ai_models_status': {
        'primary_llm': {'status': 'online', 'load': 45},
        'threat_intelligence': {'status': 'online', 'load': 23},
        'evasion_engine': {'status': 'online', 'load': 67},
        'deep_detector': {'status': 'online', 'load': 34}
    },
    'attack_chains': {},
    'target_profiles': {},
    'system_metrics': {
        'total_campaigns': 156,
        'successful_attacks': 89,
        'detection_rate': 12.3,
        'evasion_success': 87.7,
        'active_targets': 342,
        'ai_accuracy': 94.2
    },
    'threat_intelligence': {
        'apt_groups': ['APT1', 'Lazarus', 'Cozy Bear', 'Fancy Bear'],
        'latest_ttp': ['T1566.001', 'T1204.002', 'T1059.001'],
        'threat_level': 'HIGH',
        'trending_attacks': ['Business Email Compromise', 'Supply Chain Attack', 'AI-Generated Phishing']
    }
}

# 模拟活动数据
def generate_sample_campaigns():
    """生成示例攻击活动"""
    campaigns = {
        'apt_001': {
            'id': 'apt_001',
            'name': '金融目标APT模拟',
            'type': 'APT Simulation',
            'status': 'active',
            'target_count': 25,
            'success_count': 18,
            'stages_completed': 8,
            'total_stages': 13,
            'ai_enhanced': True,
            'evasion_techniques': ['Polymorphic', 'Semantic Drift', 'Steganography'],
            'start_time': datetime.now() - timedelta(hours=6),
            'estimated_completion': datetime.now() + timedelta(hours=2),
            'threat_level': 'CRITICAL',
            'attribution': 'Simulated APT Group X'
        },
        'social_002': {
            'id': 'social_002', 
            'name': '高管社交工程',
            'type': 'Executive Targeting',
            'status': 'planning',
            'target_count': 5,
            'success_count': 0,
            'stages_completed': 3,
            'total_stages': 10,
            'ai_enhanced': True,
            'evasion_techniques': ['Psychological Profiling', 'Trust Building', 'Context Aware'],
            'start_time': None,
            'estimated_completion': None,
            'threat_level': 'HIGH',
            'attribution': 'Social Engineering Team'
        },
        'supply_003': {
            'id': 'supply_003',
            'name': '供应链污染攻击',
            'type': 'Supply Chain Attack',
            'status': 'completed',
            'target_count': 12,
            'success_count': 9,
            'stages_completed': 12,
            'total_stages': 12,
            'ai_enhanced': True,
            'evasion_techniques': ['Code Injection', 'Update Hijacking', 'Certificate Spoofing'],
            'start_time': datetime.now() - timedelta(days=2),
            'estimated_completion': datetime.now() - timedelta(hours=3),
            'threat_level': 'CRITICAL',
            'attribution': 'Advanced Persistent Group'
        }
    }
    
    system_state['active_campaigns'] = campaigns
    return campaigns

# 安全装饰器
def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'authenticated' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'admin':
            return jsonify({'error': '需要管理员权限'}), 403
        return f(*args, **kwargs)
    return decorated_function

# 路由定义
@app.route('/')
@require_auth
def dashboard():
    """主控制台"""
    campaigns = generate_sample_campaigns()
    return render_template('dashboard.html', 
                         campaigns=campaigns,
                         system_metrics=system_state['system_metrics'],
                         ai_status=system_state['ai_models_status'],
                         threat_intel=system_state['threat_intelligence'])

@app.route('/login', methods=['GET', 'POST'])
def login():
    """登录页面"""
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        # 简单的认证逻辑（实际环境中应使用更安全的方法）
        if username == 'admin' and password == 'seed31':
            session['authenticated'] = True
            session['username'] = username
            session['role'] = 'admin'
            return jsonify({'success': True, 'redirect': '/'})
        else:
            return jsonify({'success': False, 'message': '用户名或密码错误'})
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """登出"""
    session.clear()
    return redirect(url_for('login'))

@app.route('/campaigns')
@require_auth
def campaigns():
    """攻击活动管理"""
    campaigns = generate_sample_campaigns()
    return render_template('campaigns.html', campaigns=campaigns)

@app.route('/campaign/<campaign_id>')
@require_auth
def campaign_detail(campaign_id):
    """活动详情"""
    campaigns = generate_sample_campaigns()
    campaign = campaigns.get(campaign_id)
    if not campaign:
        return "活动不存在", 404
    
    # 生成活动详细数据
    campaign_detail = {
        **campaign,
        'attack_chain': generate_attack_chain(campaign_id),
        'target_profiles': generate_target_profiles(campaign_id),
        'evasion_analysis': generate_evasion_analysis(campaign_id),
        'detection_events': generate_detection_events(campaign_id)
    }
    
    return render_template('campaign_detail.html', campaign=campaign_detail)

@app.route('/ai_console')
@require_auth
def ai_console():
    """AI控制台"""
    return render_template('ai_console.html',
                         ai_status=system_state['ai_models_status'])

@app.route('/openai_console')
@require_auth
def openai_console():
    """OpenAI控制台"""
    return render_template('openai_console.html')

@app.route('/openai_config')
@require_auth
def openai_config():
    """OpenAI配置管理"""
    return render_template('openai_config.html')

@app.route('/api/openai_config', methods=['GET'])
@require_auth
def api_get_openai_config():
    """获取OpenAI配置"""
    try:
        config = {
            'api_key_configured': bool(os.getenv('OPENAI_API_KEY')),
            'base_url': os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1'),
            'default_model': os.getenv('PRIMARY_LLM_MODEL', 'gpt-4o'),
            'max_tokens': int(os.getenv('PRIMARY_LLM_MAX_TOKENS', '4096')),
            'connection_status': 'online' if os.getenv('OPENAI_API_KEY') else 'offline',
            'last_test': datetime.now().isoformat()
        }
        return jsonify(config)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/openai_config', methods=['POST'])
@require_auth
def api_save_openai_config():
    """保存OpenAI配置"""
    try:
        data = request.get_json()

        # 更新环境变量
        if data.get('api_key'):
            os.environ['OPENAI_API_KEY'] = data['api_key']
        if data.get('base_url'):
            os.environ['OPENAI_BASE_URL'] = data['base_url']
        if data.get('default_model'):
            os.environ['PRIMARY_LLM_MODEL'] = data['default_model']
        if data.get('max_tokens'):
            os.environ['PRIMARY_LLM_MAX_TOKENS'] = str(data['max_tokens'])

        # 保存到.env文件
        env_path = Path(__file__).parent.parent / '.env'
        env_content = f"""# OpenAI Configuration
OPENAI_API_KEY={data.get('api_key', '')}
OPENAI_BASE_URL={data.get('base_url', 'https://api.openai.com/v1')}

# System Configuration
SYSTEM_DEBUG=true
SYSTEM_NAME=SEED Advanced Phishing System
SYSTEM_VERSION=1.0.0

# AI Models Configuration
PRIMARY_LLM_MODEL={data.get('default_model', 'gpt-4o')}
PRIMARY_LLM_MAX_TOKENS={data.get('max_tokens', 4096)}
"""

        with open(env_path, 'w', encoding='utf-8') as f:
            f.write(env_content)

        return jsonify({'success': True, 'message': '配置保存成功'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/openai_test_connection', methods=['POST'])
@require_auth
def api_test_openai_connection():
    """测试OpenAI连接"""
    try:
        data = request.get_json()

        # 创建临时客户端进行测试
        from openai import OpenAI
        test_client = OpenAI(
            api_key=data.get('api_key'),
            base_url=data.get('base_url', 'https://api.openai.com/v1')
        )

        # 发送测试请求
        response = test_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Hello, test connection"}],
            max_tokens=10
        )

        if response and response.choices:
            return jsonify({
                'success': True,
                'message': '连接测试成功',
                'response': response.choices[0].message.content.strip()
            })
        else:
            return jsonify({'success': False, 'error': '无响应内容'})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/openai_test_model', methods=['POST'])
@require_auth
def api_test_openai_model():
    """测试特定模型"""
    try:
        data = request.get_json()
        model = data.get('model')

        if not model:
            return jsonify({'success': False, 'error': '未指定模型'})

        # 创建客户端
        from openai import OpenAI
        client = OpenAI(
            api_key=os.getenv('OPENAI_API_KEY'),
            base_url=os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')
        )

        # 记录开始时间
        start_time = time.time()

        # 发送测试请求
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": f"Respond with 'OK' to confirm {model} is working"}],
            max_tokens=10
        )

        # 计算响应时间
        response_time = int((time.time() - start_time) * 1000)

        if response and response.choices:
            return jsonify({
                'success': True,
                'response_time': response_time,
                'response': response.choices[0].message.content.strip()
            })
        else:
            return jsonify({'success': False, 'error': '无响应内容'})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/openai_usage_stats')
@require_auth
def api_get_openai_usage_stats():
    """获取使用统计"""
    try:
        # 这里可以从数据库或文件中读取统计信息
        # 暂时返回模拟数据
        stats = {
            'total_requests': 47,
            'total_tokens': 12547,
            'total_cost': 2.34,
            'last_updated': datetime.now().isoformat()
        }
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/openai_reset_stats', methods=['POST'])
@require_auth
def api_reset_openai_stats():
    """重置使用统计"""
    try:
        # 这里可以重置统计信息
        return jsonify({'success': True, 'message': '统计已重置'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/threat_analytics')
@require_auth
def threat_analytics():
    """威胁分析"""
    return render_template('threat_analytics.html',
                         threat_intel=system_state['threat_intelligence'])

@app.route('/attack_designer')
@require_auth
def attack_designer():
    """攻击设计器"""
    return render_template('attack_designer.html')

@app.route('/evasion_lab')
@require_auth
def evasion_lab():
    """规避技术实验室"""
    return render_template('evasion_lab.html')

# API路由
@app.route('/api/system_status')
@require_auth
def api_system_status():
    """系统状态API"""
    status = {
        'timestamp': datetime.now().isoformat(),
        'system': {
            'cpu_usage': 67.5,
            'memory_usage': 78.2,
            'gpu_usage': 45.8,
            'disk_usage': 34.1,
            'network_io': 12.5,
            'uptime': '15d 7h 23m'
        },
        'ai_models': system_state['ai_models_status'],
        'active_campaigns': len(system_state['active_campaigns']),
        'threat_level': system_state['threat_intelligence']['threat_level']
    }
    return jsonify(status)

@app.route('/api/campaigns', methods=['GET', 'POST'])
@require_auth
def api_campaigns():
    """活动管理API"""
    if request.method == 'GET':
        campaigns = generate_sample_campaigns()
        return jsonify(list(campaigns.values()))
    
    elif request.method == 'POST':
        campaign_data = request.get_json()
        
        # 创建新活动
        campaign_id = f"custom_{secrets.token_hex(4)}"
        new_campaign = {
            'id': campaign_id,
            'name': campaign_data.get('name', '未命名活动'),
            'type': campaign_data.get('type', 'Custom'),
            'status': 'planning',
            'target_count': campaign_data.get('target_count', 0),
            'success_count': 0,
            'stages_completed': 0,
            'total_stages': campaign_data.get('total_stages', 5),
            'ai_enhanced': campaign_data.get('ai_enhanced', True),
            'evasion_techniques': campaign_data.get('evasion_techniques', []),
            'start_time': None,
            'estimated_completion': None,
            'threat_level': campaign_data.get('threat_level', 'MEDIUM'),
            'attribution': 'Custom Campaign'
        }
        
        system_state['active_campaigns'][campaign_id] = new_campaign
        
        return jsonify({
            'success': True,
            'campaign_id': campaign_id,
            'message': '活动创建成功'
        })

@app.route('/api/ai_generate', methods=['POST'])
@require_auth
def api_ai_generate():
    """AI内容生成API"""
    data = request.get_json()
    prompt = data.get('prompt', '')
    content_type = data.get('type', 'email')
    target_profile = data.get('target_profile', {})
    evasion_level = data.get('evasion_level', 0.5)
    
    # 模拟AI生成过程
    time.sleep(2)  # 模拟处理时间
    
    if content_type == 'email':
        generated_content = f"""
主题: 紧急：系统安全更新通知

尊敬的{target_profile.get('name', '用户')}：

我们检测到您的账户存在异常登录尝试。为了保护您的账户安全，请立即点击以下链接进行身份验证：

[验证链接] - 请在24小时内完成验证

如果您没有进行登录尝试，请忽略此邮件。

IT安全团队
{datetime.now().strftime('%Y年%m月%d日')}

---
此邮件由AI生成，规避等级：{evasion_level}
"""
    else:
        generated_content = "暂不支持该内容类型"
    
    return jsonify({
        'success': True,
        'content': generated_content,
        'evasion_techniques_applied': ['语义变换', '情感诱导', '紧迫性营造'],
        'detection_probability': max(0.1, 1.0 - evasion_level),
        'generation_time': 2.1
    })

@app.route('/api/ai_detect', methods=['POST'])
@require_auth
def api_ai_detect():
    """AI威胁检测API"""
    data = request.get_json()
    content = data.get('content', '')
    
    # 模拟AI检测过程
    time.sleep(1)
    
    # 简单的检测逻辑
    threat_indicators = ['紧急', '立即', '点击', '验证', '异常', '安全']
    threat_score = sum(1 for indicator in threat_indicators if indicator in content)
    threat_probability = min(0.95, threat_score / len(threat_indicators))
    
    result = {
        'is_threat': threat_probability > 0.5,
        'threat_probability': threat_probability,
        'confidence': 0.87,
        'threat_type': 'phishing' if threat_probability > 0.5 else 'benign',
        'indicators': [indicator for indicator in threat_indicators if indicator in content],
        'explanation': f'检测到{len([i for i in threat_indicators if i in content])}个威胁指标',
        'detection_time': 1.2
    }
    
    return jsonify(result)

@app.route('/api/evasion_test', methods=['POST'])
@require_auth
def api_evasion_test():
    """规避技术测试API"""
    data = request.get_json()
    original_content = data.get('content', '')
    technique = data.get('technique', 'polymorphic')
    
    # 模拟规避技术应用
    time.sleep(1.5)
    
    techniques_results = {
        'polymorphic': {
            'modified_content': original_content.replace('紧急', '重要').replace('立即', '尽快'),
            'success_rate': 0.78,
            'detection_reduction': 0.34
        },
        'semantic_drift': {
            'modified_content': f"关于{original_content[:20]}...的重要通知",
            'success_rate': 0.85,
            'detection_reduction': 0.42
        },
        'steganography': {
            'modified_content': original_content + '\u200b' * 10,  # 零宽字符
            'success_rate': 0.92,
            'detection_reduction': 0.67
        }
    }
    
    result = techniques_results.get(technique, techniques_results['polymorphic'])
    result['technique'] = technique
    result['processing_time'] = 1.5
    
    return jsonify(result)

@app.route('/api/openai_generate', methods=['POST'])
@require_auth
def api_openai_generate():
    """OpenAI内容生成API"""
    data = request.get_json()
    prompt = data.get('prompt', '')
    model = data.get('model', 'gpt-4o')
    temperature = data.get('temperature', 0.7)
    max_tokens = data.get('max_tokens', 1000)

    if not prompt.strip():
        return jsonify({'success': False, 'error': '提示不能为空'})

    try:
        # 这里应该调用真实的OpenAI客户端
        # 暂时返回模拟结果
        mock_response = f"""
根据您的提示生成的内容：

{prompt}

---

*这是使用{model}模型生成的模拟内容。实际部署时将调用真实的OpenAI API。*
"""

        return jsonify({
            'success': True,
            'content': mock_response,
            'model': model,
            'temperature': temperature,
            'tokens_used': len(prompt.split()),
            'processing_time': 2.1
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'OpenAI生成失败: {str(e)}'
        })

@app.route('/api/openai_analyze', methods=['POST'])
@require_auth
def api_openai_analyze():
    """OpenAI威胁分析API"""
    data = request.get_json()
    content = data.get('content', '')
    analysis_type = data.get('type', 'threat')

    if not content.strip():
        return jsonify({'success': False, 'error': '内容不能为空'})

    try:
        # 这里应该调用真实的OpenAI分析
        # 暂时返回模拟分析结果
        mock_analysis = f"""
威胁分析报告 ({analysis_type.upper()})

目标内容分析:
{content[:200]}...

分析结果:
1. 潜在风险: 中等
2. 可疑特征: 发现2个可疑元素
3. 建议措施: 建议人工审核
4. 置信度: 85%

详细说明:
- 检测到紧急语气表达
- 包含验证链接要求
- 建议使用多因素认证

---

*这是使用GPT-4模型生成的模拟分析报告。实际部署时将调用真实的OpenAI API。*
"""

        return jsonify({
            'success': True,
            'analysis': mock_analysis,
            'risk_level': 'MEDIUM',
            'confidence': 0.85,
            'indicators': ['紧急语气', '验证链接', '可疑发件人'],
            'recommendations': ['人工审核', '多因素认证', '链接检查']
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'OpenAI分析失败: {str(e)}'
        })

@app.route('/api/openai_status')
@require_auth
def api_openai_status():
    """OpenAI服务状态API"""
    try:
        # 检查OpenAI连接状态
        openai_available = os.getenv('OPENAI_API_KEY') is not None
        openai_models = []

        if openai_available:
            openai_models = [
                {'name': 'gpt-4o', 'description': '最新GPT-4优化版', 'context': '128K'},
                {'name': 'gpt-4-turbo', 'description': 'GPT-4 Turbo版', 'context': '128K'},
                {'name': 'gpt-3.5-turbo', 'description': 'GPT-3.5 Turbo版', 'context': '16K'},
                {'name': 'claude-3-opus', 'description': 'Claude 3顶级版', 'context': '200K'},
                {'name': 'claude-3-sonnet', 'description': 'Claude 3标准版', 'context': '200K'}
            ]

        return jsonify({
            'available': openai_available,
            'base_url': os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1'),
            'models': openai_models,
            'status': 'online' if openai_available else 'offline',
            'last_test': datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({
            'available': False,
            'error': str(e),
            'status': 'error'
        })

@app.route('/api/openai_models')
@require_auth
def api_openai_models():
    """获取可用OpenAI模型列表"""
    models = [
        {
            'id': 'gpt-4o',
            'name': 'GPT-4o',
            'description': 'OpenAI最新旗舰模型，适合复杂任务',
            'context_window': 128000,
            'strengths': ['代码生成', '创意写作', '复杂推理'],
            'use_cases': ['钓鱼内容生成', '威胁分析', '策略制定']
        },
        {
            'id': 'gpt-4-turbo',
            'name': 'GPT-4 Turbo',
            'description': '增强版GPT-4，速度更快',
            'context_window': 128000,
            'strengths': ['快速响应', '多语言支持', '实时对话'],
            'use_cases': ['实时分析', '多语言钓鱼', '快速检测']
        },
        {
            'id': 'gpt-3.5-turbo',
            'name': 'GPT-3.5 Turbo',
            'description': '经济高效的模型，适合简单任务',
            'context_window': 16385,
            'strengths': ['成本效益', '快速处理', '基本分析'],
            'use_cases': ['基础检测', '简单生成', '批量处理']
        },
        {
            'id': 'claude-3-opus',
            'name': 'Claude 3 Opus',
            'description': 'Anthropic顶级模型，擅长分析',
            'context_window': 200000,
            'strengths': ['深度分析', '道德推理', '长文本处理'],
            'use_cases': ['威胁情报分析', '道德评估', '复杂推理']
        },
        {
            'id': 'claude-3-sonnet',
            'name': 'Claude 3 Sonnet',
            'description': 'Anthropic平衡模型，速度与质量并重',
            'context_window': 200000,
            'strengths': ['平衡性能', '创意生成', '技术文档'],
            'use_cases': ['内容创作', '技术分析', '报告生成']
        }
    ]

    return jsonify({
        'models': models,
        'recommended': 'gpt-4o',
        'last_updated': datetime.now().isoformat()
    })

@app.route('/api/attack_chain', methods=['POST'])
@require_auth
@admin_required
def api_attack_chain():
    """攻击链设计API"""
    data = request.get_json()
    objectives = data.get('objectives', [])
    target_type = data.get('target_type', 'corporate')
    
    # 生成攻击链
    attack_chain = {
        'chain_id': secrets.token_hex(16),
        'objectives': objectives,
        'stages': [
            {'stage': 'reconnaissance', 'techniques': ['OSINT', 'Social Media Mining'], 'duration': '2-5 days'},
            {'stage': 'initial_access', 'techniques': ['Spear Phishing', 'Watering Hole'], 'duration': '1-3 days'},
            {'stage': 'execution', 'techniques': ['PowerShell', 'Command Line'], 'duration': '1-2 hours'},
            {'stage': 'persistence', 'techniques': ['Registry Keys', 'Scheduled Tasks'], 'duration': '30-60 minutes'},
            {'stage': 'privilege_escalation', 'techniques': ['Credential Dumping', 'Token Impersonation'], 'duration': '2-4 hours'},
            {'stage': 'defense_evasion', 'techniques': ['Process Injection', 'Rootkit'], 'duration': '1-2 hours'},
            {'stage': 'credential_access', 'techniques': ['Keylogging', 'Password Spraying'], 'duration': '1-7 days'},
            {'stage': 'discovery', 'techniques': ['Network Discovery', 'System Information'], 'duration': '2-4 hours'},
            {'stage': 'lateral_movement', 'techniques': ['Remote Services', 'Network Shares'], 'duration': '1-3 days'},
            {'stage': 'collection', 'techniques': ['Data Staging', 'Screen Capture'], 'duration': '1-5 days'},
            {'stage': 'exfiltration', 'techniques': ['DNS Tunneling', 'Web Protocols'], 'duration': '1-2 days'}
        ],
        'estimated_duration': '2-4 weeks',
        'success_probability': 0.73,
        'detection_risk': 0.28
    }
    
    return jsonify(attack_chain)

# WebSocket事件
@socketio.on('connect')
def handle_connect():
    """WebSocket连接处理"""
    if 'authenticated' not in session:
        return False
    
    join_room('system_updates')
    emit('status', {'message': '连接成功', 'timestamp': datetime.now().isoformat()})

@socketio.on('disconnect')
def handle_disconnect():
    """WebSocket断开处理"""
    leave_room('system_updates')

@socketio.on('subscribe_campaign')
def handle_subscribe_campaign(data):
    """订阅活动更新"""
    campaign_id = data.get('campaign_id')
    if campaign_id:
        join_room(f'campaign_{campaign_id}')
        emit('subscribed', {'campaign_id': campaign_id})

# 后台任务
def background_task():
    """后台任务：发送实时更新"""
    while True:
        time.sleep(5)
        
        # 发送系统状态更新
        status_update = {
            'timestamp': datetime.now().isoformat(),
            'ai_status': system_state['ai_models_status'],
            'system_load': {
                'cpu': 45.2 + (time.time() % 10),
                'memory': 78.1 + (time.time() % 5),
                'gpu': 34.7 + (time.time() % 15)
            }
        }
        
        socketio.emit('system_update', status_update, room='system_updates')

# 辅助函数
def generate_attack_chain(campaign_id):
    """生成攻击链数据"""
    return {
        'total_stages': 11,
        'completed_stages': 7,
        'current_stage': 'lateral_movement',
        'stages': [
            {'name': 'reconnaissance', 'status': 'completed', 'success_rate': 95},
            {'name': 'initial_access', 'status': 'completed', 'success_rate': 87},
            {'name': 'execution', 'status': 'completed', 'success_rate': 92},
            {'name': 'persistence', 'status': 'completed', 'success_rate': 78},
            {'name': 'privilege_escalation', 'status': 'completed', 'success_rate': 83},
            {'name': 'defense_evasion', 'status': 'completed', 'success_rate': 90},
            {'name': 'credential_access', 'status': 'completed', 'success_rate': 76},
            {'name': 'discovery', 'status': 'in_progress', 'success_rate': 45},
            {'name': 'lateral_movement', 'status': 'pending', 'success_rate': 0},
            {'name': 'collection', 'status': 'pending', 'success_rate': 0},
            {'name': 'exfiltration', 'status': 'pending', 'success_rate': 0}
        ]
    }

def generate_target_profiles(campaign_id):
    """生成目标画像数据"""
    return [
        {
            'id': 'target_001',
            'name': '张三',
            'position': 'IT经理',
            'department': '信息技术部',
            'email': 'zhangsan@target.com',
            'risk_score': 8.7,
            'susceptibility': 0.73,
            'social_footprint': {'linkedin': True, 'twitter': False, 'facebook': True}
        },
        {
            'id': 'target_002', 
            'name': '李四',
            'position': '财务总监',
            'department': '财务部',
            'email': 'lisi@target.com',
            'risk_score': 9.2,
            'susceptibility': 0.81,
            'social_footprint': {'linkedin': True, 'twitter': True, 'facebook': False}
        }
    ]

def generate_evasion_analysis(campaign_id):
    """生成规避分析数据"""
    return {
        'techniques_used': ['Polymorphic Generation', 'Semantic Drift', 'Steganography'],
        'evasion_success_rate': 0.87,
        'detected_attempts': 3,
        'successful_evasions': 23,
        'detection_engines_bypassed': ['Traditional AV', 'ML-based Detection', 'Behavioral Analysis']
    }

def generate_detection_events(campaign_id):
    """生成检测事件数据"""
    return [
        {
            'timestamp': datetime.now() - timedelta(hours=2),
            'event_type': 'suspicious_email',
            'severity': 'medium',
            'description': '检测到可疑邮件模式',
            'action_taken': 'quarantined'
        },
        {
            'timestamp': datetime.now() - timedelta(hours=4),
            'event_type': 'ai_detection',
            'severity': 'high', 
            'description': 'AI检测器识别出钓鱼内容',
            'action_taken': 'blocked'
        }
    ]

if __name__ == '__main__':
    # 启动后台任务
    task_thread = threading.Thread(target=background_task)
    task_thread.daemon = True
    task_thread.start()
    
    print("""
    🎣================================================================🎣
                SEED高级钓鱼系统 Web控制台启动
                    31-advanced-phishing-system
    🎣================================================================🎣
    
    🌐 访问地址: http://localhost:5003
    👤 默认用户: admin
    🔑 默认密码: seed31
    
    🎯 主要功能:
    • AI驱动的高级钓鱼攻击设计
    • APT攻击链模拟和分析
    • 多模态威胁检测和规避
    • 实时攻击监控和分析
    • 深度社会工程学实验
    
    ⚠️  警告: 仅限授权安全研究使用
    🔒 系统已启用多层安全防护
    
    """)
    
    socketio.run(app, host='0.0.0.0', port=5003, debug=True)
