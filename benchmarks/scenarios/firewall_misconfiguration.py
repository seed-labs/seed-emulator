#!/usr/bin/env python3
"""
Mini Internet firewall misconfiguration benchmark scenario.

The fault is contained in a single Docker node. It installs iptables in the
target container, changes INPUT's default policy to DROP, and verifies
cross-AS reachability from an AS150 host. The fix restores ACCEPT and flushes
the injected rules.
"""

import time
import re

from scenarios.base import BaseScenario, run


class FirewallMisconfigurationScenario(BaseScenario):
    name = "firewall_misconfiguration_01"
    description = (
        "AS151 主机容器的错误 iptables INPUT 策略阻断节点网络连通"
    )
    topology = "B00_mini_internet_firewall"
    fault_type = "firewall_misconfiguration"
    diagnosis_artifact = "iptables INPUT chain"
    diagnosis_faulty_value = "policy DROP"
    diagnosis_expected_value = "policy ACCEPT"
    difficulty = "core"

    target_container = "as151h-host_0-10.151.0.71"
    source_container = "as151brd-router0-10.151.0.254"
    target_ip = "10.151.0.71"

    def get_inject_cmd(self) -> str:
        # iptables is baked into the target image by mini_internet.py.
        return (
            f"docker exec {self.target_container} sh -c '"
            "command -v iptables >/dev/null 2>&1 && "
            "iptables -F INPUT && iptables -P INPUT DROP"
            "'"
        )

    def get_verify_cmd(self) -> str:
        return (
            f"docker exec {self.source_container} "
            f"ping -c 3 -W 1 {self.target_ip}"
        )

    def get_fix_cmd(self) -> str:
        # Set the policy first so recovery cannot be interrupted by a later
        # command failure.
        return (
            f"docker exec {self.target_container} sh -c '"
            "iptables -P INPUT ACCEPT && iptables -F INPUT"
            "'"
        )

    def check_verified(self, output: str) -> bool:
        # A plain substring check is wrong because "100% packet loss" also
        # contains "0% packet loss".
        return re.search(r"(?<!\d)0% packet loss", output) is not None

    def inject_fault(self):
        """Validate the healthy baseline and the injected outage."""
        print("  检查故障注入前的网络基线...")
        baseline = ""
        for attempt in range(12):
            baseline = run(self.get_verify_cmd(), timeout=15)
            if self.check_verified(baseline):
                break
            print(f"  等待目标节点就绪... ({attempt + 1}/12)")
            time.sleep(5)
        if not self.check_verified(baseline):
            raise RuntimeError(
                "故障注入前目标已不可达，拒绝产生假阳性结果。"
            )

        print(f"  注入故障: {self.fault_type}")
        injected = run(
            f"{self.get_inject_cmd()} && echo FIREWALL_DROP_ACTIVE",
            timeout=180,
        )
        if "FIREWALL_DROP_ACTIVE" not in injected:
            raise RuntimeError(f"iptables 安装或故障注入失败:\n{injected}")

        time.sleep(2)
        fault_output = run(self.get_verify_cmd(), timeout=15)
        if self.check_verified(fault_output):
            # Do not leave a bad rule behind if injection had no effect.
            run(self.get_fix_cmd(), timeout=30)
            raise RuntimeError("错误防火墙策略未能阻断目标流量。")
        print("  故障验证成功: 目标网络已不可达")
