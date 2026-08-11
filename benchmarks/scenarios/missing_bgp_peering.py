#!/usr/bin/env python3
"""
场景 4: BGP 对等缺失
"""

from scenarios.base import BaseScenario


class MissingBgpPeeringScenario(BaseScenario):
    name = "missing_bgp_peering_01"
    description = "BGP 对等缺失"
    topology = "B00_mini_internet"
    fault_type = "missing_bgp_peering"
    container = "as150brd-router0-10.150.0.254"
    diagnosis_artifact = "BIRD protocol u_as2 administrative state"
    diagnosis_faulty_value = "u_as2 disabled"
    diagnosis_expected_value = "u_as2 Established"
    diagnosis_targets = (container,)
    difficulty = "core"

    def get_inject_cmd(self) -> str:
        return f"docker exec {self.container} birdc disable u_as2"

    def get_verify_cmd(self) -> str:
        return (
            f"docker exec {self.container} sh -c \""
            "birdc show protocols | "
            "grep -Eq '^u_as2[[:space:]]+BGP.*Established' && "
            "echo BGP_PEERING_OK\""
        )

    def get_fix_cmd(self) -> str:
        return f"docker exec {self.container} birdc enable u_as2"

    def check_verified(self, output: str) -> bool:
        return "BGP_PEERING_OK" in output
