#!/usr/bin/env python3
"""Linux tc/NetEm total packet-loss scenario."""

import re

from scenarios.strict_network_software import StrictNetworkSoftwareScenario


class NetemPacketLossScenario(StrictNetworkSoftwareScenario):
    name = "netem_packet_loss_01"
    description = "tc/NetEm 在目标接口注入 100% 丢包"
    fault_type = "netem_packet_loss"
    source = "as154brd-router0-10.154.0.254"
    target = "as154h-host_0-10.154.0.71"
    diagnosis_artifact = "net0 root qdisc"
    diagnosis_faulty_value = "netem loss 100%"
    diagnosis_expected_value = "no root netem qdisc"
    diagnosis_expected_value_aliases = (
        "default root qdisc",
        "qdisc noqueue",
        "no netem qdisc",
    )
    difficulty = "core"

    def get_setup_cmd(self) -> str:
        return (
            f"docker exec {self.target} "
            "tc qdisc del dev net0 root 2>/dev/null || true"
        )

    def get_inject_cmd(self) -> str:
        return (
            f"docker exec {self.target} "
            "tc qdisc replace dev net0 root netem loss 100%"
        )

    def get_verify_cmd(self) -> str:
        return f"docker exec {self.source} ping -c 2 -W 1 10.154.0.71"

    def get_fix_cmd(self) -> str:
        return (
            f"docker exec {self.target} "
            "tc qdisc del dev net0 root 2>/dev/null || true"
        )

    def check_verified(self, output: str) -> bool:
        return re.search(r"(?<!\d)0% packet loss", output) is not None
