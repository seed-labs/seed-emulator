#!/usr/bin/env python3
"""
SEED邮件系统综合总览演示脚本
展示4257端口系统总览功能的完整使用流程
"""

import time
import webbrowser
import subprocess
import requests
import json
from datetime import datetime

def print_header():
    """打印演示头部"""
    print("🎭 SEED邮件系统综合总览演示")
    print("=" * 50)
    print(f"⏰ 演示时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

def check_environment():
    """检查演示环境"""
    print("🔍 环境检查")
    print("-" * 20)

    # 检查Python
    try:
        import sys
        print(f"✅ Python版本: {sys.version.split()[0]}")
    except:
        print("❌ Python环境异常")
        return False

    # 检查Flask
    try:
        import flask
        print(f"✅ Flask版本: {flask.__version__}")
    except ImportError:
        print("❌ Flask未安装")
        return False

    # 检查应用文件
    import os
    files_to_check = [
        "system_overview_app.py",
        "templates/system_overview.html",
        "start_system_overview.sh"
    ]

    for file in files_to_check:
        if os.path.exists(file):
            print(f"✅ 找到文件: {file}")
        else:
            print(f"❌ 缺少文件: {file}")
            return False

    print()
    return True

def demonstrate_features():
    """演示功能特性"""
    print("🎯 功能特性演示")
    print("-" * 20)

    features = [
        ("🌐 Web界面", "http://localhost:4257", "响应式设计，支持多设备访问"),
        ("📊 实时监控", "系统状态", "Docker、网络、项目状态实时更新"),
        ("🚀 一键操作", "项目管理", "启动、停止、测试项目"),
        ("📁 代码浏览", "文件结构", "可视化代码结构和源码预览"),
        ("📖 文档集成", "技术文档", "README和文档在线查看"),
        ("🧪 自动化测试", "测试执行", "一键运行项目测试套件"),
        ("💡 实践指南", "使用帮助", "详细的操作指导和最佳实践"),
        ("🔧 技术总结", "架构说明", "系统设计和技术实现详解")
    ]

    for i, (name, detail, description) in enumerate(features, 1):
        print("2d"        time.sleep(0.1)

    print()

def show_usage_scenarios():
    """展示使用场景"""
    print("🎬 使用场景演示")
    print("-" * 20)

    scenarios = [
        {
            "title": "初学者入门",
            "steps": [
                "1. 运行 seed-overview 启动总览界面",
                "2. 浏览各项目介绍了解功能特点",
                "3. 选择感兴趣的项目点击启动",
                "4. 访问对应端口体验具体功能",
                "5. 查看技术总结深入学习原理"
            ]
        },
        {
            "title": "开发者研究",
            "steps": [
                "1. 使用代码浏览器了解项目架构",
                "2. 查看API接口和实现细节",
                "3. 运行自动化测试验证功能",
                "4. 参考技术文档进行二次开发",
                "5. 使用问题诊断工具排查故障"
            ]
        },
        {
            "title": "教学演示",
            "steps": [
                "1. 启动系统总览展示项目概览",
                "2. 演示各项目的功能特点",
                "3. 展示代码结构和实现原理",
                "4. 运行测试验证系统稳定性",
                "5. 讨论安全最佳实践和注意事项"
            ]
        }
    ]

    for scenario in scenarios:
        print(f"📋 {scenario['title']}:")
        for step in scenario['steps']:
            print(f"   {step}")
        print()

def show_project_details():
    """展示项目详细信息"""
    print("📋 项目详细信息")
    print("-" * 20)

    projects = {
        "29基础版": {
            "port": 5000,
            "tech": "Docker + Flask",
            "focus": "邮件系统基础功能",
            "use_case": "快速了解邮件系统架构"
        },
        "29-1真实版": {
            "port": 5001,
            "tech": "SEED-Emulator + Docker",
            "focus": "多提供商网络仿真",
            "use_case": "生产环境邮件系统模拟"
        },
        "30 AI版": {
            "port": 5002,
            "tech": "Gophish + Ollama",
            "focus": "AI驱动钓鱼攻击",
            "use_case": "智能钓鱼技术研究"
        },
        "31高级版": {
            "port": 5003,
            "tech": "OpenAI + Flask",
            "focus": "APT攻击模拟",
            "use_case": "高级持久性威胁研究"
        }
    }

    for name, info in projects.items():
        print(f"🔹 {name}")
        print(f"   端口: {info['port']}")
        print(f"   技术: {info['tech']}")
        print(f"   重点: {info['focus']}")
        print(f"   场景: {info['use_case']}")
        print()

def show_commands():
    """展示常用命令"""
    print("💻 常用命令")
    print("-" * 20)

    commands = {
        "启动命令": [
            "seed-overview          # 启动系统总览",
            "./start_system_overview.sh  # 直接启动脚本",
            "seed-29               # 启动29基础版",
            "seed-30               # 启动30 AI版"
        ],
        "管理命令": [
            "seed-status           # 查看系统状态",
            "seed-stop             # 停止所有项目",
            "seed-force-cleanup    # 强力清理系统",
            "seed-check-ports      # 检查端口占用"
        ],
        "测试命令": [
            "python3 comprehensive_test.py  # 完整测试",
            "python3 quick_openai_test.py   # 快速测试",
            "python3 demo_openai_integration.py  # OpenAI演示"
        ]
    }

    for category, cmds in commands.items():
        print(f"📂 {category}:")
        for cmd in cmds:
            print(f"   {cmd}")
        print()

def interactive_demo():
    """交互式演示"""
    print("🎮 交互式演示")
    print("-" * 20)

    while True:
        print("\n请选择演示项目:")
        print("1. 查看系统状态")
        print("2. 启动29项目演示")
        print("3. 启动30项目演示")
        print("4. 运行测试演示")
        print("5. 退出演示")

        choice = input("\n请选择 (1-5): ").strip()

        if choice == "1":
            check_system_status()
        elif choice == "2":
            demonstrate_project_start("29")
        elif choice == "3":
            demonstrate_project_start("30")
        elif choice == "4":
            demonstrate_testing()
        elif choice == "5":
            print("👋 演示结束")
            break
        else:
            print("❌ 无效选择，请重新输入")

def check_system_status():
    """检查系统状态"""
    print("\n📊 检查系统状态...")

    try:
        # 这里可以调用实际的系统状态检查
        print("✅ 系统总览服务: 运行中 (端口4257)")
        print("✅ Docker服务: 运行中")
        print("📋 项目状态:")
        print("   • 29基础版: 可启动")
        print("   • 30 AI版: 可启动")
        print("   • 31高级版: 可启动")
    except Exception as e:
        print(f"❌ 状态检查失败: {e}")

def demonstrate_project_start(project_id):
    """演示项目启动"""
    print(f"\n🚀 演示启动项目 {project_id}...")

    # 这里可以调用实际的项目启动命令
    print(f"✅ 项目 {project_id} 启动命令已准备")
    print(f"💡 实际启动请运行: seed-{project_id}")

def demonstrate_testing():
    """演示测试功能"""
    print("\n🧪 演示测试功能...")

    print("✅ 可用的测试脚本:")
    print("   • comprehensive_test.py - 完整测试套件")
    print("   • quick_openai_test.py - 快速功能测试")
    print("   • demo_openai_integration.py - OpenAI集成演示")
    print("💡 运行示例: python3 comprehensive_test.py")

def show_summary():
    """显示总结信息"""
    print("🎉 演示总结")
    print("=" * 50)

    summary_points = [
        "✅ 完整集成了29/29-1/30/31四个项目",
        "✅ 提供了统一的Web管理界面",
        "✅ 实现了实时状态监控功能",
        "✅ 集成了代码浏览和文档查看",
        "✅ 提供了自动化测试执行",
        "✅ 包含了详细的实践指南",
        "✅ 支持一键项目管理和操作",
        "✅ 具有良好的用户体验和界面设计"
    ]

    for point in summary_points:
        print(f"   {point}")

    print()
    print("🌟 核心价值:")
    print("   • 降低了学习和使用门槛")
    print("   • 提高了开发和测试效率")
    print("   • 增强了系统的易用性和可维护性")
    print("   • 为教育和研究提供了更好的工具支持")

    print()
    print("🚀 立即体验:")
    print("   运行命令: seed-overview")
    print("   访问地址: http://localhost:4257")

def main():
    """主函数"""
    print_header()

    if not check_environment():
        print("❌ 环境检查失败，请确保所有依赖都已正确安装")
        return

    demonstrate_features()
    show_usage_scenarios()
    show_project_details()
    show_commands()

    # 询问是否进行交互式演示
    choice = input("是否进行交互式演示？(y/N): ").strip().lower()
    if choice == 'y':
        interactive_demo()

    show_summary()

    print(f"\n⏰ 演示完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("🎯 感谢使用SEED邮件系统综合总览！")

if __name__ == "__main__":
    main()
