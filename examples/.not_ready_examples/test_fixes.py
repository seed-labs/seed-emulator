#!/usr/bin/env python3
"""
SEED邮件系统修复验证脚本
验证webmail_server.py和system_overview_app.py的修复结果
"""

import subprocess
import time
import requests
import sys

def test_webmail_server():
    """测试webmail_server.py的导入修复"""
    print("🧪 测试webmail_server.py导入修复...")

    try:
        # 测试导入
        from examples._not_ready_examples['29-email-system'].webmail_server import app
        print("✅ Flask导入成功")
        return True
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        return False

def test_system_overview():
    """测试system_overview_app.py的启动"""
    print("🧪 测试system_overview_app.py启动...")

    try:
        # 启动应用
        process = subprocess.Popen(
            ['python3', 'system_overview_app.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # 等待启动
        time.sleep(3)

        # 测试主页
        try:
            response = requests.get('http://localhost:4257/', timeout=5)
            if response.status_code == 200:
                print("✅ 主页响应正常")
                success = True
            else:
                print(f"❌ 主页响应异常: {response.status_code}")
                success = False
        except:
            print("❌ 无法连接到主页")
            success = False

        # 测试API
        try:
            response = requests.get('http://localhost:4257/api/system_status', timeout=5)
            if response.status_code == 200:
                print("✅ API响应正常")
            else:
                print(f"⚠️  API响应异常: {response.status_code}")
        except:
            print("⚠️  无法连接到API")

        # 停止应用
        process.terminate()
        process.wait()

        return success

    except Exception as e:
        print(f"❌ 启动测试失败: {e}")
        return False

def main():
    """主函数"""
    print("🚀 SEED邮件系统修复验证")
    print("=" * 40)

    # 测试webmail_server
    webmail_ok = test_webmail_server()
    print()

    # 测试system_overview
    overview_ok = test_system_overview()
    print()

    # 总结
    print("=" * 40)
    print("📋 验证结果:"    print(f"✅ webmail_server.py导入: {'通过' if webmail_ok else '失败'}")
    print(f"✅ system_overview_app.py启动: {'通过' if overview_ok else '失败'}")

    if webmail_ok and overview_ok:
        print("\n🎉 所有修复验证通过！")
        print("💡 现在可以正常使用:")
        print("   • webmail_server.py (Flask导入已修复)")
        print("   • system_overview_app.py (标签页功能已修复)")
        print("\n🌐 启动系统总览:")
        print("   python3 system_overview_app.py")
        print("   访问: http://localhost:4257")
        return 0
    else:
        print("\n⚠️  部分验证失败，请检查错误信息")
        return 1

if __name__ == "__main__":
    sys.exit(main())
