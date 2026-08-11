#!/usr/bin/env python3
"""
场景 1: 错误 ASN 配置
"""

from scenarios.base import BaseScenario


class WrongAsnScenario(BaseScenario):
    name = "wrong_asn_01"
    description = "错误 ASN 配置"
    topology = "B00_mini_internet"
    fault_type = "wrong_asn"
    diagnosis_artifact = "/etc/bird/bird.conf"
    diagnosis_faulty_value = "AS 64512"
    diagnosis_expected_value = "AS 2"
    difficulty = "core"
    convergence_timeout = 120

    def __init__(self):
        super().__init__()
        self.container = self.choose_variant(
            (
                "as2brd-r100-10.100.0.2",
                "as2brd-r101-10.101.0.2",
                "as2brd-r102-10.102.0.2",
                "as2brd-r105-10.105.0.2",
            )
        )
        self.bad_asn = self.choose_variant((64512, 64513, 64514, 64515))
        self.diagnosis_targets = (self.container,)
        self.diagnosis_faulty_value = f"AS {self.bad_asn}"

    def get_inject_cmd(self) -> str:
        return (
            f"docker exec {self.container} sed -i "
            f"'s/as 2;/as {self.bad_asn};/g' /etc/bird/bird.conf && "
            f"docker exec {self.container} birdc configure"
        )

    def get_verify_cmd(self) -> str:
        return (
            f"docker exec {self.container} sh -c \""
            "birdc show protocols | grep -Eq "
            "'BGP[[:space:]].*Established' && "
            "grep -q 'as 2;' /etc/bird/bird.conf && "
            "echo BGP_ASN_OK\""
        )

    def get_fix_cmd(self) -> str:
        return (
            f"docker exec {self.container} sed -Ei "
            "'s/as (64512|64513|64514|64515|999);/as 2;/g' "
            "/etc/bird/bird.conf && "
            f"docker exec {self.container} birdc configure"
        )

    def check_verified(self, output: str) -> bool:
        return "BGP_ASN_OK" in output
