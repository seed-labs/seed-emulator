#!/usr/bin/env python3
"""
SEED邮件系统 - 预设账户创建脚本
为测试方便，自动创建一些默认邮件账户
"""

import subprocess
import time
import json

# 预设账户配置
PRESET_ACCOUNTS = [
    # seedemail.net 域名账户
    {'email': 'alice@seedemail.net', 'password': 'password123', 'domain': 'seedemail.net'},
    {'email': 'bob@seedemail.net', 'password': 'password123', 'domain': 'seedemail.net'},
    {'email': 'test@seedemail.net', 'password': 'test123', 'domain': 'seedemail.net'},
    
    # corporate.local 域名账户
    {'email': 'admin@corporate.local', 'password': 'admin123', 'domain': 'corporate.local'},
    {'email': 'manager@corporate.local', 'password': 'manager123', 'domain': 'corporate.local'},
    {'email': 'user@corporate.local', 'password': 'user123', 'domain': 'corporate.local'},
    
    # smallbiz.org 域名账户
    {'email': 'info@smallbiz.org', 'password': 'info123', 'domain': 'smallbiz.org'},
    {'email': 'support@smallbiz.org', 'password': 'support123', 'domain': 'smallbiz.org'},
    {'email': 'sales@smallbiz.org', 'password': 'sales123', 'domain': 'smallbiz.org'},
]

# 邮件服务器容器映射
CONTAINER_MAP = {
    'seedemail.net': 'mail-150-seedemail',
    'corporate.local': 'mail-151-corporate',
    'smallbiz.org': 'mail-152-smallbiz'
}

def run_command(cmd):
    """执行命令并返回结果"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "命令执行超时"
    except Exception as e:
        return False, "", str(e)

def wait_for_container(container_name, max_wait=60):
    """等待容器启动并就绪"""
    print(f"🔍 等待容器 {container_name} 启动...")
    
    for i in range(max_wait):
        # 检查容器是否运行
        success, output, error = run_command(f"docker ps --filter name={container_name} --format '{{{{.Status}}}}'")
        if success and "Up" in output:
            # 再等待几秒确保服务完全启动
            time.sleep(3)
            print(f"   ✅ 容器 {container_name} 已启动")
            return True
        
        time.sleep(1)
        if i % 10 == 0:
            print(f"   ⏳ 等待中... ({i}/{max_wait})")
    
    print(f"   ❌ 容器 {container_name} 启动超时")
    return False

def create_account(email, password, container_name):
    """创建邮件账户"""
    print(f"📧 创建账户: {email}")
    
    # 使用printf管道输入密码，避免交互式输入
    cmd = f'printf "{password}\\n{password}\\n" | docker exec -i {container_name} setup email add {email}'
    success, output, error = run_command(cmd)
    
    if success:
        print(f"   ✅ 账户 {email} 创建成功")
        return True
    else:
        # 检查是否因为账户已存在而失败
        if "already exists" in error.lower() or "already exists" in output.lower():
            print(f"   ⚠️  账户 {email} 已存在")
            return True
        else:
            print(f"   ❌ 创建失败: {error}")
            return False

def verify_account(email, container_name):
    """验证账户是否存在"""
    cmd = f'docker exec {container_name} setup email list'
    success, output, error = run_command(cmd)
    
    if success and email in output:
        return True
    return False

def setup_preset_accounts():
    """设置所有预设账户"""
    print("🚀====================================================================🚀")
    print("           SEED邮件系统 - 预设账户创建")
    print("           自动创建测试用邮件账户")
    print("🚀====================================================================🚀")
    print("")
    
    # 检查Docker是否运行
    success, _, _ = run_command("docker ps")
    if not success:
        print("❌ Docker服务未运行，请先启动Docker")
        return False
    
    print("📦 检查邮件服务器容器状态...")
    
    # 等待所有容器启动
    all_ready = True
    for domain, container in CONTAINER_MAP.items():
        if not wait_for_container(container):
            print(f"❌ 容器 {container} 未就绪")
            all_ready = False
    
    if not all_ready:
        print("❌ 部分容器未就绪，请先启动邮件系统")
        return False
    
    print("")
    print("👤 开始创建预设账户...")
    
    # 创建账户
    created_count = 0
    failed_count = 0
    
    for account in PRESET_ACCOUNTS:
        email = account['email']
        password = account['password']
        domain = account['domain']
        container = CONTAINER_MAP[domain]
        
        if create_account(email, password, container):
            created_count += 1
        else:
            failed_count += 1
        
        time.sleep(1)  # 避免过快创建
    
    print("")
    print("📊 创建结果统计:")
    print(f"   ✅ 成功创建: {created_count} 个账户")
    print(f"   ❌ 创建失败: {failed_count} 个账户")
    print("")
    
    # 验证账户
    print("🔍 验证账户列表...")
    for domain, container in CONTAINER_MAP.items():
        print(f"\n📧 {domain} 邮件服务器账户:")
        cmd = f'docker exec {container} setup email list'
        success, output, error = run_command(cmd)
        
        if success:
            accounts = [line.strip() for line in output.split('\n') if '@' in line]
            for account in accounts:
                print(f"   📮 {account}")
        else:
            print(f"   ❌ 无法获取账户列表: {error}")
    
    print("")
    print("📋 预设账户信息:")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    for account in PRESET_ACCOUNTS:
        print(f"📧 {account['email']} (密码: {account['password']})")
    
    print("")
    print("💡 使用说明:")
    print("1. 在Web界面 http://localhost:5000 中测试发送邮件")
    print("2. 使用上述账户登录邮件客户端")
    print("3. 邮件客户端配置:")
    print("   - seedemail.net: SMTP localhost:2525, IMAP localhost:1430")
    print("   - corporate.local: SMTP localhost:2526, IMAP localhost:1431")  
    print("   - smallbiz.org: SMTP localhost:2527, IMAP localhost:1432")
    
    print("")
    print("🚀====================================================================🚀")
    print("                    预设账户创建完成")
    print("🚀====================================================================🚀")
    
    return True

if __name__ == '__main__':
    setup_preset_accounts()
