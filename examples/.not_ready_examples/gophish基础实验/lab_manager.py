#!/usr/bin/env python
"""
网络安全实验室管理工具
统一管理所有实验模块的启动、停止和状态监控
"""

import os
import sys
import time
import json
import signal
import subprocess
import threading
import requests
from datetime import datetime

class SecurityLabManager:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.processes = {}
        self.modules = {
            'gophish': {
                'name': 'Gophish 钓鱼平台',
                'script': './gophish',
                'port': 3333,
                'url': 'https://localhost:3333',
                'working_dir': self.base_dir
            },
            'dashboard': {
                'name': '损失评估仪表板',
                'script': 'python dashboard.py',
                'port': 5888,
                'url': 'http://localhost:5888',
                'working_dir': os.path.join(self.base_dir, 'dashboard')
            },
            'xss_server': {
                'name': 'XSS漏洞服务器',
                'script': 'python xss_server.py',
                'port': 5001,
                'url': 'http://localhost:5001',
                'working_dir': os.path.join(self.base_dir, 'vulnerable_servers/web_xss')
            },
            'sqli_server': {
                'name': 'SQL注入服务器',
                'script': 'python sqli_server.py',
                'port': 5002,
                'url': 'http://localhost:5002',
                'working_dir': os.path.join(self.base_dir, 'vulnerable_servers/db_sqli')
            },
            'heartbleed_server': {
                'name': 'Heartbleed仿真服务器',
                'script': 'python heartbleed_server.py',
                'port': 5003,
                'url': 'http://localhost:5003',
                'working_dir': os.path.join(self.base_dir, 'vulnerable_servers/heartbleed_sim')
            },
            'apt_simulator': {
                'name': 'APT攻击链仿真',
                'script': 'python advanced_security_lab.py',
                'port': 5004,
                'url': 'http://localhost:5004',
                'working_dir': self.base_dir
            },
            'malware_sandbox': {
                'name': '恶意软件分析沙箱',
                'script': 'python malware_sandbox.py',
                'port': 5005,
                'url': 'http://localhost:5005',
                'working_dir': os.path.join(self.base_dir, 'malware_analysis')
            },
            'red_blue_exercise': {
                'name': '红蓝对抗演练平台',
                'script': 'python red_blue_exercise.py',
                'port': 5006,
                'url': 'http://localhost:5006',
                'working_dir': os.path.join(self.base_dir, 'red_blue_teams')
            },
            'iot_security': {
                'name': 'IoT安全实验室',
                'script': 'python iot_security_lab.py',
                'port': 5007,
                'url': 'http://localhost:5007',
                'working_dir': os.path.join(self.base_dir, 'IoT_security')
            }
        }
        
    def start_module(self, module_id):
        """启动单个模块"""
        if module_id not in self.modules:
            print(f"❌ 未知模块: {module_id}")
            return False
            
        module = self.modules[module_id]
        
        # 检查模块是否已经运行
        if self.is_module_running(module_id):
            print(f"⚠️  {module['name']} 已经在运行")
            return True
            
        try:
            # 切换到模块工作目录
            os.chdir(module['working_dir'])
            
            # 启动进程
            process = subprocess.Popen(
                module['script'].split(),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                preexec_fn=os.setsid if os.name != 'nt' else None
            )
            
            self.processes[module_id] = process
            print(f"🚀 启动 {module['name']} (PID: {process.pid})")
            
            # 等待服务就绪
            if self.wait_for_service(module_id, timeout=30):
                print(f"✅ {module['name']} 启动成功 - {module['url']}")
                return True
            else:
                print(f"❌ {module['name']} 启动超时")
                return False
                
        except Exception as e:
            print(f"❌ 启动 {module['name']} 失败: {e}")
            return False
        finally:
            # 回到基础目录
            os.chdir(self.base_dir)
            
    def stop_module(self, module_id):
        """停止单个模块"""
        if module_id not in self.modules:
            print(f"❌ 未知模块: {module_id}")
            return False
            
        module = self.modules[module_id]
        
        # 检查进程是否存在
        if module_id in self.processes:
            process = self.processes[module_id]
            try:
                # 优雅关闭
                if os.name == 'nt':
                    process.terminate()
                else:
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                    
                # 等待进程结束
                process.wait(timeout=10)
                del self.processes[module_id]
                print(f"🛑 {module['name']} 已停止")
                return True
                
            except subprocess.TimeoutExpired:
                # 强制终止
                if os.name == 'nt':
                    process.kill()
                else:
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                del self.processes[module_id]
                print(f"🔨 强制停止 {module['name']}")
                return True
                
            except Exception as e:
                print(f"❌ 停止 {module['name']} 失败: {e}")
                return False
        else:
            print(f"⚠️  {module['name']} 未在运行")
            return True
            
    def start_all(self):
        """启动所有模块"""
        print("🚀 启动网络安全实验室...")
        print("=" * 50)
        
        success_count = 0
        total_count = len(self.modules)
        
        for module_id in self.modules:
            if self.start_module(module_id):
                success_count += 1
            time.sleep(2)  # 避免端口冲突
            
        print("=" * 50)
        print(f"📊 启动完成: {success_count}/{total_count} 个模块")
        
        if success_count == total_count:
            print("🎉 所有模块启动成功！")
            self.show_urls()
        else:
            print("⚠️  部分模块启动失败，请检查日志")
            
    def stop_all(self):
        """停止所有模块"""
        print("🛑 停止所有模块...")
        
        for module_id in list(self.processes.keys()):
            self.stop_module(module_id)
            
        print("✅ 所有模块已停止")
        
    def status(self):
        """显示所有模块状态"""
        print("📊 网络安全实验室状态")
        print("=" * 80)
        print(f"{'模块名称':<20} {'状态':<8} {'端口':<6} {'URL':<30}")
        print("-" * 80)
        
        for module_id, module in self.modules.items():
            status = "🟢 运行中" if self.is_module_running(module_id) else "🔴 已停止"
            print(f"{module['name']:<20} {status:<8} {module['port']:<6} {module['url']:<30}")
            
    def is_module_running(self, module_id):
        """检查模块是否在运行"""
        if module_id in self.processes:
            process = self.processes[module_id]
            if process.poll() is None:  # 进程仍在运行
                return True
            else:
                # 进程已结束，清理记录
                del self.processes[module_id]
                
        # 通过端口检查
        return self.is_port_open(self.modules[module_id]['port'])
        
    def is_port_open(self, port):
        """检查端口是否开放"""
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', port))
            return result == 0
            
    def wait_for_service(self, module_id, timeout=30):
        """等待服务就绪"""
        module = self.modules[module_id]
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self.is_port_open(module['port']):
                return True
            time.sleep(1)
            
        return False
        
    def show_urls(self):
        """显示所有服务URL"""
        print("\n🌐 服务访问地址:")
        print("=" * 50)
        
        categories = {
            '基础钓鱼仿真系统': ['gophish', 'dashboard', 'xss_server', 'sqli_server', 'heartbleed_server'],
            '高级安全实验室': ['apt_simulator', 'malware_sandbox', 'red_blue_exercise', 'iot_security']
        }
        
        for category, module_ids in categories.items():
            print(f"\n📋 {category}:")
            for module_id in module_ids:
                if module_id in self.modules:
                    module = self.modules[module_id]
                    status = "🟢" if self.is_module_running(module_id) else "🔴"
                    print(f"  {status} {module['name']}: {module['url']}")
                    
    def interactive_menu(self):
        """交互式菜单"""
        while True:
            print("\n" + "=" * 50)
            print("🔬 网络安全实验室管理工具")
            print("=" * 50)
            print("1. 启动所有模块")
            print("2. 停止所有模块")
            print("3. 查看状态")
            print("4. 启动单个模块")
            print("5. 停止单个模块")
            print("6. 显示访问地址")
            print("7. 退出")
            print("-" * 50)
            
            try:
                choice = input("请选择操作 (1-7): ").strip()
                
                if choice == '1':
                    self.start_all()
                elif choice == '2':
                    self.stop_all()
                elif choice == '3':
                    self.status()
                elif choice == '4':
                    self.show_module_list()
                    module_id = input("请输入模块ID: ").strip()
                    self.start_module(module_id)
                elif choice == '5':
                    self.show_module_list()
                    module_id = input("请输入模块ID: ").strip()
                    self.stop_module(module_id)
                elif choice == '6':
                    self.show_urls()
                elif choice == '7':
                    print("👋 再见！")
                    break
                else:
                    print("❌ 无效选择，请重新输入")
                    
            except KeyboardInterrupt:
                print("\n\n👋 用户中断，正在退出...")
                break
            except Exception as e:
                print(f"❌ 操作失败: {e}")
                
    def show_module_list(self):
        """显示模块列表"""
        print("\n📋 可用模块:")
        for i, (module_id, module) in enumerate(self.modules.items(), 1):
            status = "🟢" if self.is_module_running(module_id) else "🔴"
            print(f"  {status} {module_id}: {module['name']}")

def main():
    """主函数"""
    manager = SecurityLabManager()
    
    # 注册信号处理器
    def signal_handler(signum, frame):
        print("\n\n🛑 接收到中断信号，正在停止所有服务...")
        manager.stop_all()
        sys.exit(0)
        
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 命令行参数处理
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'start':
            manager.start_all()
        elif command == 'stop':
            manager.stop_all()
        elif command == 'status':
            manager.status()
        elif command == 'urls':
            manager.show_urls()
        elif command.startswith('start-'):
            module_id = command[6:]
            manager.start_module(module_id)
        elif command.startswith('stop-'):
            module_id = command[5:]
            manager.stop_module(module_id)
        else:
            print("❌ 未知命令")
            print("📋 可用命令: start, stop, status, urls, start-<module>, stop-<module>")
    else:
        # 交互式模式
        manager.interactive_menu()

if __name__ == '__main__':
    main()
