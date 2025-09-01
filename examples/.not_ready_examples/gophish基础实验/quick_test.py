#!/usr/bin/env python
"""
快速系统测试和修复
"""

import os
import sys
import subprocess
import time
import signal

def test_flask():
    print("🔍 测试Flask...")
    try:
        from flask import Flask
        app = Flask(__name__)
        
        @app.route('/')
        def hello():
            return '<h1>✅ Flask工作正常！</h1>'
        
        print("✅ Flask导入和创建应用成功")
        return True
    except Exception as e:
        print(f"❌ Flask测试失败: {e}")
        return False

def test_script_syntax():
    print("\n🔍 测试脚本语法...")
    scripts = [
        'dashboard/dashboard.py',
        'vulnerable_servers/web_xss/xss_server.py',
        'lab_manager.py'
    ]
    
    for script in scripts:
        try:
            result = subprocess.run([sys.executable, '-m', 'py_compile', script], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print(f"  ✅ {script}")
            else:
                print(f"  ❌ {script}: {result.stderr}")
        except Exception as e:
            print(f"  ❌ {script}: {e}")

def start_simple_service():
    print("\n🚀 启动简单测试服务...")
    
    # 创建简单的测试服务器
    test_server_code = '''
from flask import Flask
app = Flask(__name__)

@app.route('/')
def index():
    return "<h1>🎯 网络安全实验室测试页面</h1><p>服务运行正常！</p>"

if __name__ == '__main__':
    print("📍 测试服务启动在端口 5555")
    app.run(host='0.0.0.0', port=5555, debug=False)
'''
    
    with open('test_server.py', 'w') as f:
        f.write(test_server_code)
    
    try:
        # 启动服务
        process = subprocess.Popen(['python', 'test_server.py'])
        print(f"✅ 测试服务已启动 (PID: {process.pid})")
        
        # 等待服务启动
        time.sleep(3)
        
        # 测试访问
        try:
            import requests
            response = requests.get('http://localhost:5555', timeout=5)
            if response.status_code == 200:
                print("✅ 服务访问正常")
                print("🌐 访问 http://localhost:5555 查看测试页面")
            else:
                print(f"⚠️ 服务响应异常: {response.status_code}")
        except Exception as e:
            print(f"⚠️ 网络请求失败: {e}")
        
        # 清理
        print("\n🧹 清理测试服务...")
        process.terminate()
        process.wait()
        os.remove('test_server.py')
        print("✅ 清理完成")
        
        return True
        
    except Exception as e:
        print(f"❌ 服务启动失败: {e}")
        return False

def fix_permissions():
    print("\n🔧 修复文件权限...")
    executable_files = [
        'start_simulation.sh',
        'start_advanced_lab.sh', 
        'lab_manager.py',
        'gophish'
    ]
    
    for file_path in executable_files:
        if os.path.exists(file_path):
            try:
                os.chmod(file_path, 0o755)
                print(f"  ✅ {file_path}")
            except Exception as e:
                print(f"  ❌ {file_path}: {e}")

def create_logs_directory():
    print("\n📁 创建日志目录...")
    os.makedirs('logs', exist_ok=True)
    print("✅ 日志目录已创建")

def main():
    print("🎯 网络安全实验室快速测试和修复")
    print("=" * 50)
    
    # 运行测试
    tests = [
        ("Flask功能", test_flask),
        ("脚本语法", test_script_syntax),
        ("文件权限", fix_permissions),
        ("日志目录", create_logs_directory),
        ("服务启动", start_simple_service)
    ]
    
    passed = 0
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                print(f"⚠️ {test_name} 测试未完全通过")
        except Exception as e:
            print(f"❌ {test_name} 测试异常: {e}")
    
    print("\n" + "=" * 50)
    print(f"🧪 测试完成: {passed}/{len(tests)} 项通过")
    
    if passed >= len(tests) - 1:  # 允许一个测试失败
        print("\n🎉 系统基本正常，可以开始使用！")
        print("\n📋 推荐使用方式:")
        print("  python3 lab_manager.py        # 管理工具")
        print("  ./start_simulation.sh         # 基础系统")
        print("  ./start_advanced_lab.sh       # 完整实验室")
    else:
        print("\n⚠️ 系统存在一些问题，建议检查上述错误")

if __name__ == '__main__':
    main()
