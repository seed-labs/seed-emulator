#!/usr/bin/env python3
"""
SEED邮件系统优化脚本
基于测试结果进行系统优化
"""

import os
import shutil
import json
import re
from datetime import datetime

class SeedSystemOptimizer:
    def __init__(self):
        self.optimizations = []
        self.backup_dir = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
    def log_optimization(self, optimization_type, file_path, description):
        """记录优化操作"""
        optimization = {
            'timestamp': datetime.now().isoformat(),
            'type': optimization_type,
            'file': file_path,
            'description': description
        }
        self.optimizations.append(optimization)
        print(f"✅ {optimization_type}: {description}")
    
    def backup_file(self, file_path):
        """备份文件"""
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)
        
        if os.path.exists(file_path):
            backup_path = os.path.join(self.backup_dir, os.path.basename(file_path))
            shutil.copy2(file_path, backup_path)
            return backup_path
        return None
    
    def enhance_security(self):
        """增强安全性"""
        print("\n🔒 增强系统安全性...")
        
        # 优化29项目的webmail_server.py
        webmail_server_path = "29-email-system/webmail_server.py"
        if os.path.exists(webmail_server_path):
            self.backup_file(webmail_server_path)
            
            with open(webmail_server_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 添加输入验证和SQL注入防护
            security_imports = """
import re
import html
from werkzeug.utils import secure_filename
from functools import wraps
"""
            
            # 添加输入验证函数
            validation_functions = """
def validate_input(input_str, max_length=1000, allowed_chars=None):
    \"\"\"输入验证函数\"\"\"
    if not input_str:
        return False
    
    if len(input_str) > max_length:
        return False
    
    # 检查危险字符
    dangerous_patterns = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'vbscript:',
        r'on\w+\s*=',
        r'<iframe[^>]*>.*?</iframe>',
        r'sql.*union.*select',
        r'drop\s+table',
        r'delete\s+from',
        r'insert\s+into'
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, input_str, re.IGNORECASE):
            return False
    
    return True

def sanitize_input(input_str):
    \"\"\"清理用户输入\"\"\"
    if not input_str:
        return ""
    
    # HTML转义
    sanitized = html.escape(input_str)
    
    # 移除潜在危险字符
    sanitized = re.sub(r'[<>"\\'`;]', '', sanitized)
    
    return sanitized.strip()

def require_valid_input(f):
    \"\"\"装饰器：验证输入\"\"\"
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method == 'POST':
            if request.is_json:
                data = request.get_json()
                for key, value in data.items():
                    if isinstance(value, str):
                        if not validate_input(value):
                            return jsonify({'success': False, 'message': '无效输入'}), 400
                        data[key] = sanitize_input(value)
            else:
                for key, value in request.form.items():
                    if not validate_input(value):
                        return jsonify({'success': False, 'message': '无效输入'}), 400
        return f(*args, **kwargs)
    return decorated_function
"""
            
            # 在imports后插入安全相关代码
            if "import subprocess" in content:
                content = content.replace("import subprocess", 
                                        f"import subprocess{security_imports}")
                
                # 在app创建后插入验证函数
                if "app = Flask(__name__)" in content:
                    content = content.replace("app = Flask(__name__)", 
                                            f"app = Flask(__name__)\n{validation_functions}")
                    
                    # 为关键路由添加验证装饰器
                    routes_to_secure = [
                        '@app.route(\'/test_connectivity\'',
                        '@app.route(\'/create_account\'',
                        '@app.route(\'/send_test_email\''
                    ]
                    
                    for route in routes_to_secure:
                        if route in content:
                            content = content.replace(route, f"@require_valid_input\n{route}")
                
                with open(webmail_server_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                self.log_optimization("Security", webmail_server_path, 
                                    "添加输入验证、XSS防护和SQL注入防护")
    
    def improve_error_handling(self):
        """改进错误处理"""
        print("\n🛡️ 改进错误处理...")
        
        # 为所有webmail_server.py添加全局错误处理
        webmail_servers = [
            "29-email-system/webmail_server.py",
            "29-1-email-system/webmail_server.py"
        ]
        
        for server_path in webmail_servers:
            if os.path.exists(server_path):
                self.backup_file(server_path)
                
                with open(server_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 添加全局错误处理
                error_handlers = """
@app.errorhandler(404)
def not_found_error(error):
    return render_template('error.html', 
                         error_code=404, 
                         error_message='页面未找到'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', 
                         error_code=500, 
                         error_message='服务器内部错误'), 500

@app.errorhandler(Exception)
def handle_exception(e):
    # 记录错误日志
    app.logger.error(f'未处理的异常: {str(e)}')
    
    # 返回友好的错误信息
    if app.debug:
        return str(e), 500
    else:
        return render_template('error.html', 
                             error_code=500, 
                             error_message='系统遇到了问题，请稍后重试'), 500
"""
                
                # 在if __name__ == '__main__':之前插入错误处理器
                if "if __name__ == '__main__':" in content:
                    content = content.replace("if __name__ == '__main__':", 
                                            f"{error_handlers}\nif __name__ == '__main__':")
                
                with open(server_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                self.log_optimization("Error Handling", server_path, 
                                    "添加全局错误处理器和友好错误页面")
    
    def create_error_templates(self):
        """创建错误页面模板"""
        print("\n📄 创建错误页面模板...")
        
        template_dirs = [
            "29-email-system/templates",
            "29-1-email-system/templates"
        ]
        
        error_template = """{% extends "base.html" %}

{% block title %}错误 {{ error_code }}{% endblock %}

{% block content %}
<div class="container mt-5">
    <div class="row justify-content-center">
        <div class="col-md-6">
            <div class="card border-danger">
                <div class="card-header bg-danger text-white text-center">
                    <h4><i class="fas fa-exclamation-triangle"></i> 错误 {{ error_code }}</h4>
                </div>
                <div class="card-body text-center">
                    <h5 class="card-title">{{ error_message }}</h5>
                    <p class="card-text">
                        {% if error_code == 404 %}
                        抱歉，您访问的页面不存在。
                        {% elif error_code == 500 %}
                        服务器遇到了问题，我们正在努力修复。
                        {% else %}
                        系统遇到了未知错误。
                        {% endif %}
                    </p>
                    <div class="d-grid gap-2 d-md-flex justify-content-md-center">
                        <a href="/" class="btn btn-primary">
                            <i class="fas fa-home"></i> 返回首页
                        </a>
                        <button class="btn btn-secondary" onclick="history.back()">
                            <i class="fas fa-arrow-left"></i> 返回上页
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}"""
        
        for template_dir in template_dirs:
            if os.path.exists(template_dir):
                error_template_path = os.path.join(template_dir, "error.html")
                with open(error_template_path, 'w', encoding='utf-8') as f:
                    f.write(error_template)
                
                self.log_optimization("Template", error_template_path, 
                                    "创建统一的错误页面模板")
    
    def optimize_performance(self):
        """优化性能"""
        print("\n⚡ 优化系统性能...")
        
        # 添加缓存配置
        cache_config = """
# Flask缓存配置
from flask_caching import Cache

# 配置缓存
cache_config = {
    'CACHE_TYPE': 'simple',
    'CACHE_DEFAULT_TIMEOUT': 300
}

cache = Cache(config=cache_config)
cache.init_app(app)
"""
        
        webmail_servers = [
            "29-email-system/webmail_server.py",
            "29-1-email-system/webmail_server.py"
        ]
        
        for server_path in webmail_servers:
            if os.path.exists(server_path):
                self.backup_file(server_path)
                
                with open(server_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 添加缓存导入
                if "from flask import Flask" in content and "from flask_caching import Cache" not in content:
                    content = content.replace("from flask import Flask", 
                                            "from flask import Flask\ntry:\n    from flask_caching import Cache\nexcept ImportError:\n    Cache = None")
                
                # 在app创建后添加缓存配置
                if "app = Flask(__name__)" in content and "cache = Cache" not in content:
                    cache_setup = """
# 缓存配置
if Cache:
    cache_config = {
        'CACHE_TYPE': 'simple',
        'CACHE_DEFAULT_TIMEOUT': 300
    }
    cache = Cache(config=cache_config)
    cache.init_app(app)
else:
    cache = None
"""
                    content = content.replace("app = Flask(__name__)", 
                                            f"app = Flask(__name__){cache_setup}")
                
                with open(server_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                self.log_optimization("Performance", server_path, 
                                    "添加Flask缓存支持，提升响应速度")
    
    def enhance_ui_ux(self):
        """增强UI/UX"""
        print("\n🎨 增强用户界面和体验...")
        
        # 添加加载动画CSS
        loading_css = """
/* 加载动画 */
.loading {
    display: none;
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    z-index: 9999;
}

.spinner {
    width: 40px;
    height: 40px;
    border: 4px solid #f3f3f3;
    border-top: 4px solid #007bff;
    border-radius: 50%;
    animation: spin 1s linear infinite;
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

/* 响应式优化 */
@media (max-width: 768px) {
    .container-fluid {
        padding: 10px;
    }
    
    .card {
        margin-bottom: 15px;
    }
    
    .btn {
        margin-bottom: 5px;
    }
}

/* 暗色主题支持 */
@media (prefers-color-scheme: dark) {
    .bg-light {
        background-color: #343a40 !important;
        color: #fff;
    }
    
    .card {
        background-color: #495057;
        border-color: #6c757d;
    }
    
    .text-muted {
        color: #adb5bd !important;
    }
}
"""
        
        # 添加JavaScript工具函数
        utils_js = """
// 通用工具函数
class SeedUtils {
    static showLoading() {
        const loading = document.querySelector('.loading');
        if (loading) loading.style.display = 'block';
    }
    
    static hideLoading() {
        const loading = document.querySelector('.loading');
        if (loading) loading.style.display = 'none';
    }
    
    static showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `alert alert-${type} position-fixed`;
        toast.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        toast.innerHTML = `
            ${message}
            <button type="button" class="btn-close ms-2" onclick="this.parentElement.remove()"></button>
        `;
        document.body.appendChild(toast);
        
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 5000);
    }
    
    static makeAjaxRequest(url, method = 'GET', data = null) {
        this.showLoading();
        
        const options = {
            method: method,
            headers: {
                'Content-Type': 'application/json',
            }
        };
        
        if (data) {
            options.body = JSON.stringify(data);
        }
        
        return fetch(url, options)
            .then(response => {
                this.hideLoading();
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }
                return response.json();
            })
            .catch(error => {
                this.hideLoading();
                this.showToast('请求失败: ' + error.message, 'danger');
                throw error;
            });
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    // 添加加载动画HTML
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'loading';
    loadingDiv.innerHTML = '<div class="spinner"></div>';
    document.body.appendChild(loadingDiv);
    
    // 自动表单验证
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const inputs = form.querySelectorAll('input[required], textarea[required]');
            let valid = true;
            
            inputs.forEach(input => {
                if (!input.value.trim()) {
                    input.classList.add('is-invalid');
                    valid = false;
                } else {
                    input.classList.remove('is-invalid');
                }
            });
            
            if (!valid) {
                e.preventDefault();
                SeedUtils.showToast('请填写所有必填字段', 'warning');
            }
        });
    });
});
"""
        
        # 更新base.html模板
        base_templates = [
            "29-email-system/templates/base.html",
            "29-1-email-system/templates/base.html"
        ]
        
        for template_path in base_templates:
            if os.path.exists(template_path):
                self.backup_file(template_path)
                
                with open(template_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 在</head>前添加CSS
                if "</head>" in content and "/* 加载动画 */" not in content:
                    content = content.replace("</head>", f"<style>{loading_css}</style>\n</head>")
                
                # 在</body>前添加JavaScript
                if "</body>" in content and "class SeedUtils" not in content:
                    content = content.replace("</body>", f"<script>{utils_js}</script>\n</body>")
                
                with open(template_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                self.log_optimization("UI/UX", template_path, 
                                    "添加加载动画、响应式设计和暗色主题支持")
    
    def add_monitoring(self):
        """添加监控功能"""
        print("\n📊 添加系统监控...")
        
        monitoring_code = """
import psutil
import logging
from logging.handlers import RotatingFileHandler

# 配置日志
if not app.debug:
    handler = RotatingFileHandler('seed_email.log', maxBytes=10240000, backupCount=10)
    handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    handler.setLevel(logging.INFO)
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('SEED邮件系统启动')

@app.route('/api/system_health')
def system_health():
    \"\"\"系统健康检查\"\"\"
    try:
        health_data = {
            'timestamp': datetime.now().isoformat(),
            'status': 'healthy',
            'system': {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': psutil.disk_usage('/').percent,
                'uptime': time.time() - app.start_time if hasattr(app, 'start_time') else 0
            },
            'services': {
                'web_server': True,
                'docker': check_docker_status(),
                'database': check_database_status()
            }
        }
        
        # 健康状态判断
        if health_data['system']['cpu_percent'] > 90:
            health_data['status'] = 'warning'
        if health_data['system']['memory_percent'] > 85:
            health_data['status'] = 'critical'
        
        return jsonify(health_data)
    except Exception as e:
        app.logger.error(f'健康检查失败: {str(e)}')
        return jsonify({'status': 'error', 'message': str(e)}), 500

def check_docker_status():
    \"\"\"检查Docker状态\"\"\"
    try:
        result = subprocess.run(['docker', 'ps'], capture_output=True, timeout=5)
        return result.returncode == 0
    except:
        return False

def check_database_status():
    \"\"\"检查数据库状态\"\"\"
    # 这里可以添加数据库连接检查
    return True
"""
        
        webmail_servers = [
            "29-email-system/webmail_server.py",
            "29-1-email-system/webmail_server.py"
        ]
        
        for server_path in webmail_servers:
            if os.path.exists(server_path):
                self.backup_file(server_path)
                
                with open(server_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 添加psutil导入
                if "import time" in content and "import psutil" not in content:
                    content = content.replace("import time", "import time\ntry:\n    import psutil\nexcept ImportError:\n    psutil = None")
                
                # 在if __name__ == '__main__':之前添加监控代码
                if "if __name__ == '__main__':" in content and "system_health" not in content:
                    content = content.replace("if __name__ == '__main__':", 
                                            f"{monitoring_code}\nif __name__ == '__main__':")
                
                with open(server_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                self.log_optimization("Monitoring", server_path, 
                                    "添加系统健康检查和日志记录")
    
    def run_optimization(self):
        """运行全面优化"""
        print("🔧" + "="*60)
        print("        SEED邮件系统优化开始")
        print("🔧" + "="*60)
        
        # 执行各项优化
        self.enhance_security()
        self.improve_error_handling()
        self.create_error_templates()
        self.optimize_performance()
        self.enhance_ui_ux()
        self.add_monitoring()
        
        # 生成优化报告
        self.generate_optimization_report()
    
    def generate_optimization_report(self):
        """生成优化报告"""
        print("\n📊" + "="*60)
        print("                优化完成报告")
        print("📊" + "="*60)
        
        print(f"📈 优化统计:")
        print(f"   总优化项: {len(self.optimizations)}")
        
        optimization_types = {}
        for opt in self.optimizations:
            opt_type = opt['type']
            optimization_types[opt_type] = optimization_types.get(opt_type, 0) + 1
        
        for opt_type, count in optimization_types.items():
            print(f"   {opt_type}: {count}项")
        
        print(f"\n📋 详细优化:")
        for opt in self.optimizations:
            print(f"   ✅ {opt['type']}: {opt['description']}")
        
        # 保存优化报告
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'backup_dir': self.backup_dir,
            'optimizations': self.optimizations,
            'summary': optimization_types
        }
        
        with open('optimization_report.json', 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 优化报告已保存至: optimization_report.json")
        print(f"🗂️  文件备份目录: {self.backup_dir}")
        
        print(f"\n🎯 优化效果:")
        print(f"   🔒 安全性: 添加输入验证、XSS防护、错误处理")
        print(f"   ⚡ 性能: 添加缓存支持、优化响应时间")
        print(f"   🎨 用户体验: 响应式设计、加载动画、暗色主题")
        print(f"   📊 监控: 健康检查、日志记录、系统状态")

if __name__ == "__main__":
    optimizer = SeedSystemOptimizer()
    optimizer.run_optimization()
