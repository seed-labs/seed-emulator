#!/usr/bin/env python3
"""
SEED 钓鱼攻击与AI防护系统 (30-phishing-ai-system)
完整的钓鱼攻击实验平台，集成AI驱动的攻击生成和防护检测
"""

import sys
import os
from seedemu import *

def create_enterprise_network(emu):
    """创建企业网络环境"""
    
    base = Base()
    
    # 创建Internet Exchanges
    ix_public = base.createInternetExchange(100)   # 公网IX
    ix_enterprise = base.createInternetExchange(101)  # 企业IX
    ix_cloud = base.createInternetExchange(102)    # 云服务IX
    
    ix_public.getPeeringLan().setDisplayName('Public-Internet-IX')
    ix_enterprise.getPeeringLan().setDisplayName('Enterprise-IX')
    ix_cloud.getPeeringLan().setDisplayName('Cloud-Services-IX')
    
    # 创建ISP
    Makers.makeTransitAs(base, 2, [100, 101, 102], [(100, 101), (101, 102), (100, 102)])
    
    # === 企业网络结构 ===
    
    # AS-200: DMZ区域 (对外服务)
    Makers.makeStubAsWithHosts(emu, base, 200, 101, 4)
    
    # AS-201: 办公网络 (员工工作站)
    Makers.makeStubAsWithHosts(emu, base, 201, 101, 8) 
    
    # AS-202: 服务器网络 (内部系统)
    Makers.makeStubAsWithHosts(emu, base, 202, 101, 6)
    
    # AS-203: 管理网络 (网络设备)
    Makers.makeStubAsWithHosts(emu, base, 203, 101, 3)
    
    # AS-204: 隔离网络 (敏感系统)
    Makers.makeStubAsWithHosts(emu, base, 204, 101, 4)
    
    # === 攻击者基础设施 ===

    # AS-205: C&C服务器网络
    Makers.makeStubAsWithHosts(emu, base, 205, 100, 3)

    # AS-206: 钓鱼基础设施
    Makers.makeStubAsWithHosts(emu, base, 206, 100, 5)

    # AS-207: 代理和匿名化网络
    Makers.makeStubAsWithHosts(emu, base, 207, 100, 4)
    
    # === 云服务提供商 ===
    
    # AS-210: 公有云服务 (AWS/Azure模拟)
    Makers.makeStubAsWithHosts(emu, base, 210, 102, 6)
    
    # AS-211: AI服务提供商
    Makers.makeStubAsWithHosts(emu, base, 211, 102, 4)
    
    # === 外部用户网络 ===
    
    # AS-220: 普通用户网络
    Makers.makeStubAsWithHosts(emu, base, 220, 100, 10)

    # AS-221: 移动用户网络
    Makers.makeStubAsWithHosts(emu, base, 221, 100, 8)
    
    return base

def configure_ai_services(emu):
    """配置AI服务组件"""
    
    print("🧠 配置AI服务组件...")
    
    # AI服务将在Docker Compose中定义
    ai_services = {
        'ollama_llm': {
            'description': '本地大语言模型服务',
            'models': ['qwen2:7b', 'chatglm3:6b'],
            'ports': ['11434:11434']
        },
        'phishing_detector': {
            'description': '钓鱼邮件检测AI',
            'model': 'bert-base-uncased',
            'ports': ['8001:8000']
        },
        'image_analyzer': {
            'description': '图像相似度检测',
            'model': 'clip-vit-base-patch32',
            'ports': ['8002:8000']
        },
        'behavior_analyzer': {
            'description': '用户行为分析AI',
            'model': 'isolation-forest',
            'ports': ['8003:8000']
        }
    }
    
    return ai_services

def configure_phishing_infrastructure(emu):
    """配置钓鱼攻击基础设施"""
    
    print("🎣 配置钓鱼攻击基础设施...")
    
    # Gophish服务器配置
    gophish_config = {
        'server_url': 'https://phishing-control.local:3333',
        'api_key': 'auto-generated',
        'landing_pages': [
            'fake-office365.html',
            'fake-gmail.html', 
            'fake-company-portal.html',
            'fake-bank-login.html'
        ],
        'email_templates': [
            'ceo-fraud.html',
            'it-support.html',
            'hr-notification.html',
            'security-alert.html'
        ]
    }
    
    # C&C服务器配置
    cc_config = {
        'domains': [
            'secure-update.org',
            'office-support.net', 
            'mail-security.info',
            'system-maintenance.com'
        ],
        'ssl_enabled': True,
        'cdn_enabled': True
    }
    
    return {'gophish': gophish_config, 'cc': cc_config}

def configure_enterprise_services(emu):
    """配置企业服务"""
    
    print("🏢 配置企业服务...")
    
    enterprise_services = {
        # DMZ区域服务
        'web_server': {
            'service': 'nginx',
            'location': 'as200_host_0',
            'ports': ['80:80', '443:443']
        },
        'mail_gateway': {
            'service': 'postfix-gateway',
            'location': 'as200_host_1', 
            'ports': ['25:25', '587:587']
        },
        'dns_server': {
            'service': 'bind9',
            'location': 'as200_host_2',
            'ports': ['53:53/udp', '53:53/tcp']
        },
        
        # 内部企业服务
        'file_server': {
            'service': 'samba',
            'location': 'as202_host_0',
            'ports': ['445:445', '139:139']
        },
        'database_server': {
            'service': 'postgresql',
            'location': 'as202_host_1',
            'ports': ['5432:5432']
        },
        'erp_system': {
            'service': 'odoo',
            'location': 'as202_host_2',
            'ports': ['8069:8069']
        },
        
        # 安全服务
        'firewall': {
            'service': 'pfsense',
            'location': 'as203_host_0',
            'ports': ['443:443']
        },
        'ids_system': {
            'service': 'suricata',
            'location': 'as203_host_1',
            'ports': ['3000:3000']
        }
    }
    
    return enterprise_services

def configure_attack_scenarios(emu):
    """配置攻击场景"""
    
    print("🎯 配置攻击场景...")
    
    attack_scenarios = [
        {
            'name': 'CEO诈骗攻击',
            'type': 'social_engineering',
            'targets': ['as201_host_*'],  # 办公网络所有员工
            'technique': 'business_email_compromise',
            'ai_enhanced': True,
            'difficulty': 4,
            'description': '模拟CEO发送的紧急转账请求邮件'
        },
        {
            'name': '供应链攻击',
            'type': 'supply_chain',
            'targets': ['as202_host_*'],  # 服务器网络
            'technique': 'malicious_update',
            'ai_enhanced': True,
            'difficulty': 5,
            'description': '通过伪造的软件更新进行攻击'
        },
        {
            'name': 'HR招聘诈骗',
            'type': 'credential_harvesting', 
            'targets': ['as220_host_*'],  # 外部用户
            'technique': 'fake_job_portal',
            'ai_enhanced': True,
            'difficulty': 3,
            'description': '伪造招聘网站收集个人信息'
        },
        {
            'name': '技术支持诈骗',
            'type': 'technical_support_scam',
            'targets': ['as221_host_*'],  # 移动用户
            'technique': 'fake_security_alert',
            'ai_enhanced': True,
            'difficulty': 2,
            'description': '虚假的安全警报要求用户操作'
        },
        {
            'name': '内部威胁模拟',
            'type': 'insider_threat',
            'targets': ['as204_host_*'],  # 隔离网络
            'technique': 'privilege_escalation',
            'ai_enhanced': True,
            'difficulty': 4,
            'description': '模拟内部员工的恶意行为'
        },
        {
            'name': '金融钓鱼攻击',
            'type': 'financial_fraud',
            'targets': ['as220_host_*', 'as221_host_*'],
            'technique': 'fake_banking_portal',
            'ai_enhanced': True,
            'difficulty': 4,
            'description': '伪造银行网站窃取登录凭据'
        }
    ]
    
    return attack_scenarios

def configure_ai_defense_system(emu):
    """配置AI防护系统"""
    
    print("🛡️ 配置AI防护系统...")
    
    defense_components = {
        'email_security_gateway': {
            'ai_models': ['phishing_detector', 'sender_reputation'],
            'features': [
                'content_analysis',
                'link_scanning', 
                'attachment_analysis',
                'sender_verification'
            ],
            'location': 'as200_host_1'
        },
        'network_traffic_analyzer': {
            'ai_models': ['anomaly_detector', 'threat_intelligence'],
            'features': [
                'traffic_pattern_analysis',
                'dns_monitoring',
                'c2_detection',
                'data_exfiltration_detection'
            ],
            'location': 'as203_host_1'
        },
        'user_behavior_monitor': {
            'ai_models': ['behavior_analyzer', 'risk_scorer'],
            'features': [
                'login_pattern_analysis',
                'file_access_monitoring',
                'privilege_usage_tracking',
                'suspicious_activity_detection'
            ],
            'location': 'as203_host_2'
        },
        'endpoint_protection': {
            'ai_models': ['malware_detector', 'process_analyzer'],
            'features': [
                'real_time_scanning',
                'behavioral_analysis',
                'memory_protection',
                'network_filtering'
            ],
            'location': 'distributed'
        }
    }
    
    return defense_components

def generate_docker_compose(ai_services, phishing_infra, enterprise_services, defense_system):
    """生成Docker Compose配置"""
    
    compose_content = """version: '3.8'

services:
  # === AI服务层 ===
  ollama:
    image: ollama/ollama:latest
    platform: linux/arm64
    container_name: seed_ollama_llm
    ports:
      - "11434:11434"
    volumes:
      - ollama_models:/root/.ollama
    environment:
      - OLLAMA_HOST=0.0.0.0
    restart: unless-stopped

  phishing-detector:
    image: huggingface/transformers-pytorch-gpu:latest
    platform: linux/arm64
    container_name: seed_phishing_detector
    ports:
      - "8001:8000"
    volumes:
      - ./ai_models/phishing_detector:/app
    command: python -m uvicorn main:app --host 0.0.0.0 --port 8000
    restart: unless-stopped

  image-analyzer:
    image: pytorch/pytorch:latest
    platform: linux/arm64
    container_name: seed_image_analyzer
    ports:
      - "8002:8000"
    volumes:
      - ./ai_models/image_analyzer:/app
    command: python -m uvicorn main:app --host 0.0.0.0 --port 8000
    restart: unless-stopped

  behavior-analyzer:
    image: python:3.11-slim
    platform: linux/arm64
    container_name: seed_behavior_analyzer
    ports:
      - "8003:8000"
    volumes:
      - ./ai_models/behavior_analyzer:/app
    working_dir: /app
    command: python -m uvicorn main:app --host 0.0.0.0 --port 8000
    restart: unless-stopped

  # === 钓鱼攻击基础设施 ===
  gophish:
    image: gophish/gophish:latest
    platform: linux/arm64
    container_name: seed_gophish
    ports:
      - "3333:3333"
      - "8080:80"
    volumes:
      - gophish_data:/opt/gophish
      - ./phishing_templates:/opt/gophish/static/endpoint
    environment:
      - GOPHISH_INITIAL_ADMIN_PASSWORD=SeedEmail2024!
    restart: unless-stopped

  # === 企业邮件服务 ===
  mailserver-enterprise:
    image: mailserver/docker-mailserver:edge
    platform: linux/arm64
    container_name: seed_enterprise_mail
    hostname: mail
    domainname: company.local
    ports:
      - "2500:25"    # SMTP
      - "5870:587"   # Submission
      - "1430:143"   # IMAP
      - "9930:993"   # IMAPS
    volumes:
      - mailserver_data:/var/mail
      - mailserver_state:/var/mail-state
      - mailserver_logs:/var/log/mail
      - mailserver_config:/tmp/docker-mailserver
    environment:
      - OVERRIDE_HOSTNAME=mail.company.local
      - PERMIT_DOCKER=connected-networks
      - ONE_DIR=1
      - ENABLE_CLAMAV=1
      - ENABLE_FAIL2BAN=1
      - ENABLE_POSTGREY=1
      - DMS_DEBUG=1
      - ENABLE_SPAMASSASSIN=1
      - SSL_TYPE=self-signed
    cap_add:
      - NET_ADMIN
    restart: unless-stopped

  # === 防护系统 ===
  suricata:
    image: jasonish/suricata:latest
    platform: linux/arm64
    container_name: seed_suricata_ids
    ports:
      - "8000:8000"
    volumes:
      - suricata_logs:/var/log/suricata
      - ./suricata_config:/etc/suricata
    network_mode: host
    cap_add:
      - NET_ADMIN
      - SYS_NICE
    restart: unless-stopped

  # === 监控和可视化 ===
  grafana:
    image: grafana/grafana:latest
    platform: linux/arm64
    container_name: seed_grafana
    ports:
      - "3000:3000"
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana_config:/etc/grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=SeedEmail2024!
    restart: unless-stopped

  prometheus:
    image: prom/prometheus:latest
    platform: linux/arm64
    container_name: seed_prometheus
    ports:
      - "9090:9090"
    volumes:
      - prometheus_data:/prometheus
      - ./prometheus_config:/etc/prometheus
    restart: unless-stopped

  # === 数据存储 ===
  postgresql:
    image: postgres:15-alpine
    platform: linux/arm64
    container_name: seed_postgresql
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=seedmail
      - POSTGRES_USER=seeduser
      - POSTGRES_PASSWORD=SeedEmail2024!
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    platform: linux/arm64
    container_name: seed_redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped

  # === Web界面和API ===
  seed-web-interface:
    build: ./web_interface
    platform: linux/arm64
    container_name: seed_web_interface
    ports:
      - "5000:5000"
    volumes:
      - ./web_interface:/app
    environment:
      - FLASK_ENV=development
      - DATABASE_URL=postgresql://seeduser:SeedEmail2024!@postgresql:5432/seedmail
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgresql
      - redis
    restart: unless-stopped

volumes:
  ollama_models:
  gophish_data:
  mailserver_data:
  mailserver_state:
  mailserver_logs:
  mailserver_config:
  suricata_logs:
  grafana_data:
  prometheus_data:
  postgres_data:
  redis_data:

networks:
  default:
    name: seed_phishing_network
    driver: bridge
    ipam:
      config:
        - subnet: 172.30.0.0/16
"""
    
    return compose_content

def run(platform="arm"):
    """运行30项目"""
    
    print("🎣 启动SEED钓鱼攻击与AI防护系统...")
    
    # 创建仿真器
    emu = Emulator()
    
    print("🌐 创建企业网络环境...")
    base = create_enterprise_network(emu)
    emu.addLayer(base)
    
    print("🔧 配置路由协议...")
    routing = Routing()
    emu.addLayer(routing)
    
    bgp = Ebgp()
    emu.addLayer(bgp)
    
    ibgp = Ibgp()
    emu.addLayer(ibgp)
    
    ospf = Ospf()
    emu.addLayer(ospf)
    
    # 配置各个组件
    ai_services = configure_ai_services(emu)
    phishing_infra = configure_phishing_infrastructure(emu)
    enterprise_services = configure_enterprise_services(emu)
    defense_system = configure_ai_defense_system(emu)
    attack_scenarios = configure_attack_scenarios(emu)
    
    print("🐳 渲染和编译...")
    emu.render()
    
    if platform.lower() == "amd":
        docker = Docker(platform=Platform.AMD64)
    else:
        docker = Docker(platform=Platform.ARM64)
        
    emu.compile(docker, "./output", override=True)
    
    # 生成Docker Compose文件
    compose_content = generate_docker_compose(ai_services, phishing_infra, enterprise_services, defense_system)
    
    with open("./output/docker-compose-services.yml", "w") as f:
        f.write(compose_content)
    
    # 生成配置文件和脚本
    generate_configuration_files(ai_services, phishing_infra, attack_scenarios, defense_system)

    # 启动Web管理界面
    print("🌐 启动Web管理界面...")
    start_web_server()
    
    print(f"""
======================================================================
🎣 SEED 钓鱼攻击与AI防护系统 (30) 创建完成！
======================================================================

🌐 网络架构:
----------------------------------------
🏢 企业网络环境:
   - DMZ区域 (AS-200): Web服务器、邮件网关、DNS服务器
   - 办公网络 (AS-201): 8个员工工作站
   - 服务器网络 (AS-202): 内部系统、数据库、ERP
   - 管理网络 (AS-203): 防火墙、IDS/IPS系统
   - 隔离网络 (AS-204): 敏感和研发系统

🎯 攻击者基础设施:
   - C&C服务器 (AS-205): 命令控制中心
   - 钓鱼基础设施 (AS-206): 钓鱼页面托管
   - 代理网络 (AS-207): 匿名化流量

☁️ 云服务环境:
   - 公有云 (AS-210): AWS/Azure模拟
   - AI服务 (AS-211): 云端AI API

👥 用户网络:
   - 普通用户 (AS-220): 10个主机
   - 移动用户 (AS-221): 8个主机

🧠 AI服务组件:
----------------------------------------
🤖 攻击侧AI:
   - Ollama LLM: 本地大语言模型 (Qwen2-7B)
   - 钓鱼邮件生成器: 个性化攻击内容
   - 社会工程学AI: 心理学攻击策略
   - 目标情报分析: 自动化信息收集

🛡️ 防护侧AI:
   - 邮件安全检测: NLP驱动的钓鱼检测
   - 图像相似度分析: Logo伪造检测
   - 用户行为分析: 异常行为识别
   - 网络流量监控: 威胁情报检测

🎯 攻击场景:
----------------------------------------
1. 🎭 CEO诈骗攻击 (难度: ⭐⭐⭐⭐)
2. 🔗 供应链攻击 (难度: ⭐⭐⭐⭐⭐)
3. 💼 HR招聘诈骗 (难度: ⭐⭐⭐)
4. 📞 技术支持诈骗 (难度: ⭐⭐)
5. 🏢 内部威胁模拟 (难度: ⭐⭐⭐⭐)
6. 💰 金融钓鱼攻击 (难度: ⭐⭐⭐⭐)

🚀 启动命令:
----------------------------------------
# 1. 启动网络基础设施
cd output/
docker-compose up -d

# 2. 启动AI和攻击服务
docker-compose -f docker-compose-services.yml up -d

# 3. 初始化AI模型
./scripts/init_ai_models.sh

# 4. 配置攻击场景
./scripts/setup_attack_scenarios.sh

📊 系统访问:
----------------------------------------
🌐 Web管理界面: http://localhost:5000
🎣 Gophish平台: https://localhost:3333
📈 监控面板: http://localhost:3000 (Grafana)
🧠 AI API文档: http://localhost:8001/docs
📧 企业邮件: localhost:2500 (SMTP)

🔧 AI模型配置:
----------------------------------------
📝 钓鱼邮件生成: Qwen2-7B + 专用微调
🖼️ 图像检测: CLIP + 相似度算法
📊 行为分析: Isolation Forest + LSTM
🔍 内容检测: BERT + 自定义分类器

⚠️ 安全提醒:
----------------------------------------
- 🔒 所有攻击活动限制在仿真环境内
- 📋 仅用于授权的安全教育和研究
- 🛡️ 严格遵守网络安全伦理准则
- 📝 完整的操作审计和日志记录

🎓 教学模块:
----------------------------------------
- 初级: 钓鱼识别和防护基础
- 中级: 企业安全防护实践
- 高级: 攻防对抗实战演练
- 专家: AI安全研究和对抗样本

======================================================================
    """)

def generate_configuration_files(ai_services, phishing_infra, attack_scenarios, defense_system):
    """生成配置文件和初始化脚本"""
    
    # 创建目录结构
    os.makedirs("./ai_models", exist_ok=True)
    os.makedirs("./phishing_templates", exist_ok=True)
    os.makedirs("./scripts", exist_ok=True)
    os.makedirs("./web_interface", exist_ok=True)
    
    # 生成AI模型初始化脚本
    init_script = """#!/bin/bash
echo "🧠 初始化AI模型..."

# 拉取Ollama模型
docker exec seed_ollama_llm ollama pull qwen2:7b
docker exec seed_ollama_llm ollama pull chatglm3:6b

# 下载预训练模型
echo "📥 下载预训练模型..."
echo "模型将存储在 ./ai_models/ 目录"

echo "✅ AI模型初始化完成！"
"""
    
    with open("./scripts/init_ai_models.sh", "w") as f:
        f.write(init_script)
    
    # 生成攻击场景配置脚本
    scenario_script = """#!/bin/bash
echo "🎯 配置攻击场景..."

# 创建钓鱼模板
echo "📧 生成钓鱼邮件模板..."

# 配置Gophish
echo "🎣 配置Gophish攻击平台..."

echo "✅ 攻击场景配置完成！"
echo "访问 https://localhost:3333 开始钓鱼实验"
"""
    
    with open("./scripts/setup_attack_scenarios.sh", "w") as f:
        f.write(scenario_script)

def start_web_server():
    """启动30项目的Web管理界面"""
    from flask import Flask, render_template_string

    app = Flask(__name__)

    @app.route('/')
    def index():
        html = """
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>SEED 钓鱼攻击与AI防护系统 (30)</title>
            <style>
                body {
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    margin: 0;
                    padding: 20px;
                    min-height: 100vh;
                }
                .container {
                    max-width: 1200px;
                    margin: 0 auto;
                    background: rgba(255, 255, 255, 0.1);
                    border-radius: 15px;
                    padding: 30px;
                    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
                }
                .header {
                    text-align: center;
                    margin-bottom: 40px;
                }
                .header h1 {
                    font-size: 2.5em;
                    margin-bottom: 10px;
                    text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
                }
                .grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                    gap: 20px;
                    margin-top: 30px;
                }
                .card {
                    background: rgba(255, 255, 255, 0.15);
                    border-radius: 10px;
                    padding: 20px;
                    backdrop-filter: blur(10px);
                    border: 1px solid rgba(255, 255, 255, 0.2);
                }
                .card h3 {
                    margin-top: 0;
                    color: #ffd700;
                }
                .status {
                    padding: 5px 10px;
                    border-radius: 20px;
                    font-size: 0.9em;
                    display: inline-block;
                    margin: 5px 0;
                }
                .status.running {
                    background: #28a745;
                    color: white;
                }
                .status.warning {
                    background: #ffc107;
                    color: black;
                }
                .btn {
                    display: inline-block;
                    padding: 10px 20px;
                    background: linear-gradient(45deg, #ff6b6b, #ffa500);
                    color: white;
                    text-decoration: none;
                    border-radius: 25px;
                    margin: 10px 5px;
                    transition: transform 0.2s;
                }
                .btn:hover {
                    transform: translateY(-2px);
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎣 SEED 钓鱼攻击与AI防护系统 (30)</h1>
                    <p>AI驱动的网络安全教学平台</p>
                </div>

                <div class="grid">
                    <div class="card">
                        <h3>🏢 企业网络环境</h3>
                        <p><span class="status running">运行中</span></p>
                        <ul>
                            <li>DMZ区域 (AS-200): Web服务器、邮件网关</li>
                            <li>办公网络 (AS-201): 8个员工工作站</li>
                            <li>服务器网络 (AS-202): 内部系统、数据库</li>
                            <li>管理网络 (AS-203): 防火墙、IDS/IPS</li>
                            <li>隔离网络 (AS-204): 敏感和研发系统</li>
                        </ul>
                    </div>

                    <div class="card">
                        <h3>🎯 攻击者基础设施</h3>
                        <p><span class="status running">运行中</span></p>
                        <ul>
                            <li>C&C服务器 (AS-205): 命令控制中心</li>
                            <li>钓鱼基础设施 (AS-206): 钓鱼页面托管</li>
                            <li>代理网络 (AS-207): 匿名化流量</li>
                        </ul>
                    </div>

                    <div class="card">
                        <h3>☁️ 云服务环境</h3>
                        <p><span class="status running">配置完成</span></p>
                        <ul>
                            <li>公有云 (AS-210): AWS/Azure模拟</li>
                            <li>AI服务 (AS-211): 云端AI API</li>
                        </ul>
                    </div>

                    <div class="card">
                        <h3>🧠 AI服务组件</h3>
                        <p><span class="status warning">待启动</span></p>
                        <ul>
                            <li>Ollama LLM: 本地大语言模型</li>
                            <li>钓鱼邮件生成器: 个性化攻击内容</li>
                            <li>邮件安全检测: NLP驱动的钓鱼检测</li>
                            <li>用户行为分析: 异常行为识别</li>
                        </ul>
                    </div>

                    <div class="card">
                        <h3>🎯 攻击场景</h3>
                        <p><span class="status running">配置完成</span></p>
                        <ul>
                            <li>CEO诈骗攻击 (难度: ⭐⭐⭐⭐)</li>
                            <li>供应链攻击 (难度: ⭐⭐⭐⭐⭐)</li>
                            <li>HR招聘诈骗 (难度: ⭐⭐⭐)</li>
                            <li>技术支持诈骗 (难度: ⭐⭐)</li>
                        </ul>
                    </div>

                    <div class="card">
                        <h3>🔧 管理控制台</h3>
                        <p><span class="status running">运行中</span></p>
                        <ul>
                            <li>Web管理界面: http://localhost:5002</li>
                            <li>Gophish平台: https://localhost:3333</li>
                            <li>Grafana监控: http://localhost:3000</li>
                            <li>AI API文档: http://localhost:8001</li>
                        </ul>
                        <a href="/project_overview" class="btn">📖 项目概述</a>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        return render_template_string(html)

    @app.route('/project_overview')
    def project_overview():
        html = """
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>30项目概述 - SEED钓鱼攻击与AI防护系统</title>
            <style>
                body {
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    margin: 0;
                    padding: 20px;
                    min-height: 100vh;
                }
                .container {
                    max-width: 1000px;
                    margin: 0 auto;
                    background: rgba(255, 255, 255, 0.1);
                    border-radius: 15px;
                    padding: 30px;
                    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
                }
                .header {
                    text-align: center;
                    margin-bottom: 30px;
                }
                .header h1 {
                    font-size: 2em;
                    margin-bottom: 10px;
                    text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
                }
                .section {
                    margin-bottom: 30px;
                    background: rgba(255, 255, 255, 0.1);
                    border-radius: 10px;
                    padding: 20px;
                }
                .section h2 {
                    color: #ffd700;
                    margin-top: 0;
                }
                .feature-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                    gap: 15px;
                    margin-top: 15px;
                }
                .feature-item {
                    background: rgba(255, 255, 255, 0.1);
                    padding: 15px;
                    border-radius: 8px;
                    border-left: 4px solid #ffd700;
                }
                .feature-item h4 {
                    margin: 0 0 8px 0;
                    color: #ffd700;
                }
                .btn {
                    display: inline-block;
                    padding: 10px 20px;
                    background: linear-gradient(45deg, #ff6b6b, #ffa500);
                    color: white;
                    text-decoration: none;
                    border-radius: 25px;
                    margin: 10px 5px 10px 0;
                    transition: transform 0.2s;
                }
                .btn:hover {
                    transform: translateY(-2px);
                }
                .code {
                    background: rgba(0, 0, 0, 0.3);
                    padding: 15px;
                    border-radius: 8px;
                    font-family: 'Courier New', monospace;
                    margin: 15px 0;
                    overflow-x: auto;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎣 SEED 钓鱼攻击与AI防护系统 (30)</h1>
                    <h2>项目概述与技术实现</h2>
                </div>

                <div class="section">
                    <h2>📋 项目简介</h2>
                    <p>SEED 30项目是一个基于AI技术的网络安全教学平台，专门用于钓鱼攻击的模拟、分析和防护研究。该系统集成了现代网络安全技术，为学生和研究人员提供了一个安全的实验环境。</p>
                </div>

                <div class="section">
                    <h2>🌐 网络架构</h2>
                    <div class="feature-grid">
                        <div class="feature-item">
                            <h4>🏢 企业网络</h4>
                            <p>完整的多层企业网络架构，包含DMZ、办公区、服务器区等安全区域。</p>
                        </div>
                        <div class="feature-item">
                            <h4>🎯 攻击基础设施</h4>
                            <p>专业的攻击者基础设施，包含C&C服务器、钓鱼页面托管、代理网络等。</p>
                        </div>
                        <div class="feature-item">
                            <h4>☁️ 云服务</h4>
                            <p>模拟公有云环境，提供AI API、存储等云端服务。</p>
                        </div>
                        <div class="feature-item">
                            <h4>👥 用户网络</h4>
                            <p>模拟普通用户和移动用户的网络环境。</p>
                        </div>
                    </div>
                </div>

                <div class="section">
                    <h2>🧠 AI技术集成</h2>
                    <div class="feature-grid">
                        <div class="feature-item">
                            <h4>🤖 攻击侧AI</h4>
                            <ul>
                                <li>Ollama大语言模型</li>
                                <li>个性化钓鱼邮件生成</li>
                                <li>社会工程学分析</li>
                                <li>目标情报收集</li>
                            </ul>
                        </div>
                        <div class="feature-item">
                            <h4>🛡️ 防护侧AI</h4>
                            <ul>
                                <li>NLP钓鱼检测</li>
                                <li>图像相似度分析</li>
                                <li>用户行为分析</li>
                                <li>威胁情报监控</li>
                            </ul>
                        </div>
                    </div>
                </div>

                <div class="section">
                    <h2>🎯 攻击场景</h2>
                    <p>系统提供多种经典的钓鱼攻击场景，每种场景都有不同的难度级别和AI增强特性：</p>
                    <ul>
                        <li><strong>CEO诈骗攻击</strong> (难度⭐⭐⭐⭐): 伪造高管邮件进行诈骗</li>
                        <li><strong>供应链攻击</strong> (难度⭐⭐⭐⭐⭐): 通过第三方供应商渗透</li>
                        <li><strong>HR招聘诈骗</strong> (难度⭐⭐⭐): 假冒招聘网站收集个人信息</li>
                        <li><strong>技术支持诈骗</strong> (难度⭐⭐): 虚假安全警报诱导操作</li>
                        <li><strong>内部威胁模拟</strong> (难度⭐⭐⭐⭐): 模拟员工恶意行为</li>
                        <li><strong>金融钓鱼攻击</strong> (难度⭐⭐⭐⭐): 伪造银行网站窃取凭据</li>
                    </ul>
                </div>

                <div class="section">
                    <h2>🚀 快速开始</h2>
                    <h3>1. 启动系统</h3>
                    <div class="code">
cd /path/to/seed-email-system/examples/.not_ready_examples<br>
source docker_aliases.sh<br>
seed-30
                    </div>

                    <h3>2. 访问管理界面</h3>
                    <ul>
                        <li><strong>主控制台</strong>: http://localhost:5002</li>
                        <li><strong>Gophish钓鱼平台</strong>: https://localhost:3333</li>
                        <li><strong>Grafana监控</strong>: http://localhost:3000</li>
                        <li><strong>AI API文档</strong>: http://localhost:8001/docs</li>
                    </ul>

                    <h3>3. 配置AI模型</h3>
                    <div class="code">
# 初始化AI模型<br>
./scripts/init_ai_models.sh<br><br>
# 配置攻击场景<br>
./scripts/setup_attack_scenarios.sh
                    </div>
                </div>

                <div class="section">
                    <h2>⚠️ 安全提醒</h2>
                    <ul>
                        <li>🔒 所有攻击活动严格限制在仿真环境内</li>
                        <li>📋 仅用于授权的安全教育和研究</li>
                        <li>🛡️ 严格遵守网络安全伦理准则</li>
                        <li>📝 完整的操作审计和日志记录</li>
                    </ul>
                </div>

                <div class="section">
                    <h2>🎓 教学价值</h2>
                    <div class="feature-grid">
                        <div class="feature-item">
                            <h4>初级课程</h4>
                            <p>钓鱼识别和防护基础</p>
                        </div>
                        <div class="feature-item">
                            <h4>中级课程</h4>
                            <p>企业安全防护实践</p>
                        </div>
                        <div class="feature-item">
                            <h4>高级课程</h4>
                            <p>攻防对抗实战演练</p>
                        </div>
                        <div class="feature-item">
                            <h4>专家课程</h4>
                            <p>AI安全研究和对抗样本</p>
                        </div>
                    </div>
                </div>

                <div class="section" style="text-align: center;">
                    <a href="/" class="btn">🏠 返回主页面</a>
                    <a href="/attack_scenarios" class="btn">🎯 查看攻击场景</a>
                    <a href="/ai_models" class="btn">🧠 AI模型配置</a>
                </div>
            </div>
        </body>
        </html>
        """
        return render_template_string(html)

    @app.route('/attack_scenarios')
    def attack_scenarios():
        html = """
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>攻击场景 - SEED 30项目</title>
            <style>
                body {
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    margin: 0;
                    padding: 20px;
                    min-height: 100vh;
                }
                .container {
                    max-width: 1000px;
                    margin: 0 auto;
                    background: rgba(255, 255, 255, 0.1);
                    border-radius: 15px;
                    padding: 30px;
                    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
                }
                .scenario-card {
                    background: rgba(255, 255, 255, 0.15);
                    border-radius: 10px;
                    padding: 20px;
                    margin-bottom: 20px;
                    border-left: 5px solid #ffd700;
                }
                .difficulty {
                    display: inline-block;
                    padding: 3px 8px;
                    border-radius: 12px;
                    font-size: 0.8em;
                    margin: 5px 0;
                }
                .difficulty.easy { background: #28a745; }
                .difficulty.medium { background: #ffc107; color: black; }
                .difficulty.hard { background: #fd7e14; }
                .difficulty.expert { background: #dc3545; }
                .btn {
                    display: inline-block;
                    padding: 8px 15px;
                    background: linear-gradient(45deg, #ff6b6b, #ffa500);
                    color: white;
                    text-decoration: none;
                    border-radius: 20px;
                    margin: 5px;
                    font-size: 0.9em;
                }
                .header { text-align: center; margin-bottom: 30px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎯 攻击场景库</h1>
                    <p>30项目支持的钓鱼攻击场景</p>
                </div>

                <div class="scenario-card">
                    <h3>CEO诈骗攻击</h3>
                    <span class="difficulty hard">难度: ⭐⭐⭐⭐</span>
                    <p>伪造高管邮件，要求下属紧急转账或提供敏感信息。</p>
                    <p><strong>AI增强:</strong> 个性化邮件内容、紧急感营造、社会工程学技巧</p>
                    <a href="#" class="btn">🚀 启动场景</a>
                    <a href="#" class="btn">📊 查看详情</a>
                </div>

                <div class="scenario-card">
                    <h3>供应链攻击</h3>
                    <span class="difficulty expert">难度: ⭐⭐⭐⭐⭐</span>
                    <p>通过第三方供应商或合作伙伴进行渗透，获取企业内部访问权限。</p>
                    <p><strong>AI增强:</strong> 供应链分析、弱点识别、多阶段攻击链</p>
                    <a href="#" class="btn">🚀 启动场景</a>
                    <a href="#" class="btn">📊 查看详情</a>
                </div>

                <div class="scenario-card">
                    <h3>HR招聘诈骗</h3>
                    <span class="difficulty medium">难度: ⭐⭐⭐</span>
                    <p>伪造招聘网站，诱导求职者提供个人信息和证件资料。</p>
                    <p><strong>AI增强:</strong> 职位描述生成、面试流程模拟、数据收集分析</p>
                    <a href="#" class="btn">🚀 启动场景</a>
                    <a href="#" class="btn">📊 查看详情</a>
                </div>

                <div class="scenario-card">
                    <h3>技术支持诈骗</h3>
                    <span class="difficulty easy">难度: ⭐⭐</span>
                    <p>虚假的安全警报，诱导用户提供系统访问权限或敏感信息。</p>
                    <p><strong>AI增强:</strong> 技术术语生成、紧急情况营造、信任建立</p>
                    <a href="#" class="btn">🚀 启动场景</a>
                    <a href="#" class="btn">📊 查看详情</a>
                </div>

                <div class="scenario-card">
                    <h3>内部威胁模拟</h3>
                    <span class="difficulty hard">难度: ⭐⭐⭐⭐</span>
                    <p>模拟内部员工的恶意行为，测试企业内部安全控制。</p>
                    <p><strong>AI增强:</strong> 行为模式分析、异常检测、权限滥用模拟</p>
                    <a href="#" class="btn">🚀 启动场景</a>
                    <a href="#" class="btn">📊 查看详情</a>
                </div>

                <div class="scenario-card">
                    <h3>金融钓鱼攻击</h3>
                    <span class="difficulty hard">难度: ⭐⭐⭐⭐</span>
                    <p>伪造银行或金融机构网站，窃取登录凭据和财务信息。</p>
                    <p><strong>AI增强:</strong> 网站克隆、交易模式分析、实时欺诈检测</p>
                    <a href="#" class="btn">🚀 启动场景</a>
                    <a href="#" class="btn">📊 查看详情</a>
                </div>

                <div style="text-align: center; margin-top: 30px;">
                    <a href="/" class="btn">🏠 返回主页</a>
                    <a href="/project_overview" class="btn">📖 项目概述</a>
                </div>
            </div>
        </body>
        </html>
        """
        return render_template_string(html)

    print("""
    ╭─────────────────────────────────────────────────────────────╮
    │             SEED 钓鱼攻击与AI防护系统 Web 管理界面             │
    │                30-phishing-ai-system AI增强版                │
    ╰─────────────────────────────────────────────────────────────╯

    🌐 访问地址: http://localhost:5002
    🎣 AI驱动的钓鱼攻击模拟和防护
    🤖 大语言模型集成 (Ollama + Qwen2-7B)
    🛡️ 智能威胁检测和行为分析
    📊 实时监控和攻击场景演示
    📖 项目概述: http://localhost:5002/project_overview

    """)

    app.run(host='0.0.0.0', port=5002, debug=True)

if __name__ == "__main__":
    platform = sys.argv[1] if len(sys.argv) > 1 else "arm"
    if platform not in ["arm", "amd"]:
        print("Usage: python3 phishing_ai_system.py [arm|amd]")
        sys.exit(1)

    run(platform)
