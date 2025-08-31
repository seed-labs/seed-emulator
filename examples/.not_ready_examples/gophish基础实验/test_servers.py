#!/usr/bin/env python3
"""
简单测试钓鱼后仿真系统是否正常工作
"""

import subprocess
import time
import requests
import threading
import os
import signal
import sys

def test_server(port, name):
    """测试单个服务器"""
    try:
        response = requests.get(f"http://localhost:{port}", timeout=5)
        if response.status_code == 200:
            print(f"✅ {name} (端口 {port}) - 正常运行")
            return True
        else:
            print(f"❌ {name} (端口 {port}) - 状态码: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ {name} (端口 {port}) - 连接失败: {e}")
        return False

def start_server_in_thread(script_path, port, name):
    """在线程中启动服务器"""
    try:
        print(f"启动 {name}...")
        process = subprocess.Popen([
            'python3', script_path
        ], cwd=os.path.dirname(script_path), 
           stdout=subprocess.DEVNULL, 
           stderr=subprocess.DEVNULL)
        
        # 等待服务器启动
        time.sleep(3)
        
        # 测试服务器
        if test_server(port, name):
            return process
        else:
            process.terminate()
            return None
            
    except Exception as e:
        print(f"❌ 启动 {name} 失败: {e}")
        return None

def main():
    print("🚀 测试钓鱼后仿真系统...")
    print("=" * 50)
    
    # 定义服务器列表
    servers = [
        ('dashboard/dashboard.py', 5000, '损失评估仪表板'),
        ('vulnerable_servers/web_xss/xss_server.py', 5001, 'XSS漏洞服务器'),
        ('vulnerable_servers/db_sqli/sqli_server.py', 5002, 'SQL注入服务器'),
        ('vulnerable_servers/heartbleed_sim/heartbleed_server.py', 5003, 'Heartbleed仿真服务器')
    ]
    
    processes = []
    
    # 启动所有服务器
    for script_path, port, name in servers:
        if os.path.exists(script_path):
            process = start_server_in_thread(script_path, port, name)
            if process:
                processes.append(process)
        else:
            print(f"❌ {name} - 文件不存在: {script_path}")
    
    print("\n" + "=" * 50)
    print("📊 系统状态总结:")
    print("=" * 50)
    
    # 再次测试所有端口
    all_working = True
    for script_path, port, name in servers:
        working = test_server(port, name)
        if not working:
            all_working = False
    
    if all_working:
        print("\n🎉 所有服务正常运行！")
        print("\n🌐 访问地址:")
        print("  - 损失评估仪表板: http://localhost:5000")
        print("  - XSS漏洞服务器: http://localhost:5001")
        print("  - SQL注入服务器: http://localhost:5002")
        print("  - Heartbleed仿真: http://localhost:5003")
        print("  - Gophish管理面板: https://localhost:3333")
        
        print("\n🔧 接下来的步骤:")
        print("1. 在浏览器中访问 https://localhost:3333")
        print("2. 使用默认用户名 admin 和系统生成的密码登录")
        print("3. 按照 GOPHISH_CONFIG.md 中的指南配置邮箱")
        print("4. 创建钓鱼邮件模板和活动")
        print("5. 在损失评估仪表板查看攻击效果")
        
        print("\n按 Ctrl+C 停止所有服务...")
        
        # 等待用户中断
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n正在停止所有服务...")
            for process in processes:
                process.terminate()
            print("✅ 所有服务已停止")
    else:
        print("\n❌ 部分服务启动失败")
        print("请检查Python依赖是否正确安装:")
        print("pip3 install flask")
        
        # 清理已启动的进程
        for process in processes:
            process.terminate()

if __name__ == "__main__":
    main()
