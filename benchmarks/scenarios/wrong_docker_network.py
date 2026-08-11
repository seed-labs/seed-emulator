#!/usr/bin/env python3
"""
场景 6: Docker 网络错误
"""

from scenarios.base import BaseScenario


class WrongDockerNetworkScenario(BaseScenario):
    name = "wrong_docker_network_01"
    description = "Docker 网络错误"
    topology = "B00_mini_internet"
    fault_type = "wrong_docker_network"
    router = "as151brd-router0-10.151.0.254"
    host = "as151h-host_0-10.151.0.71"
    network = "output_net_151_net0"
    diagnosis_artifact = "Docker network output_net_151_net0"
    diagnosis_faulty_value = "disconnected"
    diagnosis_expected_value = "connected with 10.151.0.254"
    diagnosis_targets = (router,)
    difficulty = "core"
    convergence_timeout = 90

    def get_inject_cmd(self) -> str:
        return f"docker network disconnect {self.network} {self.router}"

    def get_verify_cmd(self) -> str:
        return (
            f"docker inspect {self.router} --format "
            "'{{json .NetworkSettings.Networks}}'; "
            f"docker exec {self.router} ip -br addr show net0; "
            f"docker exec {self.host} ping -c 2 -W 1 10.151.0.254"
        )

    def get_fix_cmd(self) -> str:
        return (
            f"docker network disconnect {self.network} {self.router} "
            "2>/dev/null || true; "
            f"docker exec {self.router} ip link del net0 "
            "2>/dev/null || true; "
            f"docker network connect --ip 10.151.0.254 "
            f"{self.network} {self.router}; "
            f"docker exec {self.router} sh -c '"
            "for path in /sys/class/net/eth*; do "
            "iface=${path##*/}; "
            "if ip -o -4 addr show dev \"$iface\" | "
            "grep -q \"10.151.0.254/24\"; then "
            "ip link set \"$iface\" down; "
            "ip link set \"$iface\" name net0; "
            "ip link set net0 up; "
            "fi; done'"
        )

    def check_verified(self, output: str) -> bool:
        return (
            '"IPAddress":"10.151.0.254"' in output
            and "net0" in output
            and "10.151.0.254/24" in output
            and "0% packet loss" in output
            and "100% packet loss" not in output
        )
