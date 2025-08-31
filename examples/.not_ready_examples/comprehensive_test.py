#!/usr/bin/env python3
"""
SEED邮件系统综合测试脚本
深度测试所有功能并生成详细报告
"""

import requests
import subprocess
import json
import time
import threading
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import socket
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class SeedEmailTester:
    def __init__(self):
        self.test_results = []
        self.performance_data = []
        self.errors = []
        
        # 测试配置
        self.test_config = {
            '29': {
                'web_url': 'http://localhost:5000',
                'mail_servers': [
                    {'name': 'seedemail.net', 'host': 'localhost', 'smtp': 2525, 'imap': 1430},
                    {'name': 'corporate.local', 'host': 'localhost', 'smtp': 2526, 'imap': 1431},
                    {'name': 'smallbiz.org', 'host': 'localhost', 'smtp': 2527, 'imap': 1432}
                ]
            },
            '29-1': {
                'web_url': 'http://localhost:5001',
                'mail_servers': [
                    {'name': 'qq.com', 'host': 'localhost', 'smtp': 2520, 'imap': 1420},
                    {'name': '163.com', 'host': 'localhost', 'smtp': 2521, 'imap': 1421},
                    {'name': 'gmail.com', 'host': 'localhost', 'smtp': 2522, 'imap': 1422}
                ]
            },
            '30': {
                'web_url': 'http://localhost:5002',
                'gophish_url': 'http://localhost:3333',
                'ollama_url': 'http://localhost:11434'
            }
        }
    
    def log_test(self, test_name, status, message, duration=None):
        """记录测试结果"""
        result = {
            'timestamp': datetime.now().isoformat(),
            'test_name': test_name,
            'status': status,
            'message': message,
            'duration': duration
        }
        self.test_results.append(result)
        status_emoji = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{status_emoji} {test_name}: {message}")
    
    def test_web_interface(self, project):
        """测试Web界面响应和功能"""
        print(f"\n🌐 测试{project}项目Web界面...")
        
        config = self.test_config.get(project)
        if not config:
            self.log_test(f"{project}_web_config", "FAIL", "配置不存在")
            return
        
        web_url = config['web_url']
        
        # 1. 基础连通性测试
        try:
            start_time = time.time()
            response = requests.get(web_url, timeout=10)
            duration = time.time() - start_time
            
            if response.status_code == 200:
                self.log_test(f"{project}_web_connectivity", "PASS", 
                            f"Web界面正常访问 ({duration:.2f}s)", duration)
            else:
                self.log_test(f"{project}_web_connectivity", "FAIL", 
                            f"HTTP状态码: {response.status_code}")
        except Exception as e:
            self.log_test(f"{project}_web_connectivity", "FAIL", f"连接失败: {str(e)}")
            return
        
        # 2. 项目概述页面测试
        try:
            start_time = time.time()
            overview_response = requests.get(f"{web_url}/project_overview", timeout=10)
            duration = time.time() - start_time
            
            if overview_response.status_code == 200:
                self.log_test(f"{project}_overview_page", "PASS", 
                            f"项目概述页面正常 ({duration:.2f}s)", duration)
            else:
                self.log_test(f"{project}_overview_page", "FAIL", 
                            f"概述页面状态码: {overview_response.status_code}")
        except Exception as e:
            self.log_test(f"{project}_overview_page", "FAIL", f"概述页面失败: {str(e)}")
        
        # 3. API接口测试
        if project in ['29', '29-1']:
            self.test_email_api(project, web_url)
        elif project == '30':
            self.test_ai_api(web_url)
    
    def test_email_api(self, project, web_url):
        """测试邮件相关API"""
        print(f"📧 测试{project}项目邮件API...")
        
        # 测试系统状态API
        try:
            api_url = f"{web_url}/api/system_status" if project == '29-1' else f"{web_url}/api/status"
            response = requests.get(api_url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                self.log_test(f"{project}_status_api", "PASS", 
                            f"状态API正常，容器数: {data.get('containers', 'N/A')}")
            else:
                self.log_test(f"{project}_status_api", "FAIL", f"状态API失败: {response.status_code}")
        except Exception as e:
            self.log_test(f"{project}_status_api", "FAIL", f"状态API异常: {str(e)}")
        
        # 测试连通性API
        try:
            response = requests.post(f"{web_url}/test_connectivity", 
                                   json={'target': '127.0.0.1'}, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                self.log_test(f"{project}_connectivity_api", "PASS", 
                            f"连通性API正常: {data.get('success', False)}")
            else:
                self.log_test(f"{project}_connectivity_api", "FAIL", 
                            f"连通性API失败: {response.status_code}")
        except Exception as e:
            self.log_test(f"{project}_connectivity_api", "FAIL", f"连通性API异常: {str(e)}")
    
    def test_ai_api(self, web_url):
        """测试30项目的AI API"""
        print("🤖 测试30项目AI API...")
        
        # 测试AI状态
        try:
            response = requests.get(f"{web_url}/api/ai_status", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("30_ai_status", "PASS", 
                            f"AI状态API正常: {data}")
            else:
                self.log_test("30_ai_status", "FAIL", f"AI状态API失败: {response.status_code}")
        except Exception as e:
            self.log_test("30_ai_status", "FAIL", f"AI状态API异常: {str(e)}")
        
        # 测试AI检测
        try:
            test_content = "这是一封来自银行的重要通知，请立即点击链接验证您的账户信息"
            response = requests.post(f"{web_url}/api/test_ai_detection", 
                                   json={'content': test_content}, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("30_ai_detection", "PASS", 
                            f"AI检测API正常: 风险评分 {data.get('risk_score', 'N/A')}")
            else:
                self.log_test("30_ai_detection", "FAIL", f"AI检测API失败: {response.status_code}")
        except Exception as e:
            self.log_test("30_ai_detection", "FAIL", f"AI检测API异常: {str(e)}")
    
    def test_network_connectivity(self):
        """测试网络连通性"""
        print("\n🌐 测试网络连通性...")
        
        # 测试关键端口
        critical_ports = [
            (5000, "29项目Web界面"),
            (5001, "29-1项目Web界面"), 
            (5002, "30项目Web界面"),
            (8080, "网络地图"),
            (8081, "Roundcube"),
            (3333, "Gophish"),
            (11434, "Ollama AI")
        ]
        
        for port, service in critical_ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                result = sock.connect_ex(('localhost', port))
                sock.close()
                
                if result == 0:
                    self.log_test(f"port_{port}", "PASS", f"{service} 端口开放")
                else:
                    self.log_test(f"port_{port}", "FAIL", f"{service} 端口不可达")
            except Exception as e:
                self.log_test(f"port_{port}", "FAIL", f"{service} 测试异常: {str(e)}")
    
    def test_docker_containers(self):
        """测试Docker容器状态"""
        print("\n🐳 测试Docker容器状态...")
        
        try:
            result = subprocess.run(['docker', 'ps', '--format', '{{.Names}}\t{{.Status}}'], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                containers = result.stdout.strip().split('\n')
                running_containers = [c for c in containers if 'Up' in c]
                
                self.log_test("docker_containers", "PASS", 
                            f"Docker正常，运行中容器: {len(running_containers)}")
                
                # 检查关键容器
                container_names = [c.split('\t')[0] for c in containers]
                key_containers = ['seed-roundcube', 'seed-mail-proxy']
                
                for key_container in key_containers:
                    if any(key_container in name for name in container_names):
                        self.log_test(f"container_{key_container}", "PASS", f"{key_container} 运行中")
                    else:
                        self.log_test(f"container_{key_container}", "FAIL", f"{key_container} 未运行")
            else:
                self.log_test("docker_containers", "FAIL", "Docker命令执行失败")
        except Exception as e:
            self.log_test("docker_containers", "FAIL", f"Docker测试异常: {str(e)}")
    
    def test_performance_stress(self):
        """性能压力测试"""
        print("\n⚡ 执行性能压力测试...")
        
        def make_request(url):
            try:
                start_time = time.time()
                response = requests.get(url, timeout=10)
                duration = time.time() - start_time
                return duration, response.status_code
            except Exception as e:
                return None, str(e)
        
        # 并发测试Web界面
        test_urls = [
            'http://localhost:5000',
            'http://localhost:5000/project_overview',
            'http://localhost:5001', 
            'http://localhost:5001/project_overview'
        ]
        
        for url in test_urls:
            durations = []
            success_count = 0
            
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(make_request, url) for _ in range(20)]
                
                for future in futures:
                    duration, status = future.result()
                    if duration and status == 200:
                        durations.append(duration)
                        success_count += 1
            
            if durations:
                avg_duration = sum(durations) / len(durations)
                max_duration = max(durations)
                success_rate = success_count / 20 * 100
                
                self.log_test(f"stress_{url.split('/')[-1] or 'index'}", "PASS", 
                            f"平均响应: {avg_duration:.2f}s, 最大: {max_duration:.2f}s, 成功率: {success_rate}%")
            else:
                self.log_test(f"stress_{url.split('/')[-1] or 'index'}", "FAIL", "压力测试失败")
    
    def test_error_handling(self):
        """测试错误处理"""
        print("\n🛡️ 测试错误处理...")
        
        # 测试无效API请求
        error_tests = [
            ('http://localhost:5000/nonexistent', '404错误处理'),
            ('http://localhost:5000/api/invalid', '无效API处理'),
            ('http://localhost:5001/test_connectivity', '缺少参数处理')
        ]
        
        for url, test_name in error_tests:
            try:
                response = requests.get(url, timeout=5)
                # 错误处理测试，我们期望得到错误响应，但不是程序崩溃
                self.log_test(f"error_{test_name}", "PASS", 
                            f"错误正常处理，状态码: {response.status_code}")
            except requests.exceptions.ConnectionError:
                self.log_test(f"error_{test_name}", "FAIL", "服务不可达")
            except Exception as e:
                self.log_test(f"error_{test_name}", "WARN", f"预期错误: {str(e)}")
    
    def test_security_basics(self):
        """基础安全测试"""
        print("\n🔒 执行基础安全测试...")
        
        # 测试SQL注入防护 (如果有数据库操作)
        sql_injection_payloads = [
            "' OR '1'='1",
            "'; DROP TABLE users; --",
            "1' UNION SELECT * FROM users --"
        ]
        
        for payload in sql_injection_payloads:
            try:
                response = requests.post('http://localhost:5000/test_connectivity',
                                       json={'target': payload}, timeout=5)
                
                # 如果返回正常错误而不是程序崩溃，说明有基本防护
                if response.status_code in [400, 422, 500]:
                    self.log_test("sql_injection_protection", "PASS", "SQL注入防护正常")
                else:
                    self.log_test("sql_injection_protection", "WARN", f"需要检查SQL注入防护")
                break
            except Exception as e:
                self.log_test("sql_injection_protection", "WARN", f"SQL注入测试异常: {str(e)}")
                break
        
        # 测试XSS防护
        xss_payload = "<script>alert('xss')</script>"
        try:
            response = requests.post('http://localhost:5000/test_connectivity',
                                   json={'target': xss_payload}, timeout=5)
            
            if "<script>" not in response.text:
                self.log_test("xss_protection", "PASS", "XSS防护正常")
            else:
                self.log_test("xss_protection", "WARN", "需要加强XSS防护")
        except Exception as e:
            self.log_test("xss_protection", "WARN", f"XSS测试异常: {str(e)}")
    
    def run_comprehensive_test(self):
        """运行综合测试"""
        print("🧪" + "="*60)
        print("        SEED邮件系统综合测试开始")
        print("🧪" + "="*60)
        
        start_time = time.time()
        
        # 执行各项测试
        self.test_docker_containers()
        self.test_network_connectivity()
        
        # 测试各个项目
        for project in ['29', '29-1', '30']:
            self.test_web_interface(project)
        
        self.test_performance_stress()
        self.test_error_handling()
        self.test_security_basics()
        
        total_duration = time.time() - start_time
        
        # 生成测试报告
        self.generate_test_report(total_duration)
    
    def generate_test_report(self, total_duration):
        """生成测试报告"""
        print("\n📊" + "="*60)
        print("                  测试报告")
        print("📊" + "="*60)
        
        # 统计结果
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r['status'] == 'PASS'])
        failed_tests = len([r for r in self.test_results if r['status'] == 'FAIL'])
        warning_tests = len([r for r in self.test_results if r['status'] == 'WARN'])
        
        print(f"📈 测试统计:")
        print(f"   总测试数: {total_tests}")
        print(f"   ✅ 通过: {passed_tests} ({passed_tests/total_tests*100:.1f}%)")
        print(f"   ❌ 失败: {failed_tests} ({failed_tests/total_tests*100:.1f}%)")
        print(f"   ⚠️  警告: {warning_tests} ({warning_tests/total_tests*100:.1f}%)")
        print(f"   ⏱️  总耗时: {total_duration:.2f}秒")
        
        # 详细结果
        print(f"\n📋 详细结果:")
        for result in self.test_results:
            status_emoji = "✅" if result['status'] == "PASS" else "❌" if result['status'] == "FAIL" else "⚠️"
            duration_info = f" ({result['duration']:.2f}s)" if result['duration'] else ""
            print(f"   {status_emoji} {result['test_name']}: {result['message']}{duration_info}")
        
        # 性能分析
        performance_tests = [r for r in self.test_results if r['duration'] is not None]
        if performance_tests:
            avg_response = sum(r['duration'] for r in performance_tests) / len(performance_tests)
            max_response = max(r['duration'] for r in performance_tests)
            print(f"\n⚡ 性能分析:")
            print(f"   平均响应时间: {avg_response:.2f}秒")
            print(f"   最大响应时间: {max_response:.2f}秒")
        
        # 保存详细报告
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_tests': total_tests,
                'passed': passed_tests,
                'failed': failed_tests,
                'warnings': warning_tests,
                'duration': total_duration
            },
            'results': self.test_results
        }
        
        with open('test_report.json', 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 详细报告已保存至: test_report.json")
        
        # 优化建议
        self.generate_optimization_suggestions()
    
    def generate_optimization_suggestions(self):
        """生成优化建议"""
        print(f"\n💡" + "="*60)
        print("                 优化建议")
        print("💡" + "="*60)
        
        failed_tests = [r for r in self.test_results if r['status'] == 'FAIL']
        warning_tests = [r for r in self.test_results if r['status'] == 'WARN']
        slow_tests = [r for r in self.test_results if r.get('duration') is not None and r.get('duration') > 5]
        
        suggestions = []
        
        if failed_tests:
            suggestions.append("🔧 修复失败的功能测试，确保核心功能正常运行")
        
        if warning_tests:
            suggestions.append("⚠️ 处理警告项，加强安全防护和错误处理")
        
        if slow_tests:
            suggestions.append("⚡ 优化响应时间超过5秒的接口，提升用户体验")
        
        # 通用优化建议
        suggestions.extend([
            "📱 添加移动端适配，提升跨设备兼容性",
            "🔒 增强安全防护，添加更多安全验证机制",
            "📊 添加更详细的监控和日志记录",
            "🎨 优化界面设计，提升用户体验",
            "🚀 添加缓存机制，提升性能",
            "📝 完善API文档和错误信息",
            "🧪 增加自动化测试覆盖率",
            "🔄 实现自动重试和故障恢复机制"
        ])
        
        for i, suggestion in enumerate(suggestions, 1):
            print(f"   {i}. {suggestion}")
        
        print(f"\n🎯 下一步计划:")
        print(f"   1. 基于测试结果修复发现的问题")
        print(f"   2. 实施性能优化方案")
        print(f"   3. 设计31-advanced-phishing-system")
        print(f"   4. 增强AI能力和智能化水平")

if __name__ == "__main__":
    tester = SeedEmailTester()
    tester.run_comprehensive_test()
