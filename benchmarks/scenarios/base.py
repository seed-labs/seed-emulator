#!/usr/bin/env python3
"""
场景基类 - 所有场景继承此类。

支持轮询检测模式：修复后自动检测是否成功，而不是使用固定等待时间。
"""

from dataclasses import dataclass
import hashlib
import inspect
import os
from typing import Any, Dict, Iterable, List, Optional
import re
import shlex
import subprocess
import time


def has_unsafe_host_shell_syntax(command: str) -> bool:
    """Detect shell operators that would execute outside `docker exec`."""
    if not isinstance(command, str) or "\n" in command or "\r" in command:
        return True
    if "`" in command or "$(" in command:
        return True
    try:
        lexer = shlex.shlex(
            command, posix=True, punctuation_chars=";&|<>"
        )
        lexer.whitespace_split = True
        lexer.commenters = ""
        tokens = list(lexer)
    except ValueError:
        return True
    # Quoted payloads such as `sh -c 'echo x > /file'` remain one token;
    # unquoted host operators are emitted as punctuation-only tokens.
    return any(token and set(token) <= set(";&|<>") for token in tokens)


def run(cmd, timeout=180):
    """执行命令。"""
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout + r.stderr
    except subprocess.TimeoutExpired:
        return "命令执行超时"
    except Exception as e:
        return f"命令执行错误: {str(e)}"


def run_with_status(cmd, timeout=180):
    """Execute a scenario command while preserving its exit status."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return 124, "命令执行超时"
    except Exception as exc:
        return 125, f"命令执行错误: {exc}"


@dataclass
class ScenarioResult:
    """场景测试结果。"""
    scenario: str
    topology: str
    fault_type: str
    ai_diagnosis: str
    ai_confidence: float
    correct_diagnosis: bool
    fix_verified: bool
    duration: float


class BaseScenario:
    """场景基类。"""

    name: str = ""
    description: str = ""
    topology: str = ""
    fault_type: str = ""
    repair_containers = ()
    repair_command_prefixes = ()
    diagnosis_artifact = ""
    diagnosis_faulty_value = ""
    diagnosis_expected_value = ""
    diagnosis_targets = ()
    diagnosis_artifact_aliases = ()
    diagnosis_faulty_value_aliases = ()
    diagnosis_expected_value_aliases = ()
    expected_root_causes = ()
    benchmark_track = "network_functional"
    difficulty = "core"
    main_score_eligible = True
    quarantine_reason = ""
    fault_settle_seconds = 3
    convergence_timeout = 45
    generated_suite_id = ""
    generation_fingerprint = ""
    generation_contract_sha256 = ""
    _healthy_baseline_prepared = False

    def __init__(self):
        seed_text = os.environ.get("BENCHMARK_SEED", "0")
        digest = hashlib.sha256(
            f"{seed_text}:{self.name}".encode("utf-8")
        ).digest()
        self.scenario_seed = int.from_bytes(digest[:8], "big")

    def choose_variant(self, values: Iterable[Any]) -> Any:
        """Choose a stable per-scenario variant from BENCHMARK_SEED."""
        options = tuple(values)
        if not options:
            raise ValueError("scenario variant list must not be empty")
        return options[self.scenario_seed % len(options)]

    def _generation_metadata(self) -> Dict[str, str]:
        """Return provenance only for declaratively generated scenarios."""
        if not self.generated_suite_id:
            return {}
        return {
            "generated_suite_id": self.generated_suite_id,
            "generation_fingerprint": self.generation_fingerprint,
            "generation_contract_sha256": self.generation_contract_sha256,
        }

    def get_inject_cmd(self) -> str:
        """获取故障注入命令。"""
        raise NotImplementedError

    def get_verify_cmd(self) -> str:
        """获取验证命令。"""
        raise NotImplementedError

    def get_fix_cmd(self) -> str:
        """获取修复命令。"""
        raise NotImplementedError

    def check_verified(self, output: str) -> bool:
        """检查验证结果。"""
        raise NotImplementedError

    def _ensure_repair_containers_running(self):
        """Restore scenario targets to a runnable pre-injection state."""
        containers = self._infer_repair_containers()
        if not containers:
            return
        for container in containers:
            quoted = shlex.quote(container)
            returncode, output = run_with_status(
                "docker inspect --format '{{.State.Running}}' "
                f"{quoted}",
                timeout=15,
            )
            if returncode != 0:
                raise RuntimeError(
                    f"健康基线目标容器不存在: {container}\n"
                    f"{output[:1000]}"
                )
            if output.strip().lower() == "true":
                continue
            start_code, start_output = run_with_status(
                f"docker start {quoted}",
                timeout=60,
            )
            if start_code != 0:
                raise RuntimeError(
                    f"健康基线目标容器无法启动: {container}\n"
                    f"{start_output[:1000]}"
                )

        deadline = time.monotonic() + 30
        pending = list(containers)
        while pending and time.monotonic() < deadline:
            still_pending = []
            for container in pending:
                returncode, output = run_with_status(
                    "docker inspect --format '{{.State.Running}}' "
                    f"{shlex.quote(container)}",
                    timeout=15,
                )
                if returncode != 0 or output.strip().lower() != "true":
                    still_pending.append(container)
            pending = still_pending
            if pending:
                time.sleep(1)
        if pending:
            raise RuntimeError(
                "健康基线目标容器启动后仍未保持运行: "
                + ", ".join(pending)
            )

    def prepare_healthy_baseline(self):
        """Restore and prove a healthy pre-injection state."""
        print("  准备并验证健康基线...")
        self._ensure_repair_containers_running()
        run_with_status(self.get_fix_cmd(), timeout=120)
        output = ""
        deadline = time.monotonic() + self.convergence_timeout
        while time.monotonic() < deadline:
            output = run(self.get_verify_cmd(), timeout=30)
            if self.check_verified(output):
                self._healthy_baseline_prepared = True
                return
            time.sleep(3)
        raise RuntimeError(
            "健康基线验证失败，拒绝注入故障。\n"
            f"verification={output[:2000]}"
        )

    @staticmethod
    def _capture_observation_state() -> Dict[str, object]:
        from observations import capture_network_state

        return capture_network_state()

    def inject_fault(self):
        """Inject a fault only after proving the healthy baseline."""
        if not self._healthy_baseline_prepared:
            self.prepare_healthy_baseline()
        print(f"  注入故障: {self.fault_type}")
        returncode, output = run_with_status(self.get_inject_cmd(), timeout=120)
        if returncode != 0:
            run(self.get_fix_cmd(), timeout=120)
            self._healthy_baseline_prepared = False
            raise RuntimeError(
                f"故障注入命令失败 (exit={returncode})，已恢复。\n"
                f"{output[:2000]}"
            )
        time.sleep(self.fault_settle_seconds)
        fault_output = run(self.get_verify_cmd(), timeout=30)
        if not self.check_fault_active(fault_output):
            run(self.get_fix_cmd(), timeout=120)
            self._healthy_baseline_prepared = False
            raise RuntimeError(
                "故障未产生声明的功能影响，已恢复。\n"
                f"{fault_output[:2000]}"
            )
        self._healthy_baseline_prepared = False
        print("  故障验证成功")

    def check_fault_active(self, output: str) -> bool:
        """By default, a fault is active when the healthy verifier fails."""
        return not self.check_verified(output)

    def verify_fault(self) -> str:
        """验证故障。"""
        print(f"  验证故障...")
        cmd = self.get_verify_cmd()
        return run(cmd)

    def fix_fault(self):
        """修复故障 - 使用轮询检测模式。"""
        print(f"  修复故障...")
        cmd = self.get_fix_cmd()
        run(cmd)

        # 轮询检测修复是否成功
        max_attempts = 10
        wait_interval = 5

        for attempt in range(max_attempts):
            time.sleep(wait_interval)
            output = self.verify_fix()
            if self.check_verified(output):
                print(f"  修复成功 (尝试 {attempt + 1}/{max_attempts})")
                return
            print(f"  等待修复生效... (尝试 {attempt + 1}/{max_attempts})")

        print(f"  修复超时，可能需要更多时间")

    def verify_fix(self) -> str:
        """验证修复。"""
        print(f"  验证修复...")
        cmd = self.get_verify_cmd()
        return run(cmd)

    def _infer_repair_containers(self):
        if self.repair_containers:
            return tuple(self.repair_containers)
        injection = self.get_inject_cmd()
        containers = re.findall(
            r"\bdocker\s+exec(?:\s+--?[A-Za-z0-9_=.-]+)*"
            r"\s+([A-Za-z0-9_.-]+)",
            injection,
        )
        containers += re.findall(
            r"\bdocker\s+(?:stop|start|restart)\s+([A-Za-z0-9_.-]+)",
            injection,
        )
        containers += re.findall(
            r"\bdocker\s+network\s+(?:disconnect|connect)"
            r"(?:\s+--ip(?:=|\s+)\S+)?\s+\S+\s+"
            r"([A-Za-z0-9_.-]+)",
            injection,
        )
        # Common explicit attributes used by stricter scenarios.
        for name in (
            "container", "target_container", "left", "right", "target"
        ):
            value = getattr(self, name, None)
            if value:
                containers.append(value)
        return tuple(dict.fromkeys(containers))

    def get_repair_context(self) -> str:
        containers = ", ".join(self._infer_repair_containers()) or "由诊断确定"
        injection = " ".join(self.get_inject_cmd().split())
        return (
            "## 端到端自主修复任务\n"
            f"- 场景: {self.name}\n"
            f"- 描述: {self.description}\n"
            f"- 期望故障类别: {self.fault_type}\n"
            f"- 允许修改的容器: {containers}\n"
            f"- 故障注入作用面（用于定位，不是修复答案）: {injection[:1000]}\n"
            "- 必须根据当前实际状态自行诊断，并在最终 JSON 的 "
            "repair_commands 中给出真实修复命令。\n"
            "- 不得调用 benchmark 场景的 get_fix_cmd、fix_fault 或 repair "
            "辅助入口。\n"
        )

    def is_repair_command_allowed(self, command: str) -> bool:
        """Allow only scoped Docker mutations required by the scenario."""
        if not isinstance(command, str) or not command.strip():
            return False
        if has_unsafe_host_shell_syntax(command):
            return False
        lowered = command.lower()
        forbidden = (
            "docker rm", "docker kill", "docker compose", "docker-compose",
            "--privileged", "/var/run/docker.sock", "sudo ",
        )
        if any(token in lowered for token in forbidden):
            return False

        allowed_containers = self._infer_repair_containers()
        exec_targets = re.findall(
            r"\bdocker\s+exec(?:\s+--?[A-Za-z0-9_=.-]+)*"
            r"\s+([A-Za-z0-9_.-]+)",
            command,
        )
        lifecycle_targets = re.findall(
            r"\bdocker\s+(?:start|restart)\s+([A-Za-z0-9_.-]+)",
            command,
        )
        network_targets = re.findall(
            r"\bdocker\s+network\s+connect"
            r"(?:\s+--ip(?:=|\s+)\S+)?\s+\S+\s+"
            r"([A-Za-z0-9_.-]+)",
            command,
        )
        targets = exec_targets + lifecycle_targets + network_targets
        if targets and all(target in allowed_containers for target in targets):
            return True
        return any(
            command.strip().startswith(prefix)
            for prefix in self.repair_command_prefixes
        )

    def repair_command_rejection_reason(self, command: str) -> str:
        """Explain a safety-gate rejection without disclosing the answer."""
        if not isinstance(command, str) or not command.strip():
            return "empty or non-string command"
        if has_unsafe_host_shell_syntax(command):
            return (
                "unsafe host-shell operator or invalid quoting; put every "
                "redirection/pipeline/operator inside one quoted docker exec "
                "sh -c payload"
            )
        lowered = command.lower()
        forbidden = (
            "docker rm", "docker kill", "docker compose", "docker-compose",
            "--privileged", "/var/run/docker.sock", "sudo ",
        )
        matched = next((item for item in forbidden if item in lowered), None)
        if matched:
            return f"forbidden mutation primitive: {matched}"
        targets = re.findall(
            r"\bdocker\s+exec(?:\s+--?[A-Za-z0-9_=.-]+)*"
            r"\s+([A-Za-z0-9_.-]+)",
            command,
        )
        targets += re.findall(
            r"\bdocker\s+(?:start|restart)\s+([A-Za-z0-9_.-]+)",
            command,
        )
        targets += re.findall(
            r"\bdocker\s+network\s+connect"
            r"(?:\s+--ip(?:=|\s+)\S+)?\s+\S+\s+"
            r"([A-Za-z0-9_.-]+)",
            command,
        )
        if not targets:
            return "command does not identify a scoped Docker target"
        return (
            "one or more referenced targets are outside the scenario mutation "
            f"scope: {', '.join(dict.fromkeys(targets))}"
        )

    @staticmethod
    def _repair_field(repair: Any, name: str, default: Any = None) -> Any:
        if isinstance(repair, dict):
            return repair.get(name, default)
        return getattr(repair, name, default)

    @staticmethod
    def _normalized_fact(value: Any) -> str:
        text = str(value or "").lower()
        text = re.sub(r"\b(?:refcnt|handle)\s+\S+", " ", text)
        text = re.sub(r"\b[0-9a-f]+:\b", " ", text)
        return " ".join(text.split())

    @classmethod
    def _fact_tokens(cls, value: Any) -> set:
        return set(
            re.findall(
                r"[a-z0-9_./:+%-]+",
                cls._normalized_fact(value),
            )
        )

    @classmethod
    def _fact_matches(
        cls,
        predicted: Any,
        expected: Any,
        aliases: Iterable[Any] = (),
    ) -> bool:
        candidates = [expected, *aliases]
        left = cls._normalized_fact(predicted)
        if not left:
            return not any(cls._normalized_fact(item) for item in candidates)
        left_tokens = cls._fact_tokens(left)
        for candidate in candidates:
            right = cls._normalized_fact(candidate)
            if not right:
                continue
            if left == right or left in right or right in left:
                return True
            right_tokens = cls._fact_tokens(right)
            if right_tokens and right_tokens.issubset(left_tokens):
                return True
        return False

    def _expected_root_cause_specs(self) -> List[Dict[str, Any]]:
        if self.expected_root_causes:
            return [dict(item) for item in self.expected_root_causes]
        return [
            {
                "category": self.fault_type,
                "target_container": list(
                    self.diagnosis_targets or self._infer_repair_containers()
                ),
                "artifact": self.diagnosis_artifact,
                "artifact_aliases": self.diagnosis_artifact_aliases,
                "faulty_value": self.diagnosis_faulty_value,
                "faulty_value_aliases": self.diagnosis_faulty_value_aliases,
                "expected_value": self.diagnosis_expected_value,
                "expected_value_aliases": self.diagnosis_expected_value_aliases,
            }
        ]

    @staticmethod
    def _predicted_root_causes(repair: Dict[str, Any]) -> List[Dict[str, Any]]:
        roots = repair.get("root_causes") or []
        if roots:
            return [dict(item) for item in roots if isinstance(item, dict)]
        return [
            {
                "category": repair.get("category", ""),
                "target_container": repair.get("target_container", []),
                "artifact": repair.get("artifact", ""),
                "faulty_value": repair.get("faulty_value", ""),
                "expected_value": repair.get("expected_value", ""),
            }
        ]

    def _score_root_cause(
        self,
        predicted: Dict[str, Any],
        expected: Dict[str, Any],
    ) -> Dict[str, bool]:
        predicted_targets = {
            self._normalized_fact(item)
            for item in predicted.get("target_container", [])
            if item
        }
        expected_targets = {
            self._normalized_fact(item)
            for item in expected.get("target_container", [])
            if item
        }
        return {
            "category": predicted.get("category") == expected.get("category"),
            "target_container": (
                expected_targets.issubset(predicted_targets)
                if expected_targets
                else bool(predicted_targets)
            ),
            "artifact": self._fact_matches(
                predicted.get("artifact"),
                expected.get("artifact"),
                expected.get("artifact_aliases", ()),
            ),
            "faulty_value": self._fact_matches(
                predicted.get("faulty_value"),
                expected.get("faulty_value"),
                expected.get("faulty_value_aliases", ()),
            ),
            "expected_value": self._fact_matches(
                predicted.get("expected_value"),
                expected.get("expected_value"),
                expected.get("expected_value_aliases", ()),
            ),
        }

    def score_diagnosis(self, repair: Dict[str, Any]) -> Dict[str, Any]:
        """Semantically score one or more structured root causes."""
        predicted = self._predicted_root_causes(repair)
        expected = self._expected_root_cause_specs()
        unmatched = set(range(len(predicted)))
        root_scores = []
        for expected_root in expected:
            best_index = None
            best_components = None
            best_score = -1
            for index in unmatched:
                components = self._score_root_cause(
                    predicted[index],
                    expected_root,
                )
                score = sum(components.values())
                if score > best_score:
                    best_index = index
                    best_components = components
                    best_score = score
            if best_index is None:
                best_components = {
                    "category": False,
                    "target_container": False,
                    "artifact": False,
                    "faulty_value": False,
                    "expected_value": False,
                }
            else:
                unmatched.remove(best_index)
            root_scores.append(best_components)
        components = {
            key: all(score[key] for score in root_scores)
            for key in (
                "category",
                "target_container",
                "artifact",
                "faulty_value",
                "expected_value",
            )
        }
        component_total = sum(
            sum(score.values()) for score in root_scores
        )
        component_count = max(1, len(root_scores) * 5)
        root_count_correct = len(predicted) == len(expected)
        return {
            "components": components,
            "root_scores": root_scores,
            "root_count_correct": root_count_correct,
            "score": component_total / component_count,
            "correct": root_count_correct and all(components.values()),
            "expected": expected,
        }

    def _verify_agent_attempt(self) -> tuple[bool, str]:
        output = ""
        for _ in range(6):
            time.sleep(3)
            output = self.verify_fix()
            if self.check_verified(output):
                return True, output
        return False, output

    @staticmethod
    def _repair_func_accepts_session(repair_func) -> bool:
        signature = inspect.signature(repair_func)
        return any(
            parameter.kind == inspect.Parameter.VAR_KEYWORD
            for parameter in signature.parameters.values()
        ) or all(
            name in signature.parameters
            for name in (
                "baseline_state",
                "current_state",
                "repair_attempt_handler",
            )
        )

    def run_repair_evaluation(self, repair_func) -> dict:
        """Execute only Agent-authored repairs; use get_fix_cmd for cleanup."""
        start = time.time()
        repaired = False
        result = None
        repair = {"category": "unknown", "confidence": 0.0}
        executed = []
        rejected = []
        rejection_details = []
        proposed = []
        attempts = []
        try:
            self.prepare_healthy_baseline()
            baseline_state = self._capture_observation_state()
            self.inject_fault()
            current_state = self._capture_observation_state()

            def attempt_handler(diagnosis) -> Dict[str, Any]:
                nonlocal repaired
                commands = list(
                    self._repair_field(diagnosis, "repair_commands", []) or []
                )
                proposed.extend(commands)
                attempt_executed = []
                attempt_rejections = []
                for command in commands:
                    if not self.is_repair_command_allowed(command):
                        reason = self.repair_command_rejection_reason(command)
                        rejected.append(command)
                        detail = {"command": command, "reason": reason}
                        rejection_details.append(detail)
                        attempt_rejections.append(detail)
                        continue
                    output = run(command, timeout=90)
                    item = {"command": command, "output": output[:1000]}
                    executed.append(item)
                    attempt_executed.append(item)
                verification_output = ""
                if attempt_executed:
                    repaired, verification_output = self._verify_agent_attempt()
                outcome = {
                    "attempt": len(attempts) + 1,
                    "verified": repaired,
                    "rejections": attempt_rejections,
                    "executions": attempt_executed,
                    "verification_output": verification_output[:1500],
                }
                attempts.append(outcome)
                return outcome

            if self._repair_func_accepts_session(repair_func):
                repair = repair_func(
                    self,
                    baseline_state=baseline_state,
                    current_state=current_state,
                    repair_attempt_handler=attempt_handler,
                )
            else:
                repair = repair_func(self)
                attempt_handler(repair)

            commands = repair.get("repair_commands", [])
            if not proposed and commands:
                proposed.extend(commands)
            diagnosis_score = self.score_diagnosis(repair)

            result = {
                "scenario": self.name,
                "topology": self.topology,
                "benchmark_track": self.benchmark_track,
                "difficulty": self.difficulty,
                "main_score_eligible": self.main_score_eligible,
                "quarantine_reason": self.quarantine_reason,
                "scenario_seed": self.scenario_seed,
                "fault_type": self.fault_type,
                "ai_diagnosis": repair.get("category", "unknown"),
                "ai_confidence": repair.get("confidence", 0.0),
                "category_correct": diagnosis_score["components"]["category"],
                "correct_diagnosis": diagnosis_score["correct"],
                "diagnosis_score": diagnosis_score["score"],
                "diagnosis_score_components": diagnosis_score["components"],
                "diagnosis_root_scores": diagnosis_score["root_scores"],
                "diagnosis_root_count_correct": diagnosis_score[
                    "root_count_correct"
                ],
                "diagnosis_expected": diagnosis_score["expected"],
                "repair_evaluation": True,
                "repair_submitted": bool(proposed),
                "repair_authorized": bool(executed),
                "repair_commands_proposed": proposed,
                "repair_commands_executed": executed,
                "repair_commands_rejected": rejected,
                "repair_command_rejections": rejection_details,
                "repair_attempts": attempts,
                "repair_verified": repaired,
                "fix_verified": repaired,
                "duration": time.time() - start,
            }
            result.update(self._generation_metadata())
            if repair.get("api_stats"):
                result["api_stats"] = repair["api_stats"]
            for key in (
                "root_cause", "reasoning", "turns",
                "target_container", "artifact",
                "faulty_value", "expected_value",
                "root_causes",
                "error",
                "diagnostic_commands_executed",
                "diagnostic_commands_rejected",
            ):
                if key in repair:
                    result[key] = repair[key]
            return result
        finally:
            # Freeze the Agent score first, then always restore the known
            # scenario state. Cleanup is never counted as an Agent repair.
            cleanup_output = run(self.get_fix_cmd(), timeout=90)
            cleanup_verified = False
            for _ in range(10):
                time.sleep(3)
                if self.check_verified(self.verify_fix()):
                    cleanup_verified = True
                    break
            if result is not None:
                result["standard_cleanup_executed"] = True
                result["standard_cleanup_verified"] = cleanup_verified
                result["standard_cleanup_output"] = cleanup_output[:1000]
                result["topology_tainted"] = not cleanup_verified

    def run_test(self, ai_diagnosis_func=None) -> dict:
        """运行测试。"""
        print(f"\n{'='*60}")
        print(f"场景: {self.name}")
        print(f"描述: {self.description}")
        print(f"拓扑: {self.topology}")
        print(f"故障类型: {self.fault_type}")
        print(f"{'='*60}")

        start = time.time()

        # 注入故障
        self.inject_fault()

        # AI 诊断
        ai_diagnosis = {"category": "unknown", "confidence": 0.0}
        if ai_diagnosis_func:
            print(f"  AI 诊断...")
            ai_diagnosis = ai_diagnosis_func()
            print(f"    类别: {ai_diagnosis['category']}")
            print(f"    置信度: {ai_diagnosis['confidence']:.0%}")

        # 修复故障
        self.fix_fault()

        # 验证修复
        output = self.verify_fix()
        verified = self.check_verified(output)

        duration = time.time() - start

        # 诊断是否正确
        correct_diagnosis = ai_diagnosis['category'] == self.fault_type

        print(f"\n{'-'*60}")
        print(f"结果:")
        print(f"  AI 诊断: {ai_diagnosis['category']} ({ai_diagnosis['confidence']:.0%})")
        print(f"  期望诊断: {self.fault_type}")
        print(f"  诊断正确: {'✓' if correct_diagnosis else '✗'}")
        print(f"  修复验证: {'✓ 通过' if verified else '✗ 失败'}")
        print(f"  耗时: {duration:.1f}s")
        print(f"{'-'*60}")

        result = {
            "scenario": self.name,
            "topology": self.topology,
            "benchmark_track": self.benchmark_track,
            "difficulty": self.difficulty,
            "main_score_eligible": self.main_score_eligible,
            "quarantine_reason": self.quarantine_reason,
            "scenario_seed": self.scenario_seed,
            "fault_type": self.fault_type,
            "ai_diagnosis": ai_diagnosis['category'],
            "ai_confidence": ai_diagnosis['confidence'],
            "correct_diagnosis": correct_diagnosis,
            "fix_verified": verified,
            "healthy_baseline_verified": True,
            "fault_injection_verified": True,
            "standard_cleanup_verified": verified,
            "topology_tainted": not verified,
            "duration": duration,
        }
        result.update(self._generation_metadata())

        # Pass through AI API stats if available
        if 'api_stats' in ai_diagnosis:
            result['api_stats'] = ai_diagnosis['api_stats']

        return result
