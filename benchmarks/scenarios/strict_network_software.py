#!/usr/bin/env python3
"""Shared strict fault lifecycle for network-software scenarios."""

import re
import time

from scenarios.base import BaseScenario, has_unsafe_host_shell_syntax, run


class StrictNetworkSoftwareScenario(BaseScenario):
    topology = "B00_network_software_suite"
    settle_seconds = 2
    repair_containers = ()
    _healthy_baseline_prepared = False

    def get_baseline_cmd(self) -> str:
        return self.get_verify_cmd()

    def check_fault_active(self, output: str) -> bool:
        return not self.check_verified(output)

    def prepare_healthy_baseline(self):
        print("  准备并验证健康基线...")
        setup = run(self.get_setup_cmd(), timeout=120)
        baseline = run(self.get_baseline_cmd(), timeout=30)
        if not self.check_verified(baseline):
            raise RuntimeError(
                f"健康基线验证失败，拒绝注入故障。\nsetup={setup}\n"
                f"baseline={baseline}"
            )
        self._healthy_baseline_prepared = True

    def inject_fault(self):
        if not self._healthy_baseline_prepared:
            self.prepare_healthy_baseline()
        print(f"  注入故障: {self.fault_type}")
        injected = run(
            f"{self.get_inject_cmd()} && echo FAULT_INJECTED",
            timeout=120,
        )
        if "FAULT_INJECTED" not in injected:
            raise RuntimeError(f"故障注入命令失败:\n{injected}")
        time.sleep(self.settle_seconds)

        fault_output = run(self.get_verify_cmd(), timeout=30)
        if not self.check_fault_active(fault_output):
            run(self.get_fix_cmd(), timeout=60)
            raise RuntimeError(
                f"故障未产生预期效果，已安全恢复:\n{fault_output}"
            )
        self._healthy_baseline_prepared = False
        print("  故障验证成功")

    def get_setup_cmd(self) -> str:
        raise NotImplementedError

    def get_repair_context(self) -> str:
        containers = ", ".join(self._allowed_repair_containers())
        artifact = getattr(self, "config", "")
        artifact_line = (
            f"- 故障注入的 benchmark 专用配置文件: {artifact}\n"
            "- 必须修复上述文件，不要改同类软件的 /etc 生产配置。\n"
            if artifact else ""
        )
        return (
            "## 端到端自主修复任务\n"
            f"- 场景: {self.name}\n"
            f"- 期望故障类别: {self.fault_type}\n"
            f"- 允许修改的容器: {containers}\n"
            f"{artifact_line}"
            "- 你必须先诊断，再在最终 JSON 的 repair_commands 数组中"
            "给出实际修复命令。\n"
            "- 不要调用或猜测 benchmark 的标准修复函数；根据观测到的"
            "错误配置自行构造命令。\n"
        )

    def _allowed_repair_containers(self):
        if self.repair_containers:
            return tuple(self.repair_containers)
        return tuple(
            dict.fromkeys(
                value
                for name in ("container", "left", "right", "target")
                for value in (getattr(self, name, None),)
                if value
            )
        )

    def is_repair_command_allowed(self, command: str) -> bool:
        """Confine Agent mutations to this scenario's disposable containers."""
        if not isinstance(command, str) or not command.strip():
            return False
        if has_unsafe_host_shell_syntax(command):
            return False
        if "\n" in command or "\r" in command:
            return False
        lowered = command.lower()
        forbidden = (
            "docker rm",
            "docker stop",
            "docker kill",
            "docker restart",
            "docker compose",
            "docker-compose",
            "--privileged",
            "/var/run/docker.sock",
            "sudo ",
        )
        if any(token in lowered for token in forbidden):
            return False
        referenced = re.findall(
            r"\bdocker\s+exec(?:\s+--?[A-Za-z0-9_=.-]+)*"
            r"\s+([A-Za-z0-9_.-]+)",
            command,
        )
        allowed = self._allowed_repair_containers()
        return bool(referenced) and all(container in allowed for container in referenced)

    def repair_command_rejection_reason(self, command: str) -> str:
        if not isinstance(command, str) or not command.strip():
            return "empty or non-string command"
        if has_unsafe_host_shell_syntax(command):
            return (
                "unsafe host-shell operator or invalid quoting; keep operators "
                "inside one quoted docker exec sh -c payload"
            )
        lowered = command.lower()
        forbidden = (
            "docker rm", "docker stop", "docker kill", "docker restart",
            "docker compose", "docker-compose", "--privileged",
            "/var/run/docker.sock", "sudo ",
        )
        matched = next((item for item in forbidden if item in lowered), None)
        if matched:
            return f"forbidden mutation primitive: {matched}"
        referenced = re.findall(
            r"\bdocker\s+exec(?:\s+--?[A-Za-z0-9_=.-]+)*"
            r"\s+([A-Za-z0-9_.-]+)",
            command,
        )
        if not referenced:
            return "repair must use docker exec with an explicit scoped target"
        return (
            "one or more referenced targets are outside the scenario mutation "
            f"scope: {', '.join(dict.fromkeys(referenced))}"
        )

    def _verify_agent_attempt(self) -> tuple[bool, str]:
        output = ""
        for _ in range(3):
            time.sleep(self.settle_seconds)
            output = self.verify_fix()
            if self.check_verified(output):
                return True, output
        return False, output
