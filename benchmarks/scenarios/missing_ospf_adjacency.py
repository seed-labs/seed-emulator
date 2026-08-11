#!/usr/bin/env python3
"""
场景 5: OSPF 邻接缺失
"""

from scenarios.base import BaseScenario


class MissingOspfAdjacencyScenario(BaseScenario):
    name = "missing_ospf_adjacency_01"
    description = "OSPF 邻接缺失"
    topology = "B00_mini_internet"
    fault_type = "missing_ospf_adjacency"
    diagnosis_artifact = "/etc/bird/bird.conf"
    diagnosis_faulty_value = "area 42"
    diagnosis_expected_value = "area 0"
    container = "as2brd-r101-10.101.0.2"
    diagnosis_targets = (container,)
    difficulty = "core"

    def __init__(self):
        super().__init__()
        self.bad_area = self.choose_variant((42, 77, 99))
        self.diagnosis_faulty_value = f"area {self.bad_area}"

    def get_inject_cmd(self) -> str:
        return (
            f"docker exec {self.container} sed -i "
            f"'s/area 0/area {self.bad_area}/g' /etc/bird/bird.conf && "
            f"docker exec {self.container} birdc configure"
        )

    def get_verify_cmd(self) -> str:
        return (
            f"docker exec {self.container} sh -c \""
            "grep -q 'area 0' /etc/bird/bird.conf && "
            "birdc show ospf neighbors | grep -q 'Full/' && "
            "echo OSPF_ADJACENCY_OK\""
        )

    def get_fix_cmd(self) -> str:
        return (
            f"docker exec {self.container} sed -Ei "
            "'s/area (42|77|99)/area 0/g' /etc/bird/bird.conf && "
            f"docker exec {self.container} birdc configure"
        )

    def check_verified(self, output: str) -> bool:
        return "OSPF_ADJACENCY_OK" in output
