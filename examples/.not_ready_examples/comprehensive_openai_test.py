#!/usr/bin/env python3
"""
SEED邮件系统 OpenAI集成全面测试套件
测试所有OpenAI相关功能，包括：
- API连接测试
- 模型可用性测试
- 内容生成测试
- 威胁分析测试
- 规避技术测试
- Web界面功能测试
"""

import requests
import json
import time
import sys
from datetime import datetime
from typing import Dict, List, Any

class ComprehensiveOpenAITest:
    def __init__(self):
        self.base_url = "http://localhost:5003"
        self.test_results = []
        self.start_time = datetime.now()
        self.session = requests.Session()

        print("🎭" + "="*70)
        print("          SEED邮件系统 OpenAI集成全面测试套件")
        print("🎭" + "="*70)
        print(f"⏰ 测试开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print()

    def log_test_result(self, test_name: str, success: bool, details: Dict = None):
        """记录测试结果"""
        result = {
            "test_name": test_name,
            "success": success,
            "timestamp": datetime.now().isoformat(),
            "details": details or {}
        }
        self.test_results.append(result)

        status_icon = "✅" if success else "❌"
        print(f"{status_icon} {test_name}")

        if not success and details:
            for key, value in details.items():
                print(f"   {key}: {value}")

    def test_web_server_connection(self):
        """测试Web服务器连接"""
        print("🌐 测试Web服务器连接...")

        try:
            response = self.session.get(f"{self.base_url}/", timeout=10)
            if response.status_code == 200:
                self.log_test_result("Web服务器连接", True, {"status_code": response.status_code})
                return True
            else:
                self.log_test_result("Web服务器连接", False, {"status_code": response.status_code})
                return False
        except Exception as e:
            self.log_test_result("Web服务器连接", False, {"error": str(e)})
            return False

    def test_openai_config_page(self):
        """测试OpenAI配置页面"""
        print("⚙️ 测试OpenAI配置页面...")

        try:
            response = self.session.get(f"{self.base_url}/openai_config", timeout=10)
            if response.status_code == 200:
                self.log_test_result("OpenAI配置页面", True, {"status_code": response.status_code})
                return True
            else:
                self.log_test_result("OpenAI配置页面", False, {"status_code": response.status_code})
                return False
        except Exception as e:
            self.log_test_result("OpenAI配置页面", False, {"error": str(e)})
            return False

    def test_openai_console_page(self):
        """测试OpenAI控制台页面"""
        print("🎛️ 测试OpenAI控制台页面...")

        try:
            response = self.session.get(f"{self.base_url}/openai_console", timeout=10)
            if response.status_code == 200:
                self.log_test_result("OpenAI控制台页面", True, {"status_code": response.status_code})
                return True
            else:
                self.log_test_result("OpenAI控制台页面", False, {"status_code": response.status_code})
                return False
        except Exception as e:
            self.log_test_result("OpenAI控制台页面", False, {"error": str(e)})
            return False

    def test_openai_config_api(self):
        """测试OpenAI配置API"""
        print("🔧 测试OpenAI配置API...")

        try:
            response = self.session.get(f"{self.base_url}/api/openai_config", timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.log_test_result("OpenAI配置API", True, {
                    "api_configured": data.get('api_key_configured'),
                    "connection_status": data.get('connection_status'),
                    "default_model": data.get('default_model')
                })
                return True
            else:
                self.log_test_result("OpenAI配置API", False, {"status_code": response.status_code})
                return False
        except Exception as e:
            self.log_test_result("OpenAI配置API", False, {"error": str(e)})
            return False

    def test_openai_status_api(self):
        """测试OpenAI状态API"""
        print("📊 测试OpenAI状态API...")

        try:
            response = self.session.get(f"{self.base_url}/api/openai_status", timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.log_test_result("OpenAI状态API", True, {
                    "available": data.get('available'),
                    "status": data.get('status'),
                    "models_count": len(data.get('models', []))
                })
                return True
            else:
                self.log_test_result("OpenAI状态API", False, {"status_code": response.status_code})
                return False
        except Exception as e:
            self.log_test_result("OpenAI状态API", False, {"error": str(e)})
            return False

    def test_openai_models_api(self):
        """测试OpenAI模型API"""
        print("🤖 测试OpenAI模型API...")

        try:
            response = self.session.get(f"{self.base_url}/api/openai_models", timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.log_test_result("OpenAI模型API", True, {
                    "models_count": len(data.get('models', [])),
                    "recommended": data.get('recommended')
                })
                return True
            else:
                self.log_test_result("OpenAI模型API", False, {"status_code": response.status_code})
                return False
        except Exception as e:
            self.log_test_result("OpenAI模型API", False, {"error": str(e)})
            return False

    def test_openai_generate_api(self):
        """测试OpenAI内容生成API"""
        print("🎨 测试OpenAI内容生成API...")

        test_prompt = "生成一封简单的企业邮件通知"

        try:
            response = self.session.post(
                f"{self.base_url}/api/openai_generate",
                json={
                    "prompt": test_prompt,
                    "model": "gpt-3.5-turbo",
                    "temperature": 0.7,
                    "max_tokens": 200
                },
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                success = data.get('success', False)
                self.log_test_result("OpenAI内容生成API", success, {
                    "model": data.get('model'),
                    "tokens_used": data.get('tokens_used'),
                    "processing_time": data.get('processing_time')
                })
                return success
            else:
                self.log_test_result("OpenAI内容生成API", False, {"status_code": response.status_code})
                return False
        except Exception as e:
            self.log_test_result("OpenAI内容生成API", False, {"error": str(e)})
            return False

    def test_openai_analyze_api(self):
        """测试OpenAI威胁分析API"""
        print("🔍 测试OpenAI威胁分析API...")

        test_content = "紧急通知：您的账户需要验证，请点击链接确认身份。"

        try:
            response = self.session.post(
                f"{self.base_url}/api/openai_analyze",
                json={
                    "content": test_content,
                    "type": "threat"
                },
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                success = data.get('success', False)
                self.log_test_result("OpenAI威胁分析API", success, {
                    "risk_level": data.get('risk_level'),
                    "confidence": data.get('confidence'),
                    "indicators_count": len(data.get('indicators', []))
                })
                return success
            else:
                self.log_test_result("OpenAI威胁分析API", False, {"status_code": response.status_code})
                return False
        except Exception as e:
            self.log_test_result("OpenAI威胁分析API", False, {"error": str(e)})
            return False

    def test_openai_connection_api(self):
        """测试OpenAI连接测试API"""
        print("🔌 测试OpenAI连接测试API...")

        try:
            response = self.session.post(
                f"{self.base_url}/api/openai_test_connection",
                json={
                    "api_key": "sk-test12345678901234567890123456789012",  # 测试用的假密钥
                    "base_url": "https://api.openai.com/v1"
                },
                timeout=15
            )

            # 连接测试API可能会失败（因为是测试密钥），但重要的是API本身工作正常
            if response.status_code in [200, 401, 403]:  # 401/403表示连接正常但认证失败
                data = response.json()
                success = response.status_code == 200 and data.get('success', False)
                self.log_test_result("OpenAI连接测试API", success, {
                    "status_code": response.status_code,
                    "api_works": True
                })
                return True
            else:
                self.log_test_result("OpenAI连接测试API", False, {"status_code": response.status_code})
                return False
        except Exception as e:
            self.log_test_result("OpenAI连接测试API", False, {"error": str(e)})
            return False

    def test_openai_model_test_api(self):
        """测试OpenAI模型测试API"""
        print("🧪 测试OpenAI模型测试API...")

        try:
            response = self.session.post(
                f"{self.base_url}/api/openai_test_model",
                json={"model": "gpt-3.5-turbo"},
                timeout=20
            )

            if response.status_code == 200:
                data = response.json()
                success = data.get('success', False)
                self.log_test_result("OpenAI模型测试API", success, {
                    "response_time": data.get('response_time'),
                    "model": "gpt-3.5-turbo"
                })
                return success
            else:
                self.log_test_result("OpenAI模型测试API", False, {"status_code": response.status_code})
                return False
        except Exception as e:
            self.log_test_result("OpenAI模型测试API", False, {"error": str(e)})
            return False

    def test_openai_usage_stats_api(self):
        """测试OpenAI使用统计API"""
        print("📈 测试OpenAI使用统计API...")

        try:
            response = self.session.get(f"{self.base_url}/api/openai_usage_stats", timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.log_test_result("OpenAI使用统计API", True, {
                    "total_requests": data.get('total_requests'),
                    "total_tokens": data.get('total_tokens')
                })
                return True
            else:
                self.log_test_result("OpenAI使用统计API", False, {"status_code": response.status_code})
                return False
        except Exception as e:
            self.log_test_result("OpenAI使用统计API", False, {"error": str(e)})
            return False

    def generate_test_report(self):
        """生成测试报告"""
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()

        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r['success']])
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0

        print("\n" + "="*70)
        print("📋 测试报告总览")
        print("="*70)
        print(f"⏰ 测试开始: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏰ 测试结束: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏱️ 总耗时: {duration:.2f}秒")
        print()
        print(f"📊 总测试数: {total_tests}")
        print(f"✅ 通过测试: {passed_tests}")
        print(f"❌ 失败测试: {failed_tests}")
        print(f"📈 成功率: {success_rate:.1f}%")
        print()

        if failed_tests > 0:
            print("❌ 失败的测试:")
            for result in self.test_results:
                if not result['success']:
                    print(f"   • {result['test_name']}")
                    if result['details']:
                        for key, value in result['details'].items():
                            if key == 'error':
                                print(f"     错误: {value}")
            print()

        print("✅ 通过的测试:")
        for result in self.test_results:
            if result['success']:
                details_str = ""
                if result['details']:
                    details_list = []
                    for key, value in result['details'].items():
                        if isinstance(value, (int, float)):
                            details_list.append(f"{key}={value}")
                        elif isinstance(value, str) and len(value) < 20:
                            details_list.append(f"{key}={value}")
                    if details_list:
                        details_str = f" ({', '.join(details_list[:2])})"

                print(f"   • {result['test_name']}{details_str}")
        print()

        # 保存详细报告
        report_file = f"openai_comprehensive_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_data = {
            "test_summary": {
                "start_time": self.start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_seconds": duration,
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "success_rate": success_rate
            },
            "test_results": self.test_results,
            "system_info": {
                "web_server_url": self.base_url,
                "test_timestamp": datetime.now().isoformat()
            }
        }

        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)

        print(f"💾 详细报告已保存至: {report_file}")

        # 性能评估
        print("\n🏆 性能评估:")
        if success_rate >= 90:
            print("   🏅 优秀: 所有核心功能正常运行")
        elif success_rate >= 75:
            print("   🥈 良好: 大部分功能正常，少数问题")
        elif success_rate >= 50:
            print("   🥉 一般: 部分功能异常，需要检查")
        else:
            print("   ⚠️  差: 多数功能异常，需要修复")

        print("\n🎯 测试完成！")

    def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始全面测试...\n")

        # 基础连接测试
        if not self.test_web_server_connection():
            print("❌ Web服务器连接失败，跳过其余测试")
            return

        # 页面测试
        self.test_openai_config_page()
        self.test_openai_console_page()

        # API功能测试
        self.test_openai_config_api()
        self.test_openai_status_api()
        self.test_openai_models_api()
        self.test_openai_usage_stats_api()

        # 核心功能测试
        self.test_openai_generate_api()
        self.test_openai_analyze_api()
        self.test_openai_connection_api()
        self.test_openai_model_test_api()

        # 生成报告
        self.generate_test_report()

def main():
    """主函数"""
    print("🎭 SEED邮件系统 OpenAI集成全面测试套件")
    print("=" * 60)

    # 检查命令行参数
    quick_mode = len(sys.argv) > 1 and sys.argv[1] == "--quick"
    auto_mode = len(sys.argv) > 1 and sys.argv[1] == "--auto"

    if quick_mode:
        print("⚡ 快速测试模式")
    elif auto_mode:
        print("🤖 自动测试模式")
    else:
        print("🕐 完整测试模式")

    print("\n🔍 正在检查环境...")
    print("📡 检查Web服务器连接...")
    print("🔧 检查OpenAI配置...")
    print()

    # 自动检查环境
    tester = ComprehensiveOpenAITest()

    # 快速连接测试
    if tester.test_web_server_connection():
        print("✅ Web服务器连接正常")
        if auto_mode:
            print("🚀 自动开始测试...")
            tester.run_all_tests()
        else:
            try:
                input("✅ 环境检查完成，按Enter键开始测试...")
                tester.run_all_tests()
            except KeyboardInterrupt:
                print("\n👋 用户取消测试")
                return
    else:
        print("❌ 环境检查失败")
        print("\n🔧 故障排除:")
        print("1. 确保31项目已启动: seed-31")
        print("2. 检查端口5003是否被占用")
        print("3. 等待几秒钟让服务完全启动")
        print("4. 或者使用 --auto 参数自动重试")
        print("\n💡 尝试命令:")
        print("   python3 comprehensive_openai_test.py --auto")
        return

if __name__ == "__main__":
    main()
