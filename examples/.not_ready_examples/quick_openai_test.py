#!/usr/bin/env python3
"""
快速OpenAI集成测试脚本
"""

import requests
import time
import os
from datetime import datetime

def test_basic_connection():
    """测试基本连接"""
    print("🌐 测试Web服务器连接...")
    try:
        response = requests.get("http://localhost:5003/", timeout=5)
        if response.status_code == 200:
            print("✅ Web服务器连接成功")
            return True
        else:
            print(f"❌ HTTP状态码: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 连接失败: {str(e)}")
        return False

def test_openai_config_page():
    """测试OpenAI配置页面"""
    print("⚙️ 测试OpenAI配置页面...")
    try:
        response = requests.get("http://localhost:5003/openai_config", timeout=5)
        if response.status_code == 200:
            print("✅ OpenAI配置页面可访问")
            return True
        else:
            print(f"❌ HTTP状态码: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 访问失败: {str(e)}")
        return False

def test_openai_console_page():
    """测试OpenAI控制台页面"""
    print("🎛️ 测试OpenAI控制台页面...")
    try:
        response = requests.get("http://localhost:5003/openai_console", timeout=5)
        if response.status_code == 200:
            print("✅ OpenAI控制台页面可访问")
            return True
        else:
            print(f"❌ HTTP状态码: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 访问失败: {str(e)}")
        return False

def test_openai_api_status():
    """测试OpenAI API状态"""
    print("📊 测试OpenAI API状态...")
    try:
        response = requests.get("http://localhost:5003/api/openai_status", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API状态: {data.get('status', 'unknown')}")
            print(f"📋 可用模型: {len(data.get('models', []))}个")
            return True
        else:
            print(f"❌ HTTP状态码: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API调用失败: {str(e)}")
        return False

def test_openai_generate():
    """测试OpenAI内容生成"""
    print("🎨 测试OpenAI内容生成...")
    try:
        payload = {
            "prompt": "生成一封简短的测试邮件",
            "model": "gpt-3.5-turbo",
            "temperature": 0.7,
            "max_tokens": 200
        }
        response = requests.post("http://localhost:5003/api/openai_generate",
                               json=payload, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print("✅ 内容生成成功")
                print(f"📝 生成长度: {len(data.get('content', ''))} 字符")
                print(f"🤖 使用模型: {data.get('model', 'unknown')}")
                return True
            else:
                print(f"❌ 生成失败: {data.get('error', 'unknown error')}")
                return False
        else:
            print(f"❌ HTTP状态码: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 生成请求失败: {str(e)}")
        return False

def main():
    """主函数"""
    print("🚀 OpenAI集成快速测试")
    print("=" * 40)
    print(f"⏰ 开始时间: {datetime.now().strftime('%H:%M:%S')}")
    print()

    # 检查环境
    print("🔍 环境检查...")
    if not test_basic_connection():
        print("\n❌ 基础连接失败，请确保31项目已启动")
        print("💡 启动命令: cd 31-advanced-phishing-system/web_console && python3 app.py")
        return

    print()

    # 运行所有测试
    tests = [
        test_openai_config_page,
        test_openai_console_page,
        test_openai_api_status,
        test_openai_generate
    ]

    results = []
    for test_func in tests:
        result = test_func()
        results.append(result)
        time.sleep(0.5)  # 短暂延迟避免请求过快

    print()
    print("=" * 40)
    print("📋 测试结果汇总")

    total_tests = len(results)
    passed_tests = sum(results)
    success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0

    print(f"总测试数: {total_tests}")
    print(f"通过测试: {passed_tests}")
    print(f"失败测试: {total_tests - passed_tests}")
    print(".1f")
    # 评估结果
    if success_rate >= 90:
        print("🏆 优秀: OpenAI集成运行良好")
    elif success_rate >= 75:
        print("🥈 良好: 大部分功能正常")
    elif success_rate >= 50:
        print("🥉 一般: 部分功能异常")
    else:
        print("⚠️  差: 大部分功能异常")

    print()
    print("🎯 建议:")
    if success_rate < 100:
        print("• 检查OpenAI API密钥配置")
        print("• 确认网络连接正常")
        print("• 查看Flask应用日志")
        print("• 尝试重启Web服务")

    print(f"\n⏰ 结束时间: {datetime.now().strftime('%H:%M:%S')}")

if __name__ == "__main__":
    main()
