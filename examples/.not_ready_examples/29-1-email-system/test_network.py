#!/usr/bin/env python3
"""
SEED 29-1邮件系统 - 网络测试脚本
独立测试29-1项目的网络连通性和功能
"""

import subprocess
import json
import time
import sys

class Network29_1Tester:
    """29-1网络系统测试器"""
    
    def __init__(self):
        self.test_results = {}
        
    def run_command(self, cmd, timeout=30):
        """执行命令并返回结果"""
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, 
                                 text=True, timeout=timeout)
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", "Command timeout"
        except Exception as e:
            return False, "", str(e)
    
    def test_container_status(self):
        """测试容器状态"""
        print("🔍 测试容器状态...")
        
        success, output, error = self.run_command(
            "cd output && docker-compose ps --format json"
        )
        
        if not success:
            self.test_results['containers'] = {
                'status': 'FAIL',
                'error': f"无法获取容器状态: {error}"
            }
            return False
        
        containers = []
        running_count = 0
        
        for line in output.strip().split('\n'):
            if line.strip():
                try:
                    container = json.loads(line)
                    containers.append(container)
                    if container.get('State') == 'running':
                        running_count += 1
                except json.JSONDecodeError:
                    continue
        
        self.test_results['containers'] = {
            'status': 'PASS',
            'total': len(containers),
            'running': running_count,
            'details': containers
        }
        
        print(f"   ✅ 容器状态: {running_count}/{len(containers)} 运行中")
        return True
    
    def test_network_connectivity(self):
        """测试网络连通性"""
        print("🌐 测试网络连通性...")
        
        # 测试目标：客户端到邮件服务商的连通性
        test_pairs = [
            ("北京用户到QQ邮箱", "as150h-host_0-10.150.0.71", "10.200.0.71"),
            ("上海用户到163邮箱", "as151h-host_0-10.151.0.71", "10.201.0.71"),
            ("广州用户到Gmail", "as152h-host_0-10.152.0.71", "10.202.0.71"),
            ("企业用户到企业邮箱", "as153h-host_0-10.153.0.71", "10.204.0.71"),
        ]
        
        connectivity_results = {}
        
        for test_name, source_container, target_ip in test_pairs:
            success, output, error = self.run_command(
                f"docker exec -it {source_container} ping -c 2 {target_ip}"
            )
            
            if success and "2 received" in output:
                connectivity_results[test_name] = "PASS"
                print(f"   ✅ {test_name}")
            else:
                connectivity_results[test_name] = "FAIL"
                print(f"   ❌ {test_name}")
        
        self.test_results['connectivity'] = connectivity_results
        return len([r for r in connectivity_results.values() if r == "PASS"]) > 0
    
    def test_routing_protocols(self):
        """测试路由协议"""
        print("🛣️ 测试路由协议...")
        
        # 测试BGP路由表
        success, output, error = self.run_command(
            "docker exec -it as2brd-r100-10.100.0.2 birdc show route"
        )
        
        if success:
            route_count = len([line for line in output.split('\n') 
                             if '10.' in line and 'via' in line])
            print(f"   ✅ BGP路由表: {route_count} 条路由")
            
            self.test_results['routing'] = {
                'bgp_routes': route_count,
                'status': 'PASS' if route_count > 5 else 'WARN'
            }
        else:
            print(f"   ❌ BGP路由测试失败: {error}")
            self.test_results['routing'] = {'status': 'FAIL', 'error': error}
        
        return success
    
    def test_as_structure(self):
        """测试AS结构"""
        print("🏢 测试AS结构...")
        
        expected_ases = {
            'ISPs': [2, 3, 4],  # 三大运营商
            'Mail_Providers': [200, 201, 202, 203, 204, 205],  # 6个邮件服务商
            'Clients': [150, 151, 152, 153]  # 4个客户网络
        }
        
        total_expected = sum(len(ases) for ases in expected_ases.values())
        
        # 获取实际运行的AS
        success, output, error = self.run_command(
            "cd output && docker-compose ps | grep 'brd-' | wc -l"
        )
        
        if success:
            actual_as_count = int(output.strip())
            print(f"   ✅ AS结构: {actual_as_count}/{total_expected} 个AS运行")
            
            self.test_results['as_structure'] = {
                'expected': total_expected,
                'actual': actual_as_count,
                'status': 'PASS' if actual_as_count >= total_expected else 'WARN'
            }
        else:
            print(f"   ❌ AS结构测试失败")
            self.test_results['as_structure'] = {'status': 'FAIL'}
        
        return success
    
    def test_internet_exchanges(self):
        """测试Internet Exchange"""
        print("🔗 测试Internet Exchange...")
        
        expected_ixes = [100, 101, 102, 103]  # 北京、上海、广州、海外
        
        ix_results = {}
        for ix in expected_ixes:
            success, output, error = self.run_command(
                f"docker exec -it as{ix}brd-ix{ix}-10.{ix}.0.{ix} ip addr show"
            )
            
            if success:
                ix_results[f"IX-{ix}"] = "PASS"
                print(f"   ✅ IX-{ix} 运行正常")
            else:
                ix_results[f"IX-{ix}"] = "FAIL"
                print(f"   ❌ IX-{ix} 连接失败")
        
        self.test_results['internet_exchanges'] = ix_results
        return len([r for r in ix_results.values() if r == "PASS"]) >= 3
    
    def test_geographic_distribution(self):
        """测试地理分布"""
        print("📍 测试地理分布...")
        
        geographic_mapping = {
            "北京": [100, 150, 153, 205],  # 北京IX，北京用户，企业用户，自建邮箱
            "上海": [101, 151, 201, 204],  # 上海IX，上海用户，163邮箱，企业邮箱
            "广州": [102, 152, 200],       # 广州IX，广州用户，QQ邮箱
            "海外": [103, 202, 203]        # 海外IX，Gmail，Outlook
        }
        
        geo_results = {}
        for location, ases in geographic_mapping.items():
            working_count = 0
            for asn in ases:
                # 检查AS是否有运行的容器
                success, output, error = self.run_command(
                    f"docker ps | grep 'as{asn}' | wc -l"
                )
                if success and int(output.strip()) > 0:
                    working_count += 1
            
            coverage = working_count / len(ases)
            geo_results[location] = {
                'working': working_count,
                'total': len(ases),
                'coverage': f"{coverage:.1%}"
            }
            print(f"   {'✅' if coverage > 0.5 else '❌'} {location}: {working_count}/{len(ases)} AS运行")
        
        self.test_results['geographic_distribution'] = geo_results
        return True
    
    def generate_test_report(self):
        """生成测试报告"""
        print("\n" + "="*60)
        print("📋 SEED 29-1邮件系统测试报告")
        print("="*60)
        
        total_tests = 0
        passed_tests = 0
        
        for test_name, result in self.test_results.items():
            total_tests += 1
            
            if isinstance(result, dict) and 'status' in result:
                status = result['status']
                if status == 'PASS':
                    passed_tests += 1
                    print(f"✅ {test_name.replace('_', ' ').title()}: {status}")
                elif status == 'WARN':
                    print(f"⚠️  {test_name.replace('_', ' ').title()}: {status}")
                else:
                    print(f"❌ {test_name.replace('_', ' ').title()}: {status}")
            else:
                # 对于复杂结果，计算通过率
                if test_name == 'connectivity':
                    passed = len([r for r in result.values() if r == "PASS"])
                    total = len(result)
                    if passed > total / 2:
                        passed_tests += 1
                        print(f"✅ 网络连通性: {passed}/{total} 通过")
                    else:
                        print(f"❌ 网络连通性: {passed}/{total} 通过")
                
                elif test_name == 'internet_exchanges':
                    passed = len([r for r in result.values() if r == "PASS"])
                    total = len(result)
                    if passed >= 3:
                        passed_tests += 1
                        print(f"✅ Internet Exchange: {passed}/{total} 正常")
                    else:
                        print(f"❌ Internet Exchange: {passed}/{total} 正常")
        
        print(f"\n📊 总体结果: {passed_tests}/{total_tests} 测试通过")
        
        if passed_tests == total_tests:
            print("🎉 所有测试通过！29-1系统运行良好")
            return True
        elif passed_tests >= total_tests * 0.7:
            print("⚠️  大部分测试通过，系统基本正常")
            return True
        else:
            print("❌ 多个测试失败，系统可能存在问题")
            return False
    
    def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始测试SEED 29-1邮件系统...")
        print("="*60)
        
        # 检查output目录是否存在
        success, _, _ = self.run_command("ls output/docker-compose.yml")
        if not success:
            print("❌ 未找到output目录，请先运行: python3 email_realistic.py arm")
            return False
        
        # 运行各项测试
        tests = [
            self.test_container_status,
            self.test_as_structure,
            self.test_internet_exchanges,
            self.test_geographic_distribution,
            self.test_routing_protocols,
            self.test_network_connectivity,
        ]
        
        for test_func in tests:
            try:
                test_func()
                time.sleep(2)  # 间隔2秒
            except Exception as e:
                print(f"   ❌ 测试出错: {e}")
        
        # 生成报告
        return self.generate_test_report()

def main():
    """主函数"""
    print("""
    ╭─────────────────────────────────────────────────────────────╮
    │                SEED 29-1邮件系统网络测试工具                │
    │                     独立项目验证                           │
    ╰─────────────────────────────────────────────────────────────╯
    """)
    
    tester = Network29_1Tester()
    
    if tester.run_all_tests():
        print("\n🎊 29-1项目测试完成，系统状态良好！")
        sys.exit(0)
    else:
        print("\n⚠️  29-1项目测试发现问题，请检查系统状态")
        sys.exit(1)

if __name__ == "__main__":
    main()
