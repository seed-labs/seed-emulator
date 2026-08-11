#!/usr/bin/env python3
"""
场景 8: MPLS 标签问题
"""

from scenarios.base import BaseScenario


class MplsLabelProblemScenario(BaseScenario):
    name = "mpls_label_problem_01"
    description = "MPLS 标签问题"
    topology = "B31_mini_internet_mpls"
    fault_type = "mpls_label_problem"
    diagnosis_artifact = "FRR running-config"
    diagnosis_faulty_value = "no mpls ldp"
    diagnosis_expected_value = "mpls ldp"
    benchmark_track = "network_control_plane"
    difficulty = "advanced"

    def get_inject_cmd(self) -> str:
        return "docker exec as2r-core_100_101-10.2.0.253 vtysh -c 'configure terminal' -c 'no mpls ldp' -c 'end' -c 'write memory'"

    def get_verify_cmd(self) -> str:
        return (
            "docker exec as2r-core_100_101-10.2.0.253 sh -c \""
            "vtysh -c 'show running-config' | grep -q '^mpls ldp' && "
            "vtysh -c 'show mpls ldp neighbor' | "
            "grep -Eq 'Operational|Up' && echo MPLS_LDP_OK\""
        )

    def get_fix_cmd(self) -> str:
        return "docker exec as2r-core_100_101-10.2.0.253 vtysh -c 'configure terminal' -c 'mpls ldp' -c 'end' -c 'write memory'"

    def check_verified(self, output: str) -> bool:
        return "MPLS_LDP_OK" in output
