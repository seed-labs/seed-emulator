#!/usr/bin/env python
"""
系统测试脚本 - 检查所有组件是否正常
"""

import os
import sys
import time
import subprocess
import requests
import threading
from datetime import datetime

class SystemTester:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.test_results = {}
        
    def test_python_imports(self):
        """测试Python导入"""
        print("🔍 测试Python模块导入...")
        
        modules_to_test = [
            'flask',
            'sqlite3', 
            'hashlib',
            'uuid',
            'json',
            'datetime',
            'requests'
        ]
        
        failed_imports = []
        for module in modules_to_test:
            try:
                __import__(module)
                print(f"  ✅ {module}")
            except ImportError as e:
                print(f"  ❌ {module}: {e}")
                failed_imports.append(module)
        
        if failed_imports:
            print(f"\n❌ 以下模块导入失败: {', '.join(failed_imports)}")
            return False
        
        print("✅ 所有Python模块导入成功")
        return True
    
    def test_file_structure(self):
        """测试文件结构"""
        print("\n🔍 测试文件结构...")
        
        required_files = [
            'dashboard/dashboard.py',
            'vulnerable_servers/web_xss/xss_server.py',
            'vulnerable_servers/db_sqli/sqli_server.py', 
            'vulnerable_servers/heartbleed_sim/heartbleed_server.py',
            'advanced_security_lab.py',
            'malware_analysis/malware_sandbox.py',
            'red_blue_teams/red_blue_exercise.py',
            'IoT_security/iot_security_lab.py',
            'start_simulation.sh',
            'start_advanced_lab.sh',
            'lab_manager.py'
        ]
        
        missing_files = []
        for file_path in required_files:
            full_path = os.path.join(self.base_dir, file_path)
            if os.path.exists(full_path):
                print(f"  ✅ {file_path}")
            else:
                print(f"  ❌ {file_path}")
                missing_files.append(file_path)
        
        if missing_files:
            print(f"\n❌ 以下文件缺失: {', '.join(missing_files)}")
            return False
            
        print("✅ 所有必需文件存在")
        return True
    
    def test_python_syntax(self):
        """测试Python脚本语法"""
        print("\n🔍 测试Python脚本语法...")
        
        python_files = [
            'dashboard/dashboard.py',
            'vulnerable_servers/web_xss/xss_server.py',
            'vulnerable_servers/db_sqli/sqli_server.py',
            'vulnerable_servers/heartbleed_sim/heartbleed_server.py',
            'advanced_security_lab.py',
            'malware_analysis/malware_sandbox.py',
            'red_blue_teams/red_blue_exercise.py',
            'IoT_security/iot_security_lab.py',
            'lab_manager.py'
        ]
        
        failed_syntax = []
        for file_path in python_files:
            full_path = os.path.join(self.base_dir, file_path)
            if os.path.exists(full_path):
                try:
                    result = subprocess.run(
                        ['python', '-m', 'py_compile', full_path],
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0:
                        print(f"  ✅ {file_path}")
                    else:
                        print(f"  ❌ {file_path}: {result.stderr}")
                        failed_syntax.append(file_path)
                except Exception as e:
                    print(f"  ❌ {file_path}: {e}")
                    failed_syntax.append(file_path)
        
        if failed_syntax:
            print(f"\n❌ 以下脚本有语法错误: {', '.join(failed_syntax)}")
            return False
            
        print("✅ 所有Python脚本语法正确")
        return True
    
    def test_permissions(self):
        """测试文件权限"""
        print("\n🔍 测试文件权限...")
        
        executable_files = [
            'start_simulation.sh',
            'start_advanced_lab.sh',
            'lab_manager.py',
            'gophish'
        ]
        
        permission_issues = []
        for file_path in executable_files:
            full_path = os.path.join(self.base_dir, file_path)
            if os.path.exists(full_path):
                if os.access(full_path, os.X_OK):
                    print(f"  ✅ {file_path}")
                else:
                    print(f"  ❌ {file_path}: 不可执行")
                    permission_issues.append(file_path)
                    # 尝试修复权限
                    try:
                        os.chmod(full_path, 0o755)
                        print(f"  🔧 已修复 {file_path} 的权限")
                    except Exception as e:
                        print(f"  ❌ 无法修复 {file_path} 的权限: {e}")
        
        if permission_issues:
            print(f"\n⚠️  以下文件权限已修复: {', '.join(permission_issues)}")
        
        print("✅ 文件权限检查完成")
        return True
    
    def start_single_service(self, service_name, command, working_dir, port):
        """启动单个服务进行测试"""
        print(f"\n🚀 测试启动 {service_name}...")
        
        try:
            # 切换到工作目录
            original_dir = os.getcwd()
            os.chdir(working_dir)
            
            # 启动服务
            process = subprocess.Popen(
                command.split(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # 等待服务启动
            time.sleep(5)
            
            # 检查进程是否仍在运行
            if process.poll() is None:
                print(f"  ✅ {service_name} 启动成功 (PID: {process.pid})")
                
                # 尝试访问服务
                try:
                    url = f"http://localhost:{port}"
                    response = requests.get(url, timeout=5)
                    if response.status_code == 200:
                        print(f"  ✅ {service_name} 响应正常")
                    else:
                        print(f"  ⚠️  {service_name} 响应状态码: {response.status_code}")
                except requests.exceptions.RequestException as e:
                    print(f"  ⚠️  {service_name} 网络访问失败: {e}")
                
                # 停止服务
                process.terminate()
                process.wait(timeout=5)
                print(f"  🛑 {service_name} 已停止")
                
                os.chdir(original_dir)
                return True
            else:
                stdout, stderr = process.communicate()
                print(f"  ❌ {service_name} 启动失败")
                if stderr:
                    print(f"     错误: {stderr}")
                if stdout:
                    print(f"     输出: {stdout}")
                os.chdir(original_dir)
                return False
                
        except Exception as e:
            print(f"  ❌ {service_name} 测试异常: {e}")
            os.chdir(original_dir)
            return False
    
    def test_services(self):
        """测试所有服务启动"""
        print("\n🔍 测试服务启动...")
        
        services = [
            {
                'name': '损失评估仪表板',
                'command': 'python3 dashboard.py',
                'working_dir': os.path.join(self.base_dir, 'dashboard'),
                'port': 5000
            },
            {
                'name': 'XSS漏洞服务器',
                'command': 'python3 xss_server.py',
                'working_dir': os.path.join(self.base_dir, 'vulnerable_servers/web_xss'),
                'port': 5001
            }
        ]
        
        failed_services = []
        for service in services:
            if not self.start_single_service(
                service['name'], 
                service['command'], 
                service['working_dir'], 
                service['port']
            ):
                failed_services.append(service['name'])
        
        if failed_services:
            print(f"\n❌ 以下服务启动失败: {', '.join(failed_services)}")
            return False
        
        print("\n✅ 所有测试服务启动正常")
        return True
    
    def run_all_tests(self):
        """运行所有测试"""
        print("🧪 开始系统测试...")
        print("=" * 50)
        
        tests = [
            ("Python模块导入", self.test_python_imports),
            ("文件结构", self.test_file_structure), 
            ("Python语法", self.test_python_syntax),
            ("文件权限", self.test_permissions),
            ("服务启动", self.test_services)
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            try:
                if test_func():
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"❌ {test_name} 测试异常: {e}")
                failed += 1
        
        print("\n" + "=" * 50)
        print("🧪 测试结果总结:")
        print(f"  ✅ 通过: {passed}")
        print(f"  ❌ 失败: {failed}")
        print(f"  📊 总计: {passed + failed}")
        
        if failed == 0:
            print("\n🎉 所有测试通过！系统已准备就绪")
            return True
        else:
            print(f"\n⚠️  有 {failed} 个测试失败，请检查上述错误信息")
            return False

def main():
    """主函数"""
    tester = SystemTester()
    
    print("🎯 网络安全实验室系统测试")
    print(f"📅 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    success = tester.run_all_tests()
    
    if success:
        print("\n🚀 系统测试完成，可以开始使用实验室！")
        print("\n📋 快速启动命令:")
        print("  python3 lab_manager.py        # 交互式管理")
        print("  ./start_simulation.sh         # 启动基础系统")
        print("  ./start_advanced_lab.sh       # 启动完整实验室")
    else:
        print("\n🔧 请修复上述问题后重新测试")
    
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())
