#!/usr/bin/env python3
"""
Benchmark 管理器 - 用户交互界面。
"""

import subprocess
import time
import sys
import os
from datetime import datetime

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scenarios'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'agents'))

from scenarios import ALL_SCENARIOS, get_scenario, list_scenarios, get_scenarios_by_topology


def run(cmd, timeout=180):
    """执行命令。"""
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout + r.stderr
    except subprocess.TimeoutExpired:
        return "命令执行超时"
    except Exception as e:
        return f"命令执行错误: {str(e)}"


def cleanup_environment():
    """清理环境。"""
    print("  清理环境...")
    run("docker stop $(docker ps -aq) 2>/dev/null", timeout=60)
    run("docker rm $(docker ps -aq) 2>/dev/null", timeout=60)
    run("docker network prune -f 2>/dev/null", timeout=30)
    run("docker system prune -f 2>/dev/null", timeout=30)
    time.sleep(5)


def build_topology(topology: str):
    """编译拓扑。"""
    if topology == "RANDOM_COMPLEX_INTERNET":
        run("cd /home/zvanadium/seed-emulator && python3 benchmarks/topologies/random_complex_internet.py", timeout=300)
        return
    print(f"  编译拓扑: {topology}")

    if topology == "B00_mini_internet":
        run("cd /home/zvanadium/seed-emulator && python3 examples/internet/B00_mini_internet/mini_internet.py amd --output benchmarks/generated/mini_internet/output", timeout=120)
    elif topology == "B00_mini_internet_firewall":
        run("cd /home/zvanadium/seed-emulator && python3 benchmarks/topologies/firewall_mini_internet.py", timeout=300)
    elif topology == "B00_network_software_suite":
        run("cd /home/zvanadium/seed-emulator && python3 benchmarks/topologies/network_software_suite.py", timeout=300)
    elif topology == "B31_mini_internet_mpls":
        run("cd /home/zvanadium/seed-emulator && python3 examples/internet/B31_mini_internet_mpls/mini_internet_mpls.py amd --output benchmarks/generated/mini_internet_mpls/output", timeout=120)
    elif topology == "R02_bgp_free_core_mpls":
        run("cd /home/zvanadium/seed-emulator && python3 examples/routing/R02_bgp_free_core_mpls/bgp_free_core_mpls.py amd --output benchmarks/generated/bgp_free_core_mpls/output", timeout=120)


def start_topology(topology: str):
    """启动拓扑。"""
    if topology == "RANDOM_COMPLEX_INTERNET":
        run("cd /home/zvanadium/seed-emulator/benchmarks/generated/random_complex/output && docker compose up -d", timeout=600)
        time.sleep(30)
        return
    print(f"  启动拓扑: {topology}")

    if topology == "B00_mini_internet":
        run("cd /home/zvanadium/seed-emulator/benchmarks/generated/mini_internet/output && docker-compose up -d", timeout=180)
    elif topology == "B00_mini_internet_firewall":
        run("cd /home/zvanadium/seed-emulator/benchmarks/generated/firewall_mini_internet/output && docker-compose up -d", timeout=180)
    elif topology == "B00_network_software_suite":
        run("cd /home/zvanadium/seed-emulator/benchmarks/generated/network_software_suite/output && docker-compose up -d", timeout=600)
    elif topology == "B31_mini_internet_mpls":
        run("cd /home/zvanadium/seed-emulator/benchmarks/generated/mini_internet_mpls/output && docker-compose up -d", timeout=180)
    elif topology == "R02_bgp_free_core_mpls":
        run("cd /home/zvanadium/seed-emulator/benchmarks/generated/bgp_free_core_mpls/output && docker-compose up -d", timeout=180)

    print("  等待拓扑启动...")
    time.sleep(45)


def run_ai_diagnosis():
    """运行 AI 诊断代理。"""
    print("  运行 AI 诊断代理...")

    cmd = "timeout 90 python3 /home/zvanadium/seed-emulator/benchmarks/agents/ai_agent.py"

    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
        output = r.stdout + r.stderr

        lines = output.split('\n')
        diagnosis = {"category": "unknown", "confidence": 0.0}

        for line in lines:
            if line.startswith("类别:"):
                diagnosis["category"] = line.split(":")[1].strip()
            elif line.startswith("置信度:"):
                try:
                    confidence_str = line.split(":")[1].strip().replace("%", "")
                    diagnosis["confidence"] = float(confidence_str) / 100
                except:
                    diagnosis["confidence"] = 0.0

        return diagnosis
    except Exception as e:
        return {"category": "error", "confidence": 0.0, "error": str(e)}


def run_random_complex_diagnosis():
    from random_topology_ai_agent import RandomTopologyAIAgent
    agent = RandomTopologyAIAgent(api_key=os.environ.get("AI_API_KEY"), max_turns=10, verbose=True)
    diagnosis = agent.diagnose_interactive()
    stats = agent.api_stats
    return {"category": diagnosis.category, "confidence": diagnosis.confidence, "root_cause": diagnosis.root_cause, "api_stats": {"total_calls": stats.total_calls, "total_prompt_tokens": stats.total_prompt_tokens, "total_completion_tokens": stats.total_completion_tokens, "total_tokens": stats.total_tokens, "total_latency_ms": stats.total_latency_ms, "per_call_details": [vars(c) for c in stats.calls]}}


def generate_report(results, report_path):
    """生成测试报告。"""
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# MIMO AI 诊断代理测试报告\n\n")
        f.write(f"**日期**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        # 汇总
        correct = sum(1 for r in results if r.get('correct_diagnosis'))
        verified = sum(1 for r in results if r.get('fix_verified'))

        f.write("## 测试汇总\n\n")
        f.write(f"- **已测试**: {len(results)}\n")
        f.write(f"- **诊断正确**: {correct}/{len(results)}\n")
        f.write(f"- **修复验证通过**: {verified}/{len(results)}\n")
        f.write(f"- **诊断准确率**: {correct/len(results)*100:.1f}%\n\n")

        # 详细结果
        f.write("## 详细结果\n\n")
        f.write("| 序号 | 场景 | 拓扑 | 故障类型 | AI 诊断 | 诊断正确 | 修复验证 |\n")
        f.write("|------|------|------|----------|---------|----------|----------|\n")

        for i, r in enumerate(results, 1):
            diag_status = "✓" if r.get('correct_diagnosis') else "✗"
            fix_status = "✓" if r.get('fix_verified') else "✗"
            f.write(f"| {i} | {r['scenario']} | {r['topology']} | {r['fault_type']} | {r['ai_diagnosis']} | {diag_status} | {fix_status} |\n")

    print(f"\n报告已保存: {report_path}")


def main():
    """主程序。"""

    print("=" * 60)
    print("SEED Benchmark 管理器")
    print("=" * 60)

    while True:
        print("\n菜单:")
        print("1. 查看所有场景")
        print("2. 测试单个场景")
        print("3. 测试所有场景")
        print("4. 测试指定拓扑的场景")
        print("5. 退出")

        choice = input("\n请选择 (1-5): ").strip()

        if choice == "1":
            print("\n所有场景:")
            for i, cls in enumerate(ALL_SCENARIOS, 1):
                print(f"  {i}. {cls.name}: {cls.description} [{cls.topology}]")

        elif choice == "2":
            print("\n选择场景:")
            for i, cls in enumerate(ALL_SCENARIOS, 1):
                print(f"  {i}. {cls.name}: {cls.description}")

            try:
                idx = int(input("\n输入场景编号: ").strip()) - 1
                if 0 <= idx < len(ALL_SCENARIOS):
                    scenario_cls = ALL_SCENARIOS[idx]
                    scenario = scenario_cls()

                    # 清理环境
                    cleanup_environment()

                    # 构建并启动拓扑
                    build_topology(scenario.topology)
                    start_topology(scenario.topology)

                    # 运行测试
                    result = scenario.run_test(ai_diagnosis_func=(run_random_complex_diagnosis if scenario.topology == "RANDOM_COMPLEX_INTERNET" else run_ai_diagnosis))

                    # 生成报告
                    report_path = f"/home/zvanadium/seed-emulator/benchmarks/reports/{scenario.name}.md"
                    generate_report([result], report_path)
                else:
                    print("无效编号")
            except ValueError:
                print("请输入数字")

        elif choice == "3":
            print("\n测试所有场景...")

            results = []
            current_topology = None

            for scenario_cls in ALL_SCENARIOS:
                scenario = scenario_cls()

                # 如果拓扑不同，需要切换
                if scenario.topology != current_topology:
                    print(f"\n切换拓扑: {current_topology} -> {scenario.topology}")
                    cleanup_environment()
                    build_topology(scenario.topology)
                    start_topology(scenario.topology)
                    current_topology = scenario.topology
                else:
                    # 同拓扑，只重置环境
                    print(f"\n重置环境 (拓扑: {scenario.topology})")
                    cleanup_environment()
                    start_topology(scenario.topology)

                # 运行测试
                result = scenario.run_test(ai_diagnosis_func=(run_random_complex_diagnosis if scenario.topology == "RANDOM_COMPLEX_INTERNET" else run_ai_diagnosis))
                results.append(result)

            # 生成汇总报告
            report_path = "/home/zvanadium/seed-emulator/benchmarks/reports/ALL_SCENARIOS.md"
            generate_report(results, report_path)

        elif choice == "4":
            print("\n选择拓扑:")
            topologies = list(set(cls.topology for cls in ALL_SCENARIOS))
            for i, topo in enumerate(topologies, 1):
                print(f"  {i}. {topo}")

            try:
                idx = int(input("\n输入拓扑编号: ").strip()) - 1
                if 0 <= idx < len(topologies):
                    topology = topologies[idx]
                    scenarios = get_scenarios_by_topology(topology)

                    print(f"\n测试 {topology} 拓扑的场景...")

                    # 清理环境
                    cleanup_environment()
                    build_topology(topology)
                    start_topology(topology)

                    results = []
                    for scenario_cls in scenarios:
                        scenario = scenario_cls()
                        result = scenario.run_test(ai_diagnosis_func=(run_random_complex_diagnosis if scenario.topology == "RANDOM_COMPLEX_INTERNET" else run_ai_diagnosis))
                        results.append(result)

                    # 生成报告
                    report_path = f"/home/zvanadium/seed-emulator/benchmarks/reports/{topology}.md"
                    generate_report(results, report_path)
                else:
                    print("无效编号")
            except ValueError:
                print("请输入数字")

        elif choice == "5":
            print("退出")
            break

        else:
            print("无效选择，请重新输入")



if __name__ == "__main__":
    main()
