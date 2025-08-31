#!/usr/bin/env python3
"""
简单Flask测试脚本
"""

import requests
import subprocess
import time
import signal
import os

def start_flask_app():
    """启动Flask应用"""
    print("🚀 启动Flask应用...")
    os.chdir("/home/parallels/seed-email-system/examples/.not_ready_examples/31-advanced-phishing-system/web_console")

    process = subprocess.Popen(
        ["python3", "app.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    print(f"📋 Flask进程PID: {process.pid}")
    return process

def wait_for_server(process, timeout=15):
    """等待服务器启动"""
    print("⏳ 等待服务器启动...")
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            response = requests.get("http://localhost:5003/", timeout=2)
            if response.status_code == 200:
                print("✅ 服务器启动成功!")
                return True
        except:
            pass

        time.sleep(1)

    print("❌ 服务器启动超时")
    return False

def test_basic_connection():
    """测试基本连接"""
    try:
        response = requests.get("http://localhost:5003/", timeout=5)
        print(f"🌐 HTTP状态码: {response.status_code}")
        print(f"📄 响应长度: {len(response.text)} 字符")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ 连接失败: {str(e)}")
        return False

def test_openai_config():
    """测试OpenAI配置页面"""
    try:
        response = requests.get("http://localhost:5003/openai_config", timeout=5)
        print(f"⚙️ 配置页面状态码: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ 配置页面访问失败: {str(e)}")
        return False

def test_openai_api():
    """测试OpenAI API"""
    try:
        response = requests.get("http://localhost:5003/api/openai_status", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"🤖 API状态: {data.get('status', 'unknown')}")
            print(f"📋 可用模型: {len(data.get('models', []))}个")
            return True
        else:
            print(f"❌ API状态码: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API调用失败: {str(e)}")
        return False

def main():
    """主函数"""
    print("🧪 Flask应用简单测试")
    print("=" * 40)

    # 启动Flask应用
    process = start_flask_app()

    try:
        # 等待服务器启动
        if not wait_for_server(process):
            print("❌ 无法启动服务器，终止测试")
            return

        print("\n🧪 开始功能测试...")

        # 测试基本连接
        print("\n1. 测试基本连接:")
        basic_ok = test_basic_connection()

        # 测试OpenAI配置页面
        print("\n2. 测试OpenAI配置页面:")
        config_ok = test_openai_config()

        # 测试OpenAI API
        print("\n3. 测试OpenAI API:")
        api_ok = test_openai_api()

        print("\n" + "=" * 40)
        print("📋 测试结果:")
        print(f"✅ 基本连接: {'通过' if basic_ok else '失败'}")
        print(f"✅ 配置页面: {'通过' if config_ok else '失败'}")
        print(f"✅ API功能: {'通过' if api_ok else '失败'}")

        success_count = sum([basic_ok, config_ok, api_ok])
        print(f"\n🏆 总体结果: {success_count}/3 测试通过")

        if success_count == 3:
            print("🎉 所有测试通过！OpenAI集成运行良好")
        elif success_count >= 1:
            print("⚠️ 部分功能正常，建议检查配置")
        else:
            print("❌ 所有测试失败，请检查Flask应用")

    finally:
        # 清理进程
        print("\n🧹 清理测试进程...")
        try:
            process.terminate()
            process.wait(timeout=5)
            print("✅ 进程已清理")
        except:
            process.kill()
            print("⚠️ 强制终止进程")

if __name__ == "__main__":
    main()
