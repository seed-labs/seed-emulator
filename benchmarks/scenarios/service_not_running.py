#!/usr/bin/env python3
"""
场景 2: 服务未运行
"""

from scenarios.base import BaseScenario


class ServiceNotRunningScenario(BaseScenario):
    name = "service_not_running_01"
    description = "目标容器意外停止"
    topology = "B00_mini_internet"
    fault_type = "container_not_running"
    diagnosis_artifact = "Docker container state"
    diagnosis_faulty_value = "stopped"
    diagnosis_expected_value = "running"
    difficulty = "basic"

    def get_inject_cmd(self) -> str:
        return "docker stop as150h-host_0-10.150.0.71"

    def get_verify_cmd(self) -> str:
        return "docker ps --filter name=as150h-host_0 --format '{{.Status}}'"

    def get_fix_cmd(self) -> str:
        return "docker start as150h-host_0-10.150.0.71"

    def check_verified(self, output: str) -> bool:
        return "Up" in output
