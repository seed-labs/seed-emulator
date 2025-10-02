#!/usr/bin/env python3
"""
自动化框架集成测试脚本
Automated Framework Integration Test Script

该脚本用于测试所有自动化框架的集成是否正常工作
"""

import sys
import os
import json
import time
import logging
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def setup_logging():
    """设置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('test_results/automation_test.log'),
            logging.StreamHandler()
        ]
    )

def test_gophish_integration():
    """测试Gophish集成"""
    print("测试Gophish集成...")
    try:
        from automation_frameworks.gophish_integration import GophishIntegration

        # 注意：这只是测试导入和初始化，不会实际运行钓鱼活动
        gophish = GophishIntegration()
        print("✓ Gophish集成模块导入成功")

        # 测试配置加载
        if hasattr(gophish, 'config') and gophish.config:
            print("✓ Gophish配置加载成功")
            return True
        else:
            print("✗ Gophish配置加载失败")
            return False

    except ImportError as e:
        print(f"✗ Gophish集成模块导入失败: {e}")
        return False
    except Exception as e:
        print(f"✗ Gophish集成测试失败: {e}")
        return False

def test_aurora_demos_integration():
    """测试Aurora-demos集成"""
    print("测试Aurora-demos集成...")
    try:
        from automation_frameworks.aurora_demos_integration import AuroraDemosIntegration

        aurora = AuroraDemosIntegration()
        print("✓ Aurora-demos集成模块导入成功")

        # 测试配置加载
        if hasattr(aurora, 'config') and aurora.config:
            print("✓ Aurora-demos配置加载成功")
            return True
        else:
            print("✗ Aurora-demos配置加载失败")
            return False

    except ImportError as e:
        print(f"✗ Aurora-demos集成模块导入失败: {e}")
        return False
    except Exception as e:
        print(f"✗ Aurora-demos集成测试失败: {e}")
        return False

def test_pentest_agent_integration():
    """测试PentestAgent集成"""
    print("测试PentestAgent集成...")
    try:
        from automation_frameworks.pentest_agent_integration import PentestAgentIntegration

        pentest = PentestAgentIntegration()
        print("✓ PentestAgent集成模块导入成功")

        # 测试配置加载
        if hasattr(pentest, 'config') and pentest.config:
            print("✓ PentestAgent配置加载成功")
            return True
        else:
            print("✗ PentestAgent配置加载失败")
            return False

    except ImportError as e:
        print(f"✗ PentestAgent集成模块导入失败: {e}")
        return False
    except Exception as e:
        print(f"✗ PentestAgent集成测试失败: {e}")
        return False

def test_unified_integrator():
    """测试统一集成器"""
    print("测试统一集成器...")
    try:
        from automation_frameworks.unified_integrator import UnifiedAutomationIntegrator

        integrator = UnifiedAutomationIntegrator()
        print("✓ 统一集成器导入成功")

        # 测试框架状态
        status = integrator.get_framework_status()
        if status and 'frameworks' in status:
            print("✓ 框架状态检查成功")
            print(f"  已加载框架: {list(status['frameworks'].keys())}")
            return True
        else:
            print("✗ 框架状态检查失败")
            return False

    except ImportError as e:
        print(f"✗ 统一集成器导入失败: {e}")
        return False
    except Exception as e:
        print(f"✗ 统一集成器测试失败: {e}")
        return False

def test_configuration_files():
    """测试配置文件"""
    print("测试配置文件...")

    config_files = [
        "automation_frameworks/unified_config.json",
        "automation_frameworks/gophish_config.json",
        "automation_frameworks/aurora_config.yaml",
        "automation_frameworks/pentest_agent_config.json"
    ]

    all_valid = True

    for config_file in config_files:
        try:
            if config_file.endswith('.json'):
                with open(config_file, 'r', encoding='utf-8') as f:
                    json.load(f)
                print(f"✓ {config_file} 格式正确")
            elif config_file.endswith('.yaml'):
                import yaml
                with open(config_file, 'r', encoding='utf-8') as f:
                    yaml.safe_load(f)
                print(f"✓ {config_file} 格式正确")
        except Exception as e:
            print(f"✗ {config_file} 格式错误: {e}")
            all_valid = False

    return all_valid

def run_integration_test():
    """运行集成测试"""
    print("开始自动化框架集成测试...")
    print("=" * 50)

    test_results = {}

    # 测试配置文件
    test_results['config_files'] = test_configuration_files()
    print()

    # 测试各个框架
    test_results['gophish'] = test_gophish_integration()
    print()

    test_results['aurora_demos'] = test_aurora_demos_integration()
    print()

    test_results['pentest_agent'] = test_pentest_agent_integration()
    print()

    test_results['unified_integrator'] = test_unified_integrator()
    print()

    # 生成测试报告
    generate_test_report(test_results)

    # 输出总结
    print("=" * 50)
    print("测试总结:")

    passed = sum(1 for result in test_results.values() if result)
    total = len(test_results)

    for test_name, result in test_results.items():
        status = "✓ 通过" if result else "✗ 失败"
        print(f"  {test_name}: {status}")

    print(f"\n总体结果: {passed}/{total} 测试通过")

    if passed == total:
        print("🎉 所有测试通过！自动化框架集成完成。")
        return True
    else:
        print("⚠️  部分测试失败，请检查配置和依赖。")
        return False

def generate_test_report(results):
    """生成测试报告"""
    report = {
        "test_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "test_results": results,
        "summary": {
            "total_tests": len(results),
            "passed_tests": sum(1 for result in results.values() if result),
            "failed_tests": sum(1 for result in results.values() if not result)
        }
    }

    # 确保测试结果目录存在
    os.makedirs('test_results', exist_ok=True)

    with open('test_results/automation_integration_test.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print("测试报告已保存到: test_results/automation_integration_test.json")

def main():
    """主函数"""
    setup_logging()

    try:
        success = run_integration_test()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"测试过程中发生错误: {e}")
        logging.exception("测试失败")
        sys.exit(1)

if __name__ == "__main__":
    main()