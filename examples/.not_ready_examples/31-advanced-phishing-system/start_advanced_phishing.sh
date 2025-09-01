#!/bin/bash

echo "🎣====================================================================🎣"
echo "          SEED 高级钓鱼攻防系统启动脚本"
echo "               31-advanced-phishing-system"
echo "🎣====================================================================🎣"
echo ""

# 设置错误时退出
set -e

# 检查运行环境
echo "🔍 检查运行环境..."

# 检查Python环境
if ! python3 --version &> /dev/null; then
    echo "❌ Python3未安装"
    exit 1
fi

# 检查Docker环境
if ! docker --version &> /dev/null; then
    echo "❌ Docker未安装或未启动"
    exit 1
fi

# 检查必要的Python包
echo "📦 检查Python依赖..."
REQUIRED_PACKAGES=("torch" "transformers" "fastapi" "flask" "flask-socketio" "numpy" "pandas" "scikit-learn" "asyncio" "aiohttp" "asyncpg" "redis" "cryptography" "openai" "python-dotenv")

for package in "${REQUIRED_PACKAGES[@]}"; do
    if ! python3 -c "import $package" &> /dev/null; then
        echo "⚠️  缺少依赖包: $package"
        echo "📥 正在安装 $package..."
        pip3 install $package 2>/dev/null || echo "⚠️  $package 安装失败，请手动安装"
    fi
done

# 检查OpenAI配置
echo "🤖 检查OpenAI配置..."
if [ -f ".env" ]; then
    source .env
    if [ -n "$OPENAI_API_KEY" ]; then
        echo "✅ OpenAI API密钥已配置"
        echo "🔗 OpenAI Base URL: $OPENAI_BASE_URL"
    else
        echo "⚠️  未找到OPENAI_API_KEY环境变量"
        echo "📝 请在.env文件中设置OPENAI_API_KEY"
    fi
else
    echo "⚠️  未找到.env配置文件"
    echo "📄 创建默认配置文件..."
    cat > .env << 'EOF'
# OpenAI Configuration
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://www.dmxapi.cn/v1

# System Configuration
SYSTEM_DEBUG=true
SYSTEM_NAME=SEED Advanced Phishing System
SYSTEM_VERSION=1.0.0
EOF
    echo "✅ 已创建.env文件，请配置您的OpenAI API密钥"
fi

echo "✅ 环境检查完成"
echo ""

# 检查SEED网络基础设施
echo "🌐 检查SEED网络基础设施..."

# 检查29-1项目是否运行（作为网络基础）
if ! docker ps | grep -q "hnode_"; then
    echo "⚠️  未检测到SEED网络基础设施"
    echo "🚀 启动基础网络环境..."
    
    # 检查是否有29-1项目
    if [ -d "../29-1-email-system" ]; then
        echo "📡 使用29-1项目作为网络基础..."
        cd ../29-1-email-system
        
        if [ ! -f "output/docker-compose.yml" ]; then
            echo "📦 生成网络配置..."
            python3 email_realistic.py arm
        fi
        
        echo "🐳 启动网络基础设施..."
        cd output && docker-compose up -d
        cd ../../31-advanced-phishing-system
        
        echo "⏳ 等待网络基础设施稳定..."
        sleep 10
    else
        echo "⚠️  未找到网络基础项目，将使用简化网络"
    fi
fi

echo "✅ 网络基础设施就绪"
echo ""

# 创建必要的目录
echo "📁 创建项目目录结构..."
mkdir -p {config,logs,data,backups}
mkdir -p web_console/{static/{css,js,images},templates}
mkdir -p ai_models/{models,cache,datasets}
mkdir -p attack_framework/{campaigns,templates,targets}
mkdir -p utils/{osint,steganography,polymorphic}

# 生成配置文件
echo "⚙️  生成系统配置..."
if [ ! -f "config/system_config.json" ]; then
    cat > config/system_config.json << 'EOF'
{
    "system": {
        "name": "SEED Advanced Phishing System",
        "version": "1.0.0",
        "debug": true,
        "max_concurrent_campaigns": 100,
        "ai_model_cache_size": "8GB"
    },
    "ai_models": {
        "primary_llm": {
            "model_name": "Qwen/Qwen2-7B-Instruct",
            "device": "auto",
            "max_length": 4096,
            "temperature": 0.7
        },
        "threat_intelligence": {
            "model_path": "./ai_models/threat_intelligence/",
            "update_interval": 3600
        },
        "evasion_engine": {
            "techniques": ["polymorphic", "semantic_drift", "adversarial"],
            "strength": 0.8
        }
    },
    "attack_framework": {
        "apt_simulation": {
            "max_stages": 10,
            "persistence_techniques": ["registry", "services", "files"],
            "lateral_movement": true
        },
        "social_engineering": {
            "osint_sources": ["linkedin", "twitter", "company_website"],
            "psychological_profiles": true,
            "trust_building": true
        }
    },
    "security": {
        "encryption_key": null,
        "access_control": "strict",
        "audit_logging": true,
        "sandbox_isolation": true
    },
    "network": {
        "web_port": 5003,
        "api_port": 8003,
        "websocket_port": 9003,
        "database_url": "postgresql://seed:seed@localhost:5432/advanced_phishing"
    }
}
EOF
    echo "✅ 配置文件已生成"
fi

# 创建Docker Compose文件
echo "🐳 生成Docker编排文件..."
if [ ! -f "docker-compose.yml" ]; then
    cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  advanced-phishing-web:
    build: .
    container_name: seed-advanced-phishing
    ports:
      - "5003:5003"
      - "8003:8003"
      - "9003:9003"
    volumes:
      - ./config:/app/config
      - ./logs:/app/logs
      - ./data:/app/data
      - ./ai_models:/app/ai_models
    environment:
      - PYTHONPATH=/app
      - FLASK_ENV=development
    networks:
      - seed-advanced-network
    restart: unless-stopped
    depends_on:
      - redis
      - postgres

  redis:
    image: redis:alpine
    container_name: seed-advanced-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    networks:
      - seed-advanced-network
    restart: unless-stopped

  postgres:
    image: postgres:13
    container_name: seed-advanced-postgres
    environment:
      POSTGRES_DB: advanced_phishing
      POSTGRES_USER: seed
      POSTGRES_PASSWORD: seed
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    networks:
      - seed-advanced-network
    restart: unless-stopped

  ollama:
    image: ollama/ollama:latest
    container_name: seed-advanced-ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    networks:
      - seed-advanced-network
    restart: unless-stopped

networks:
  seed-advanced-network:
    driver: bridge
    external: false

volumes:
  redis_data:
  postgres_data:
  ollama_data:
EOF
    echo "✅ Docker编排文件已生成"
fi

# 创建Dockerfile
if [ ! -f "Dockerfile" ]; then
    cat > Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# 安装Python依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 设置权限
RUN chmod +x start_advanced_phishing.sh

# 暴露端口
EXPOSE 5003 8003 9003

# 启动命令
CMD ["python3", "web_console/app.py"]
EOF
    echo "✅ Dockerfile已生成"
fi

# 创建requirements.txt
if [ ! -f "requirements.txt" ]; then
    cat > requirements.txt << 'EOF'
torch>=2.0.0
transformers>=4.30.0
fastapi>=0.100.0
uvicorn>=0.22.0
flask>=2.3.0
flask-socketio>=5.3.0
numpy>=1.24.0
pandas>=2.0.0
scikit-learn>=1.3.0
aiohttp>=3.8.0
asyncpg>=0.28.0
redis>=4.5.0
cryptography>=41.0.0
Pillow>=10.0.0
requests>=2.31.0
websockets>=11.0.0
jinja2>=3.1.0
psutil>=5.9.0
python-multipart>=0.0.6
python-socketio>=5.8.0
python-engineio>=4.7.0
EOF
    echo "✅ 依赖文件已生成"
fi

# 检查是否需要启动容器服务
echo "🔧 检查并启动容器服务..."

# 启动Redis（如果未运行）
if ! docker ps | grep -q "redis"; then
    echo "🚀 启动Redis服务..."
    docker run -d --name seed-advanced-redis \
        -p 6379:6379 \
        --restart unless-stopped \
        redis:alpine 2>/dev/null || echo "⚠️  Redis启动失败或已存在"
fi

# 启动PostgreSQL（如果未运行）
if ! docker ps | grep -q "postgres"; then
    echo "🚀 启动PostgreSQL服务..."
    docker run -d --name seed-advanced-postgres \
        -e POSTGRES_DB=advanced_phishing \
        -e POSTGRES_USER=seed \
        -e POSTGRES_PASSWORD=seed \
        -p 5432:5432 \
        --restart unless-stopped \
        postgres:13 2>/dev/null || echo "⚠️  PostgreSQL启动失败或已存在"
fi

# 启动Ollama（如果未运行）
if ! docker ps | grep -q "ollama"; then
    echo "🚀 启动Ollama AI服务..."
    docker run -d --name seed-advanced-ollama \
        -p 11434:11434 \
        -v ollama_data:/root/.ollama \
        --restart unless-stopped \
        ollama/ollama:latest 2>/dev/null || echo "⚠️  Ollama启动失败或已存在"
    
    # 等待Ollama启动并拉取模型
    echo "⏳ 等待Ollama服务启动..."
    sleep 5
    
    echo "📥 拉取Qwen2-7B模型（首次运行需要较长时间）..."
    docker exec seed-advanced-ollama ollama pull qwen2:7b 2>/dev/null || echo "⚠️  模型拉取失败，请手动执行"
fi

echo "✅ 容器服务启动完成"
echo ""

# 初始化数据库
echo "💾 初始化数据库..."
python3 -c "
import asyncio
import asyncpg
import json

async def init_db():
    try:
        conn = await asyncpg.connect('postgresql://seed:seed@localhost:5432/advanced_phishing')
        
        # 创建基本表结构
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS campaigns (
                id VARCHAR(32) PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                type VARCHAR(100) NOT NULL,
                status VARCHAR(50) NOT NULL DEFAULT 'planning',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                config JSONB,
                results JSONB
            )
        ''')
        
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS targets (
                id VARCHAR(32) PRIMARY KEY,
                name VARCHAR(255),
                email VARCHAR(255),
                position VARCHAR(255),
                company VARCHAR(255),
                profile JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS attack_logs (
                id SERIAL PRIMARY KEY,
                campaign_id VARCHAR(32) REFERENCES campaigns(id),
                target_id VARCHAR(32) REFERENCES targets(id),
                action VARCHAR(100),
                result VARCHAR(50),
                details JSONB,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        await conn.close()
        print('✅ 数据库初始化完成')
        
    except Exception as e:
        print(f'⚠️  数据库初始化失败: {e}')

# asyncio.run(init_db())
print('💾 数据库初始化跳过（需要PostgreSQL完全启动）')
" 2>/dev/null

# 启动Web控制台
echo "🌐 启动Web控制台..."

# 检查端口是否被占用
if lsof -Pi :5003 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  端口5003已被占用，尝试停止现有服务..."
    pkill -f "web_console/app.py" 2>/dev/null || true
    sleep 2
fi

# 启动Web服务
echo "🚀 启动高级钓鱼系统Web控制台..."
cd web_console
nohup python3 app.py > ../logs/web_console.log 2>&1 &
WEB_PID=$!
cd ..

# 等待服务启动
echo "⏳ 等待Web服务启动..."
sleep 5

# 检查服务状态
if ps -p $WEB_PID > /dev/null 2>&1; then
    echo "✅ Web控制台启动成功 (PID: $WEB_PID)"
else
    echo "❌ Web控制台启动失败，查看日志："
    tail -20 logs/web_console.log
    exit 1
fi

echo ""
echo "🎣====================================================================🎣"
echo "              SEED高级钓鱼系统启动完成"
echo "🎣====================================================================🎣"
echo ""
echo "🌐 访问地址:"
echo "   主控制台: http://localhost:5003"
echo "   API接口:  http://localhost:8003"
echo "   WebSocket: ws://localhost:9003"
echo ""
echo "🔐 默认登录:"
echo "   用户名: admin"
echo "   密码:   seed31"
echo ""
echo "🎯 主要功能:"
echo "   • AI驱动的高级钓鱼攻击设计"
echo "   • APT攻击链模拟和分析"
echo "   • 多模态威胁检测和规避"
echo "   • 实时攻击监控和分析"
echo "   • 深度社会工程学实验"
echo ""
echo "🔧 核心服务:"
echo "   • Web控制台: 运行中 (PID: $WEB_PID)"
echo "   • Redis缓存: $(docker ps | grep redis > /dev/null && echo "运行中" || echo "未运行")"
echo "   • PostgreSQL: $(docker ps | grep postgres > /dev/null && echo "运行中" || echo "未运行")"
echo "   • Ollama AI: $(docker ps | grep ollama > /dev/null && echo "运行中" || echo "未运行")"
echo ""
echo "⚠️  安全警告:"
echo "   • 本系统包含极其危险的攻击工具"
echo "   • 仅限授权安全研究使用"
echo "   • 所有活动都有完整审计日志"
echo "   • 请遵守相关法律法规"
echo ""
echo "📚 使用指南:"
echo "   • 查看项目概述: http://localhost:5003/project_overview"
echo "   • 停止系统: ./stop_advanced_phishing.sh"
echo "   • 查看日志: tail -f logs/web_console.log"
echo ""
echo "🚀 系统就绪，开始您的高级安全研究之旅！"
echo "🎣====================================================================🎣"
