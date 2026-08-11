#!/usr/bin/env python3
"""
Benchmark CLI - 命令行调用 agent 测试场景。

用法:
  python3 benchmark_cli.py --agent <agent> --scenario <scenario>
  python3 benchmark_cli.py --agent <agent> --all
  python3 benchmark_cli.py --agent <agent> --topology <topology>

示例:
  python3 benchmark_cli.py --agent rule --scenario wrong_asn_01
  python3 benchmark_cli.py --agent ai --scenario wrong_asn_01,service_not_running_01
  python3 benchmark_cli.py --agent rule --all
  python3 benchmark_cli.py --agent ai --topology B00_mini_internet
  python3 benchmark_cli.py --list
"""

import subprocess
import time
import sys
import os
import argparse
import atexit
import json
from datetime import datetime


CONSOLE_LOG_PATH = None
_CONSOLE_LOG_HANDLE = None
_ORIGINAL_STDOUT = sys.stdout
_ORIGINAL_STDERR = sys.stderr


class TeeStream:
    """Mirror a console stream into the CLI's persistent log file."""

    def __init__(self, console, log_file):
        self.console = console
        self.log_file = log_file

    def write(self, data):
        self.console.write(data)
        self.log_file.write(data)
        self.log_file.flush()
        return len(data)

    def flush(self):
        self.console.flush()
        self.log_file.flush()

    def isatty(self):
        return self.console.isatty()

    @property
    def encoding(self):
        return self.console.encoding

    def __getattr__(self, name):
        return getattr(self.console, name)


def setup_console_logging():
    """Persist stdout and stderr under benchmarks/logs for every CLI run."""
    global CONSOLE_LOG_PATH, _CONSOLE_LOG_HANDLE
    if _CONSOLE_LOG_HANDLE is not None:
        return
    benchmarks_dir = os.path.dirname(os.path.abspath(__file__))
    logs_dir = os.path.join(benchmarks_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    CONSOLE_LOG_PATH = os.path.join(
        logs_dir, f"BENCHMARK_CLI_{stamp}_{os.getpid()}.log"
    )
    _CONSOLE_LOG_HANDLE = open(
        CONSOLE_LOG_PATH, "a", encoding="utf-8", buffering=1
    )
    sys.stdout = TeeStream(_ORIGINAL_STDOUT, _CONSOLE_LOG_HANDLE)
    sys.stderr = TeeStream(_ORIGINAL_STDERR, _CONSOLE_LOG_HANDLE)
    print(f"[CLI] 控制台日志: {CONSOLE_LOG_PATH}")


def close_console_logging():
    """Restore process streams before closing the shared log handle."""
    global _CONSOLE_LOG_HANDLE
    if _CONSOLE_LOG_HANDLE is None:
        return
    sys.stdout.flush()
    sys.stderr.flush()
    sys.stdout = _ORIGINAL_STDOUT
    sys.stderr = _ORIGINAL_STDERR
    _CONSOLE_LOG_HANDLE.close()
    _CONSOLE_LOG_HANDLE = None


atexit.register(close_console_logging)

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scenarios'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'agents'))

from scenarios import (
    ALL_SCENARIOS,
    MAIN_SCENARIOS,
    get_scenario,
    get_scenarios_by_topology,
    get_scenarios_by_track,
    list_scenarios,
)


def run(cmd, timeout=180):
    """执行命令。"""
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout + r.stderr
    except subprocess.TimeoutExpired:
        return "命令执行超时"
    except Exception as e:
        return f"命令执行错误: {str(e)}"


def run_checked(cmd, timeout=180):
    """Run infrastructure commands and fail with their bounded output."""
    try:
        completed = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"基础设施命令超时 ({timeout}s): {cmd}"
        ) from exc
    except OSError as exc:
        raise RuntimeError(f"基础设施命令无法执行: {exc}") from exc
    output = completed.stdout + completed.stderr
    if completed.returncode != 0:
        raise RuntimeError(
            f"基础设施命令失败 (exit={completed.returncode}): {cmd}\n"
            f"{output[-3000:]}"
        )
    return output


def run_checked_with_retries(cmd, timeout=180, attempts=2):
    """Retry bounded transient infrastructure failures with full auditing."""
    if attempts < 1:
        raise ValueError("attempts must be at least 1")
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            return run_checked(cmd, timeout=timeout)
        except RuntimeError as exc:
            last_error = exc
            if attempt >= attempts:
                break
            print(
                f"  基础设施命令失败，准备重试 "
                f"({attempt}/{attempts}): {str(exc)[-500:]}"
            )
            time.sleep(3)
    raise last_error


def run_argv_checked(args, timeout=180):
    """Run a command without a shell so timeout cannot orphan shell children."""
    try:
        completed = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"基础设施命令超时 ({timeout}s): {' '.join(args)}"
        ) from exc
    except OSError as exc:
        raise RuntimeError(f"基础设施命令无法执行: {exc}") from exc
    output = completed.stdout + completed.stderr
    if completed.returncode != 0:
        raise RuntimeError(
            f"基础设施命令失败 (exit={completed.returncode}): "
            f"{' '.join(args)}\n{output[-3000:]}"
        )
    return output


def cleanup_environment():
    """清理环境。"""
    print("  清理环境...")
    listed = run_argv_checked(
        ["docker", "ps", "-aq"],
        timeout=30,
    ).splitlines()
    container_ids = [item for item in listed if item.strip()]
    for offset in range(0, len(container_ids), 50):
        run_argv_checked(
            ["docker", "rm", "-f", *container_ids[offset:offset + 50]],
            timeout=300,
        )
    remaining = run_argv_checked(
        ["docker", "ps", "-aq"],
        timeout=30,
    ).splitlines()
    if any(item.strip() for item in remaining):
        raise RuntimeError(
            "容器清理后仍有残留，拒绝并发启动新拓扑"
        )
    run_argv_checked(
        ["docker", "network", "prune", "-f"],
        timeout=120,
    )


def build_topology(topology: str):
    """编译拓扑。"""
    print(f"  编译拓扑: {topology}")
    run_checked(get_topology_build_cmd(topology), timeout=600)


def get_topology_build_cmd(topology: str) -> str:
    """返回拓扑的编译命令。"""
    base = "/home/zvanadium/seed-emulator"
    if topology == "B00_mini_internet":
        return (
            f"cd {base} && python3 "
            "examples/internet/B00_mini_internet/mini_internet.py amd "
            "--output benchmarks/generated/mini_internet/output"
        )
    elif topology == "B00_mini_internet_firewall":
        return f"cd {base} && python3 benchmarks/topologies/firewall_mini_internet.py"
    elif topology == "B00_network_software_suite":
        return f"cd {base} && python3 benchmarks/topologies/network_software_suite.py"
    elif topology == "B31_mini_internet_mpls":
        return (
            f"cd {base} && python3 "
            "examples/internet/B31_mini_internet_mpls/mini_internet_mpls.py amd "
            "--output benchmarks/generated/mini_internet_mpls/output"
        )
    elif topology == "R02_bgp_free_core_mpls":
        return (
            f"cd {base} && python3 "
            "examples/routing/R02_bgp_free_core_mpls/bgp_free_core_mpls.py amd "
            "--output benchmarks/generated/bgp_free_core_mpls/output"
        )
    elif topology == "RANDOM_COMPLEX_INTERNET":
        return f"cd {base} && python3 benchmarks/topologies/random_complex_internet.py"
    else:
        return f"cd {base} && python3 examples/internet/B00_mini_internet/mini_internet.py amd"


def get_topology_path(topology: str) -> str:
    """返回拓扑的 output 目录路径。"""
    if topology == "B00_mini_internet":
        return "/home/zvanadium/seed-emulator/benchmarks/generated/mini_internet/output"
    elif topology == "B00_mini_internet_firewall":
        return "/home/zvanadium/seed-emulator/benchmarks/generated/firewall_mini_internet/output"
    elif topology == "B00_network_software_suite":
        return "/home/zvanadium/seed-emulator/benchmarks/generated/network_software_suite/output"
    elif topology == "B31_mini_internet_mpls":
        return "/home/zvanadium/seed-emulator/benchmarks/generated/mini_internet_mpls/output"
    elif topology == "R02_bgp_free_core_mpls":
        return "/home/zvanadium/seed-emulator/benchmarks/generated/bgp_free_core_mpls/output"
    elif topology == "RANDOM_COMPLEX_INTERNET":
        return "/home/zvanadium/seed-emulator/benchmarks/generated/random_complex/output"
    else:
        return "/home/zvanadium/seed-emulator/benchmarks/generated/mini_internet/output"


def _docker_exec(container: str, *args: str, timeout: int = 5) -> str:
    """Execute a probe without routing container names or arguments through a shell."""
    try:
        completed = subprocess.run(
            ["docker", "exec", container, *args],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return completed.stdout
    except (subprocess.TimeoutExpired, OSError):
        return ""


def _backend_containers(backend: str, limit: int = 6):
    """Discover BGP speakers from SEED's backend metadata instead of fixed names."""
    label = "org.seedsecuritylabs.seedemu.meta.seedemu_bgp_backend"
    try:
        completed = subprocess.run(
            [
                "docker",
                "ps",
                "--filter",
                f"label={label}={backend}",
                "--format",
                "{{.Names}}",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (subprocess.TimeoutExpired, OSError):
        return []
    return [name for name in completed.stdout.splitlines() if name][:limit]


def _count_json_established(value) -> int:
    if isinstance(value, dict):
        own = int(value.get("state") == "Established")
        return own + sum(_count_json_established(item) for item in value.values())
    if isinstance(value, list):
        return sum(_count_json_established(item) for item in value)
    return 0


def count_established_bgp_sessions():
    """Return established sessions and the backends that were actually probed."""
    established = 0
    probed = set()

    for container in _backend_containers("bird"):
        output = _docker_exec(container, "birdc", "show", "protocols")
        if output:
            probed.add("bird")
            established += sum(
                1 for line in output.splitlines() if "Established" in line
            )

    for container in _backend_containers("frr"):
        output = _docker_exec(
            container, "vtysh", "-c", "show bgp summary json"
        )
        if not output:
            continue
        probed.add("frr")
        try:
            established += _count_json_established(json.loads(output))
        except json.JSONDecodeError:
            # Older FRR builds may not support JSON. The text summary still uses
            # the literal state for peers that have not established.
            established += sum(
                1
                for line in output.splitlines()
                if "Established" in line
            )

    return established, sorted(probed)


def wait_for_bgp_convergence(max_wait: int = 120):
    """Poll both BIRD and FRR speakers discovered from topology metadata."""
    print("  等待 BGP 收敛 (轮询模式)...")
    check_interval = 5
    elapsed = 0
    last_backends = []
    while elapsed < max_wait:
        established, last_backends = count_established_bgp_sessions()

        if established >= 1:
            backends = "/".join(last_backends)
            print(
                f"  BGP 已收敛 ({established} Established sessions, "
                f"后端 {backends}, 耗时 {elapsed}s)"
            )
            return True

        backend_note = "/".join(last_backends) or "尚未发现 BGP speaker"
        print(
            f"  等待中... ({elapsed}s/{max_wait}s, "
            f"{established} Established, {backend_note})"
        )
        time.sleep(check_interval)
        elapsed += check_interval

    backend_note = "/".join(last_backends) or "未发现 BGP speaker"
    print(
        f"  超时: BGP 在 {max_wait}s 内未收敛 "
        f"({backend_note})，继续执行"
    )
    return False


def wait_for_topology_containers(topology: str, max_wait: int = 120) -> bool:
    """Require every Compose service container to exist and be running."""
    topo_path = get_topology_path(topology)
    compose = (
        ["docker", "compose"]
        if topology == "RANDOM_COMPLEX_INTERNET"
        else ["docker-compose"]
    )
    try:
        service_result = subprocess.run(
            compose + ["config", "--services"],
            cwd=topo_path,
            capture_output=True,
            text=True,
            timeout=20,
        )
        expected = {
            item
            for item in service_result.stdout.splitlines()
            if item.strip()
        }
    except (subprocess.TimeoutExpired, OSError):
        expected = set()

    deadline = time.monotonic() + max_wait
    last_problem = "未发现 Compose 容器"
    while time.monotonic() < deadline:
        try:
            ps_result = subprocess.run(
                compose + ["ps", "-aq"],
                cwd=topo_path,
                capture_output=True,
                text=True,
                timeout=20,
            )
            container_ids = [
                item for item in ps_result.stdout.splitlines() if item.strip()
            ]
            if container_ids:
                inspect_result = subprocess.run(
                    ["docker", "inspect", *container_ids],
                    capture_output=True,
                    text=True,
                    timeout=20,
                )
                documents = json.loads(inspect_result.stdout or "[]")
                stopped = []
                tolerated_dummies = 0
                role_label = "org.seedsecuritylabs.seedemu.meta.role"
                for document in documents:
                    state = document.get("State", {})
                    labels = document.get("Config", {}).get("Labels") or {}
                    if state.get("Running"):
                        continue
                    # SEED emits dependency-only dummy image services. They
                    # intentionally exit 0 and carry no node role metadata.
                    if (
                        state.get("Status") == "exited"
                        and state.get("ExitCode") == 0
                        and not labels.get(role_label)
                    ):
                        tolerated_dummies += 1
                        continue
                    stopped.append(
                        f"{document.get('Name', '').lstrip('/')}:"
                        f"{state.get('Status')}:{state.get('ExitCode')}"
                    )
                missing_count = max(0, len(expected) - len(container_ids))
                if not stopped and not missing_count:
                    active_count = len(container_ids) - tolerated_dummies
                    print(
                        f"  拓扑容器已就绪 "
                        f"({active_count} running, "
                        f"{tolerated_dummies} dependency dummies exited 0)"
                    )
                    return True
                last_problem = (
                    f"missing={missing_count}, stopped={stopped[:8]}"
                )
        except (subprocess.TimeoutExpired, OSError) as exc:
            last_problem = str(exc)
        time.sleep(3)

    print(f"  拓扑容器就绪超时: {last_problem}")
    return False


def start_topology(topology: str):
    """启动拓扑。"""
    print(f"  启动拓扑: {topology}")
    topo_path = get_topology_path(topology)
    if topology == "RANDOM_COMPLEX_INTERNET":
        run_checked_with_retries(
            f"cd {topo_path} && COMPOSE_PARALLEL_LIMIT=1 "
            "DOCKER_BUILDKIT=0 docker compose build",
            timeout=3600,
            attempts=3,
        )
        run_checked(
            f"cd {topo_path} && docker compose up -d",
            timeout=600,
        )
    elif topology in (
        "B00_mini_internet_firewall",
        "B00_network_software_suite",
    ):
        # The full mini Internet can exceed the generic 180s startup budget
        # on this VM, leaving late services in Created state.
        run_checked(
            f"cd {topo_path} && DOCKER_BUILDKIT=0 docker-compose build",
            timeout=3600,
        )
        run_checked(
            f"cd {topo_path} && docker-compose up -d",
            timeout=600,
        )
    else:
        run_checked(
            f"cd {topo_path} && docker-compose up -d",
            timeout=600,
        )
    print("  等待拓扑启动...")
    if not wait_for_topology_containers(topology, max_wait=180):
        raise RuntimeError(
            f"拓扑 {topology} 存在缺失或未运行的 Compose 服务"
        )
    if topology != "RANDOM_COMPLEX_INTERNET":
        wait_for_bgp_convergence(max_wait=120)


def recreate_topology_for_isolation(topology: str) -> bool:
    """Destroy and recreate containers so Agent side effects cannot leak."""
    topo_path = get_topology_path(topology)
    compose = (
        "docker compose"
        if topology == "RANDOM_COMPLEX_INTERNET"
        else "docker-compose"
    )
    marker = "BENCHMARK_ISOLATION_RECREATED"
    output = run(
        f"cd {topo_path} && "
        f"{compose} down --remove-orphans && "
        f"{compose} up -d && echo {marker}",
        timeout=480,
    )
    if marker not in output:
        return False
    if not wait_for_topology_containers(topology, max_wait=180):
        return False
    if topology != "RANDOM_COMPLEX_INTERNET":
        wait_for_bgp_convergence(max_wait=120)
    return True


def can_reuse_topology_between_scenarios(args, topology: str) -> bool:
    """Reuse only when the active workflow has deterministic scenario cleanup."""
    return bool(
        args.repair_eval
        or args.validate_only
        or topology == "B00_network_software_suite"
    )


def run_ai_diagnosis(max_turns=20):
    """运行 AI 诊断代理（直接调用 + API资源监控）。"""
    print("  运行 AI 诊断代理...")

    from ai_agent import AIAgent

    API_KEY = os.environ.get("AI_API_KEY")

    try:
        agent = AIAgent(api_key=API_KEY, max_turns=max_turns, verbose=True)
        diagnosis = agent.diagnose_interactive()

        result = {
            "category": diagnosis.category,
            "confidence": diagnosis.confidence,
            "root_cause": diagnosis.root_cause,
            "reasoning": getattr(diagnosis, "reasoning", ""),
            "diagnostic_commands_executed": getattr(
                agent, "diagnostic_commands_executed", []
            ),
            "diagnostic_commands_rejected": getattr(
                agent, "diagnostic_commands_rejected", []
            ),
            "turns": agent.api_stats.total_calls,
            "max_turns": max_turns,
        }

        stats = agent.api_stats
        result["api_stats"] = {
            "total_calls": stats.total_calls,
            "successful_calls": stats.successful_calls,
            "failed_calls": stats.failed_calls,
            "total_prompt_tokens": stats.total_prompt_tokens,
            "total_completion_tokens": stats.total_completion_tokens,
            "total_tokens": stats.total_tokens,
            "total_latency_ms": stats.total_latency_ms,
            "avg_latency_ms": stats.total_latency_ms / stats.successful_calls if stats.successful_calls > 0 else 0,
            "per_call_details": [
                {
                    "turn": c.turn,
                    "latency_ms": c.latency_ms,
                    "prompt_tokens": c.prompt_tokens,
                    "completion_tokens": c.completion_tokens,
                    "total_tokens": c.total_tokens,
                    "success": c.success,
                    "error": c.error,
                }
                for c in stats.calls
            ]
        }

        return result
    except Exception as e:
        return {
            "category": "error",
            "confidence": 0.0,
            "max_turns": max_turns,
            "error": str(e),
            "api_stats": None
        }


def run_ai_repair(
    scenario,
    blind=True,
    max_turns=20,
    baseline_state=None,
    current_state=None,
    repair_attempt_handler=None,
):
    """Run MIMO in end-to-end repair mode and return its executable commands."""
    print("  运行 MIMO AI 自主诊断与修复规划...")
    from ai_agent import AIAgent

    API_KEY = os.environ.get("AI_API_KEY")
    try:
        agent = AIAgent(api_key=API_KEY, max_turns=max_turns, verbose=True)
        if blind:
            task_context = (
                "## Blind benchmark mode\n"
                "The environment contains an unknown network fault. Scenario name, "
                "expected category, description, fault location, injection method, "
                "target containers, reference repair, and scenario-specific hints are "
                "intentionally withheld. Diagnose only from live evidence gathered "
                "with read-only commands, then return the category and repair_commands."
            )
        else:
            task_context = scenario.get_repair_context()
        diagnosis = agent.diagnose_interactive(
            task_context=task_context,
            repair_mode=True,
            baseline_state=baseline_state,
            current_state=current_state,
            repair_attempt_handler=repair_attempt_handler,
        )
        stats = agent.api_stats
        return {
            "category": diagnosis.category,
            "confidence": diagnosis.confidence,
            "root_cause": diagnosis.root_cause,
            "reasoning": getattr(diagnosis, "reasoning", ""),
            "repair_commands": diagnosis.repair_commands,
            "target_container": diagnosis.target_container,
            "artifact": diagnosis.artifact,
            "faulty_value": diagnosis.faulty_value,
            "expected_value": diagnosis.expected_value,
            "root_causes": getattr(diagnosis, "root_causes", []),
            "blind_mode": blind,
            "max_turns": max_turns,
            "turns": stats.total_calls,
            "diagnostic_commands_executed": getattr(
                agent, "diagnostic_commands_executed", []
            ),
            "diagnostic_commands_rejected": getattr(
                agent, "diagnostic_commands_rejected", []
            ),
            "api_stats": {
                "total_calls": stats.total_calls,
                "successful_calls": stats.successful_calls,
                "failed_calls": stats.failed_calls,
                "total_prompt_tokens": stats.total_prompt_tokens,
                "total_completion_tokens": stats.total_completion_tokens,
                "total_tokens": stats.total_tokens,
                "total_latency_ms": stats.total_latency_ms,
                "avg_latency_ms": (
                    stats.total_latency_ms / stats.successful_calls
                    if stats.successful_calls > 0 else 0
                ),
                "per_call_details": [
                    {
                        "turn": c.turn,
                        "latency_ms": c.latency_ms,
                        "prompt_tokens": c.prompt_tokens,
                        "completion_tokens": c.completion_tokens,
                        "total_tokens": c.total_tokens,
                        "success": c.success,
                        "error": c.error,
                    }
                    for c in stats.calls
                ],
            },
        }
    except Exception as exc:
        return {
            "category": "error",
            "confidence": 0.0,
            "repair_commands": [],
            "blind_mode": blind,
            "max_turns": max_turns,
            "error": str(exc),
            "api_stats": None,
        }


def run_rule_diagnosis():
    """运行规则型诊断代理。"""
    print("  运行规则型诊断代理...")

    try:
        from agent import CompleteRuleBasedAgent
        agent = CompleteRuleBasedAgent()
        diagnosis = agent.diagnose()

        return {
            "category": diagnosis.category,
            "confidence": diagnosis.confidence
        }
    except Exception as e:
        return {"category": "error", "confidence": 0.0, "error": str(e)}


def generate_report(results, report_path, agent_type):
    """生成测试报告（含API资源消耗）。"""
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# Benchmark 测试报告 - {agent_type.upper()} Agent\n\n")
        f.write(f"**日期**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        eligible_results = [
            result for result in results
            if result.get("main_score_eligible", True)
        ]
        score_results = eligible_results or results
        correct = sum(
            1 for r in score_results if r.get("correct_diagnosis")
        )
        category_correct = sum(
            1 for r in score_results if r.get(
                "category_correct", r.get("correct_diagnosis")
            )
        )
        verified = sum(1 for r in score_results if r.get("fix_verified"))

        f.write("## 测试汇总\n\n")
        f.write(f"- **Agent 类型**: {agent_type}\n")
        if CONSOLE_LOG_PATH:
            f.write(f"- **控制台日志**: `{CONSOLE_LOG_PATH}`\n")
        blind_values = {
            result.get("blind_mode")
            for result in results
            if "blind_mode" in result
        }
        if len(blind_values) == 1:
            blind_mode = blind_values.pop()
            f.write(
                f"- **测试模式**: {'盲测' if blind_mode else '指导测试'}\n"
            )
            if blind_mode:
                f.write(
                    "> 盲测不会向 Agent 提供场景名称、预期类别、故障注入、"
                    "目标容器、参考修复或场景专属提示。\n\n"
                )
        max_turn_values = {
            result.get("max_turns")
            for result in results
            if "max_turns" in result
        }
        if len(max_turn_values) == 1:
            f.write(f"- **AI 最大问询轮数**: {max_turn_values.pop()}\n")
        seed_values = {
            result.get("scenario_seed")
            for result in results
            if "scenario_seed" in result
        }
        if seed_values:
            f.write(
                "- **场景变体种子**: "
                f"`BENCHMARK_SEED={os.environ.get('BENCHMARK_SEED', '0')}`\n"
            )
        generated_suites = sorted(
            {
                result.get("generated_suite_id")
                for result in results
                if result.get("generated_suite_id")
            }
        )
        if generated_suites:
            f.write(
                "- **生成 Suite**: "
                + ", ".join(f"`{item}`" for item in generated_suites)
                + "\n"
            )
        f.write(f"- **已测试**: {len(results)}\n")
        f.write(f"- **主榜计分场景**: {len(eligible_results)}\n")
        denominator = len(score_results)
        f.write(f"- **类别正确**: {category_correct}/{denominator}\n")
        f.write(f"- **完整根因正确**: {correct}/{denominator}\n")
        f.write(f"- **修复验证通过**: {verified}/{denominator}\n")
        f.write(
            f"- **完整根因准确率**: "
            f"{correct/denominator*100:.1f}%\n\n"
        )

        f.write("## 分轨结果\n\n")
        f.write("| Track | 场景数 | 主榜计分 | 完整根因 | 修复通过 |\n")
        f.write("|---|---:|---:|---:|---:|\n")
        tracks = sorted(
            {result.get("benchmark_track", "legacy") for result in results}
        )
        for track in tracks:
            track_results = [
                result for result in results
                if result.get("benchmark_track", "legacy") == track
            ]
            track_correct = sum(
                1 for result in track_results
                if result.get("correct_diagnosis")
            )
            track_repaired = sum(
                1 for result in track_results if result.get("fix_verified")
            )
            track_eligible = sum(
                1 for result in track_results
                if result.get("main_score_eligible", True)
            )
            f.write(
                f"| {track} | {len(track_results)} | {track_eligible} | "
                f"{track_correct}/{len(track_results)} | "
                f"{track_repaired}/{len(track_results)} |\n"
            )
        f.write("\n")

        repair_results = [r for r in results if r.get("repair_evaluation")]
        if repair_results:
            submitted = sum(
                1 for r in repair_results if r.get("repair_submitted")
            )
            authorized = sum(
                1 for r in repair_results if r.get("repair_authorized")
            )
            repair_verified = sum(
                1 for r in repair_results if r.get("repair_verified")
            )
            f.write("## Agent 修复能力评估\n\n")
            f.write(f"- **修复评估场景**: {len(repair_results)}\n")
            f.write(f"- **Agent 提交修复**: {submitted}/{len(repair_results)}\n")
            f.write(f"- **至少一条命令通过白名单并执行**: {authorized}/{len(repair_results)}\n")
            f.write(
                f"- **Agent 修复验证通过**: "
                f"{repair_verified}/{len(repair_results)}\n\n"
            )
            cleanup_ok = sum(
                1 for r in repair_results
                if r.get("standard_cleanup_verified")
            )
            recreated = sum(
                1 for r in repair_results if r.get("isolation_recreated")
            )
            tainted = sum(
                1 for r in repair_results if r.get("topology_tainted")
            )
            f.write("## 跨场景隔离与安全清理\n\n")
            f.write(
                f"- **标准清理验证通过**: "
                f"{cleanup_ok}/{len(repair_results)}\n"
            )
            f.write(
                f"- **场景后拓扑重建成功**: "
                f"{recreated}/{len(repair_results)}\n"
            )
            f.write(f"- **仍处于污染状态**: {tainted}\n\n")
            f.write(
                "> 修复验证仅统计 Agent 生成且通过白名单审查后实际执行的"
                "命令；场景标准 fix 仅用于失败后的安全清理。\n\n"
            )

        # API资源消耗汇总（仅AI Agent）
        if agent_type == "ai":
            total_api_calls = sum(r.get('api_calls', 0) for r in results)
            total_prompt_tokens = sum(r.get('api_prompt_tokens', 0) for r in results)
            total_completion_tokens = sum(r.get('api_completion_tokens', 0) for r in results)
            total_tokens = sum(r.get('api_total_tokens', 0) for r in results)
            total_latency_s = sum(r.get('api_latency_ms', 0) for r in results) / 1000

            f.write("## API 资源消耗汇总\n\n")
            f.write(f"- **API 总调用次数**: {total_api_calls}\n")
            f.write(f"- **Prompt Tokens 总计**: {total_prompt_tokens:,}\n")
            f.write(f"- **Completion Tokens 总计**: {total_completion_tokens:,}\n")
            f.write(f"- **Token 总计**: {total_tokens:,}\n")
            f.write(f"- **总延迟**: {total_latency_s:.1f}s\n")
            f.write(f"- **估算成本**: ${total_tokens / 1000 * 0.002:.4f}\n\n")

        # 详细结果
        f.write("## 详细结果\n\n")
        if agent_type == "ai":
            f.write("| 序号 | 场景 | Track | 难度 | 故障类型 | 诊断结果 | 可信度 | 类别正确 | 完整根因 | 修复验证 | 耗时 | API调用 | Token | 延迟 |\n")
            f.write("|------|------|-------|------|----------|----------|--------|----------|----------|----------|------|---------|-------|------|\n")
            for i, r in enumerate(results, 1):
                diag_status = "\u2713" if r.get('correct_diagnosis') else "\u2717"
                category_status = "\u2713" if r.get(
                    "category_correct", r.get("correct_diagnosis")
                ) else "\u2717"
                fix_status = "\u2713" if r.get('fix_verified') else "\u2717"
                api_calls = r.get('api_calls', 0)
                api_tokens = r.get('api_total_tokens', 0)
                api_latency = r.get('api_latency_ms', 0) / 1000
                f.write(
                    f"| {i} | {r['scenario']} | "
                    f"{r.get('benchmark_track', 'legacy')} | "
                    f"{r.get('difficulty', 'unknown')} | "
                    f"{r['fault_type']} | {r['ai_diagnosis']} | "
                    f"{r.get('ai_confidence',0):.0%} | {category_status} | "
                    f"{diag_status} | {fix_status} | "
                    f"{r.get('duration',0):.0f}s | {api_calls} | "
                    f"{api_tokens} | {api_latency:.1f}s |\n"
                )
        else:
            f.write("| 序号 | 场景 | 拓扑 | 故障类型 | 诊断结果 | 诊断正确 | 修复验证 |\n")
            f.write("|------|------|------|----------|----------|----------|----------|\n")
            for i, r in enumerate(results, 1):
                diag_status = "\u2713" if r.get('correct_diagnosis') else "\u2717"
                fix_status = "\u2713" if r.get('fix_verified') else "\u2717"
                f.write(f"| {i} | {r['scenario']} | {r['topology']} | {r['fault_type']} | {r['ai_diagnosis']} | {diag_status} | {fix_status} |\n")

        if repair_results:
            f.write("\n## 修复门控详情\n\n")
            f.write("| 场景 | Agent 诊断 | 提交修复 | 命令执行 | 修复验证 |\n")
            f.write("|------|------------|----------|----------|----------|\n")
            for r in repair_results:
                submitted = "✓" if r.get("repair_submitted") else "✗"
                authorized = "✓" if r.get("repair_authorized") else "✗"
                repaired = "✓" if r.get("repair_verified") else "✗"
                f.write(
                    f"| {r['scenario']} | {r['ai_diagnosis']} | "
                    f"{submitted} | {authorized} | {repaired} |\n"
                )

        # 每个场景的详细API调用详情
        if agent_type == "ai":
            has_details = any(r.get('api_per_call') for r in results)
            if has_details:
                f.write("\n## API 调用详情（每场景）\n\n")
                for i, r in enumerate(results, 1):
                    api_details = r.get('api_per_call', [])
                    if api_details:
                        f.write(f"### 场景 {i}: {r['scenario']}\n\n")
                        f.write("| 轮次 | 延迟(ms) | Prompt Tokens | Completion Tokens | Total Tokens | 状态 |\n")
                        f.write("|------|----------|---------------|-------------------|--------------|------|\n")
                        for d in api_details:
                            status = "OK" if d.get('success') else f"FAIL: {d.get('error', '')[:20]}"
                            f.write(f"| {d['turn']} | {d['latency_ms']:.0f} | {d['prompt_tokens']} | {d['completion_tokens']} | {d['total_tokens']} | {status} |\n")
                        f.write("\n")
                        f.write(f"- **场景调用数**: {r.get('api_calls', 0)}\n")
                        f.write(f"- **场景Token**: {r.get('api_total_tokens', 0):,}\n")
                        f.write(f"- **场景延迟**: {r.get('api_latency_ms', 0) / 1000:.1f}s\n\n")

        if repair_results:
            f.write("\n## Agent 实际修复命令审计\n\n")
            for i, r in enumerate(repair_results, 1):
                f.write(f"### 场景 {i}: {r['scenario']}\n\n")
                proposed = r.get("repair_commands_proposed", [])
                executed = r.get("repair_commands_executed", [])
                rejected = r.get("repair_commands_rejected", [])
                rejection_details = r.get("repair_command_rejections", [])
                attempts = r.get("repair_attempts", [])
                diagnostic_executed = r.get("diagnostic_commands_executed", [])
                diagnostic_rejected = r.get("diagnostic_commands_rejected", [])
                f.write(f"- 根因判断: {r.get('root_cause', '未记录')}\n")
                f.write(
                    f"- Track/难度: {r.get('benchmark_track', 'legacy')}/"
                    f"{r.get('difficulty', 'unknown')}\n"
                )
                f.write(f"- 场景派生种子: {r.get('scenario_seed', '')}\n")
                if r.get("generated_suite_id"):
                    f.write(
                        f"- 生成 Suite: `{r['generated_suite_id']}`\n"
                    )
                    f.write(
                        "- 生成指纹: "
                        f"`{r.get('generation_fingerprint', '')}`\n"
                    )
                    f.write(
                        "- 生成契约: "
                        f"`{r.get('generation_contract_sha256', '')}`\n"
                    )
                f.write(
                    f"- 主榜计分: "
                    f"{'是' if r.get('main_score_eligible', True) else '否'}\n"
                )
                if r.get("quarantine_reason"):
                    f.write(
                        f"- 分轨原因: {r.get('quarantine_reason')}\n"
                    )
                if r.get("error"):
                    f.write(f"- 基础设施错误: {r['error']}\n")
                f.write(
                    f"- 目标容器: {r.get('target_container', [])}\n"
                )
                f.write(f"- 故障资产: {r.get('artifact', '')}\n")
                f.write(f"- 错误值: {r.get('faulty_value', '')}\n")
                f.write(f"- 期望值: {r.get('expected_value', '')}\n")
                if r.get("root_causes"):
                    f.write(
                        "- 多根因结构: "
                        f"`{json.dumps(r['root_causes'], ensure_ascii=False)}`\n"
                    )
                f.write(
                    f"- 根因字段评分: "
                    f"{r.get('diagnosis_score', 0):.0%} "
                    f"{r.get('diagnosis_score_components', {})}\n"
                )
                f.write(f"- 诊断问询轮数: {r.get('turns', 0)}\n")
                f.write(f"- 修复尝试轮数: {len(attempts)}\n")
                f.write(f"- 只读诊断命令执行: {len(diagnostic_executed)}\n")
                f.write(f"- 非只读诊断命令拒绝: {len(diagnostic_rejected)}\n")
                f.write(f"- 提议命令: {len(proposed)}\n")
                f.write(f"- 实际执行: {len(executed)}\n")
                f.write(f"- 白名单拒绝: {len(rejected)}\n")
                f.write(
                    f"- 功能验证: {'通过' if r.get('repair_verified') else '失败'}\n\n"
                )
                f.write(
                    f"- 标准清理验证: "
                    f"{'通过' if r.get('standard_cleanup_verified') else '失败'}\n"
                )
                f.write(
                    f"- 拓扑隔离重建: "
                    f"{'通过' if r.get('isolation_recreated') else '失败'}\n"
                )
                f.write(
                    f"- 污染状态: "
                    f"{'是' if r.get('topology_tainted') else '否'}\n\n"
                )
                for item in executed:
                    f.write("```sh\n")
                    f.write(item["command"] + "\n")
                    f.write("```\n\n")
                if rejected:
                    f.write("拒绝的命令：\n\n")
                    detail_by_command = {
                        item.get("command"): item.get("reason", "")
                        for item in rejection_details
                    }
                    for command in rejected:
                        f.write("```sh\n")
                        f.write(command + "\n")
                        f.write("```\n\n")
                        reason = detail_by_command.get(command)
                        if reason:
                            f.write(f"- 拒绝原因: {reason}\n\n")
                if attempts:
                    f.write("修复闭环尝试：\n\n")
                    for attempt in attempts:
                        f.write(
                            f"- 尝试 {attempt.get('attempt')}: "
                            f"executed={len(attempt.get('executions', []))}, "
                            f"rejected={len(attempt.get('rejections', []))}, "
                            f"verified={attempt.get('verified', False)}\n"
                        )
                if diagnostic_executed:
                    f.write("执行的只读诊断命令：\n\n")
                    for command in diagnostic_executed:
                        f.write(f"```sh\n{command}\n```\n\n")
                if diagnostic_rejected:
                    f.write("诊断阶段拒绝的非只读命令：\n\n")
                    for command in diagnostic_rejected:
                        f.write(f"```sh\n{command}\n```\n\n")

    print(f"\n报告已保存: {report_path}")


def main():
    """主程序。"""
    setup_console_logging()

    parser = argparse.ArgumentParser(description="Benchmark CLI - 测试场景")
    parser.add_argument("--list", action="store_true", help="列出所有场景")
    parser.add_argument("--agent", choices=["rule", "ai"], help="选择 agent 类型")
    parser.add_argument("--scenario", help="场景名称（逗号分隔）")
    parser.add_argument("--all", action="store_true", help="测试所有场景")
    parser.add_argument("--topology", help="测试指定拓扑的场景")
    parser.add_argument(
        "--track",
        choices=[
            "main",
            "network_functional",
            "network_control_plane",
            "config_lint",
            "advanced",
            "robustness",
            "all",
        ],
        help="按独立 benchmark 分轨选择场景；--all 默认仅运行主榜",
    )
    parser.add_argument("--report", help="报告输出路径")
    parser.add_argument(
        "--repair-eval",
        action="store_true",
        help="授权 Agent 尝试通过安全白名单的修复命令，并独立统计诊断和修复结果",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="仅验证场景故障注入和恢复，不运行诊断 Agent",
    )
    parser.add_argument(
        "--reuse-running",
        action="store_true",
        help="复用当前已运行的指定拓扑，跳过首次构建和启动",
    )
    parser.add_argument(
        "--max-turns",
        type=int,
        default=20,
        metavar="N",
        help="AI 最大问询轮数（默认：20）",
    )
    blind_group = parser.add_mutually_exclusive_group()
    blind_group.add_argument(
        "--blind",
        dest="blind",
        action="store_true",
        help="盲测模式（默认）：不向 AI 暴露场景元数据、注入信息或专属提示",
    )
    blind_group.add_argument(
        "--no-blind",
        dest="blind",
        action="store_false",
        help="指导模式：向 AI 提供场景专属诊断与修复上下文",
    )
    parser.set_defaults(blind=True)

    args = parser.parse_args()

    if not 1 <= args.max_turns <= 1000:
        parser.error("--max-turns 必须是 1 到 1000 之间的整数")

    # 无参数时直接运行随机大型 AI 场景（一次性完整流程）
    if len(sys.argv) == 1:
        args.agent = "ai"
        args.scenario = "randomized_transit_acl_shadowing_01"

    # 列出所有场景
    if args.list:
        print("所有场景:")
        for i, cls in enumerate(ALL_SCENARIOS, 1):
            eligibility = "main" if cls.main_score_eligible else "separate"
            print(
                f"  {i}. {cls.name}: {cls.description} "
                f"[{cls.topology}; track={cls.benchmark_track}; "
                f"difficulty={cls.difficulty}; {eligibility}]"
            )
        return

    # 检查 agent 参数
    if not args.agent:
        print("错误: 请指定 --agent (rule 或 ai)")
        parser.print_help()
        return
    if (
        args.agent == "ai"
        and not args.validate_only
        and not os.environ.get("AI_API_KEY")
    ):
        parser.error(
            "AI_API_KEY 未配置；请先在 VM 环境中设置轮换后的 API 密钥"
        )

    # 确定要测试的场景
    test_scenarios = []

    if args.scenario:
        # 测试指定场景
        names = [s.strip() for s in args.scenario.split(',')]
        for name in names:
            scenario = get_scenario(name)
            if scenario:
                test_scenarios.append(scenario)
            else:
                print(f"警告: 未知场景 '{name}'")
    elif args.track:
        test_scenarios = get_scenarios_by_track(args.track)
    elif args.all:
        # --all means the comparable main leaderboard, not mixed tracks.
        test_scenarios = MAIN_SCENARIOS
    elif args.topology:
        # 测试指定拓扑的场景
        test_scenarios = get_scenarios_by_topology(args.topology)
        if not test_scenarios:
            print(f"错误: 没有找到拓扑 '{args.topology}' 的场景")
            return
    else:
        print("错误: 请指定 --scenario, --all, --track 或 --topology")
        parser.print_help()
        return

    if not test_scenarios:
        print("没有要测试的场景")
        return

    # 选择诊断函数
    if args.agent == "ai":
        diagnosis_func = lambda: run_ai_diagnosis(max_turns=args.max_turns)
    else:
        diagnosis_func = run_rule_diagnosis
    if args.validate_only:
        diagnosis_func = None

    # 打印测试信息
    print("=" * 60)
    print(f"Benchmark 测试 - {args.agent.upper()} Agent")
    print("=" * 60)
    print(f"\n要测试的场景: {len(test_scenarios)}")
    print(f"测试模式: {'盲测' if args.blind else '指导测试'}")
    print(f"AI 最大问询轮数: {args.max_turns}")
    for cls in test_scenarios:
        print(f"  - {cls.name}: {cls.description} [{cls.topology}]")

    # 执行测试
    results = []
    current_topology = None
    report_path = (
        args.report
        if args.report
        else (
            "/home/zvanadium/seed-emulator/benchmarks/reports/"
            f"BENCHMARK_{args.agent.upper()}_REPORT.md"
        )
    )

    for scenario_cls in test_scenarios:
        scenario = scenario_cls()

        # 如果拓扑不同，需要切换
        if scenario.topology != current_topology:
            print(f"\n切换拓扑: {current_topology} -> {scenario.topology}")
            if args.reuse_running and current_topology is None:
                print("  复用当前运行中的拓扑")
            else:
                cleanup_environment()
                build_topology(scenario.topology)
                start_topology(scenario.topology)
            current_topology = scenario.topology
        else:
            if can_reuse_topology_between_scenarios(args, scenario.topology):
                # Every suite scenario performs an idempotent setup/fix cycle;
                # repair-eval and validate-only also perform deterministic
                # scenario cleanup, so a full topology restart is unnecessary.
                print(
                    "\n复用当前拓扑；场景负责恢复自身状态"
                )
            else:
                # 同拓扑：快速重启
                print(f"\n快速重启 (同拓扑: {scenario.topology})")
                topo_path = get_topology_path(scenario.topology)
                run(f"cd {topo_path} && docker-compose down 2>/dev/null", timeout=60)
                run(f"cd {topo_path} && docker-compose up -d 2>/dev/null", timeout=180)
                wait_for_bgp_convergence(max_wait=60)

        # 运行测试
        active_diagnosis_func = diagnosis_func
        if (
            args.agent == "ai"
            and scenario.topology == "RANDOM_COMPLEX_INTERNET"
            and not args.repair_eval
        ):
            from random_topology_ai_agent import RandomTopologyAIAgent
            def active_diagnosis_func():
                agent = RandomTopologyAIAgent(api_key=os.environ.get("AI_API_KEY"), max_turns=args.max_turns, verbose=True)
                diagnosis = agent.diagnose_interactive()
                stats = agent.api_stats
                return {"category": diagnosis.category, "confidence": diagnosis.confidence, "root_cause": diagnosis.root_cause, "api_stats": {"total_calls": stats.total_calls, "total_prompt_tokens": stats.total_prompt_tokens, "total_completion_tokens": stats.total_completion_tokens, "total_tokens": stats.total_tokens, "total_latency_ms": stats.total_latency_ms, "per_call_details": [vars(c) for c in stats.calls]}}
        try:
            if args.repair_eval:
                if not hasattr(scenario, "run_repair_evaluation"):
                    raise RuntimeError(
                        f"场景 {scenario.name} 不支持 --repair-eval"
                    )
                if args.agent == "ai":
                    result = scenario.run_repair_evaluation(
                        lambda active_scenario, **session_kwargs: run_ai_repair(
                            active_scenario,
                            blind=args.blind,
                            max_turns=args.max_turns,
                            **session_kwargs,
                        )
                    )
                else:
                    result = scenario.run_repair_evaluation(
                        lambda _: active_diagnosis_func()
                    )
            else:
                result = scenario.run_test(
                    ai_diagnosis_func=active_diagnosis_func
                )
        except Exception as exc:
            # Preserve earlier results and make infrastructure/setup failures
            # visible in the unified report instead of losing the whole batch.
            print(f"  场景执行失败: {exc}")
            result = {
                "scenario": scenario.name,
                "topology": scenario.topology,
                "benchmark_track": scenario.benchmark_track,
                "difficulty": scenario.difficulty,
                "main_score_eligible": scenario.main_score_eligible,
                "quarantine_reason": scenario.quarantine_reason,
                "scenario_seed": scenario.scenario_seed,
                "fault_type": scenario.fault_type,
                "ai_diagnosis": "scenario_error",
                "ai_confidence": 0.0,
                "correct_diagnosis": False,
                "repair_evaluation": bool(args.repair_eval),
                "repair_authorized": False,
                "repair_verified": False,
                "fix_verified": False,
                "duration": 0.0,
                "scenario_error": str(exc),
            }

        # 如果是AI Agent，附加API资源消耗到结果中
        result["blind_mode"] = args.blind
        result["max_turns"] = args.max_turns

        if args.agent == "ai" and 'api_stats' in result:
            api_stats = result['api_stats']
            if api_stats:
                result['api_calls'] = api_stats.get('total_calls', 0)
                result['api_prompt_tokens'] = api_stats.get('total_prompt_tokens', 0)
                result['api_completion_tokens'] = api_stats.get('total_completion_tokens', 0)
                result['api_total_tokens'] = api_stats.get('total_tokens', 0)
                result['api_latency_ms'] = api_stats.get('total_latency_ms', 0)
                result['api_per_call'] = api_stats.get('per_call_details', [])

        if args.repair_eval:
            result.setdefault("standard_cleanup_executed", False)
            result.setdefault("standard_cleanup_verified", False)
            result.setdefault("topology_tainted", True)
            print("  Recreating topology to isolate Agent side effects...")
            isolation_ok = recreate_topology_for_isolation(scenario.topology)
            result["isolation_recreated"] = isolation_ok
            result["isolation_fallback_rebuild"] = False
            if not isolation_ok:
                print("  Fast recreation failed; performing full rebuild...")
                cleanup_environment()
                build_topology(scenario.topology)
                start_topology(scenario.topology)
                isolation_ok = bool(
                    run("docker ps -q | head -n 1", timeout=15).strip()
                )
                result["isolation_recreated"] = isolation_ok
                result["isolation_fallback_rebuild"] = True
            result["topology_tainted"] = not isolation_ok

        results.append(result)
        generate_report(results, report_path, args.agent)
        if args.repair_eval and result.get("topology_tainted"):
            raise RuntimeError(
                f"Topology {scenario.topology} could not be safely recreated"
            )

    # 生成报告
    generate_report(results, report_path, args.agent)
    if args.validate_only and any(
        result.get("scenario_error") or not result.get("fix_verified")
        for result in results
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
