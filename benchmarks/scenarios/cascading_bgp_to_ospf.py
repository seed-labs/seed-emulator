#!/usr/bin/env python3
"""BGP ASN corruption causing loss of an iBGP-learned route."""

from scenarios.base import BaseScenario


class CascadingBgpToOspfScenario(BaseScenario):
    name = "cascading_bgp_to_route_loss_01"
    description = "级联故障: BGP ASN 错误导致跨域路由消失"
    topology = "B00_mini_internet"
    fault_type = "wrong_asn"
    container = "as2brd-r101-10.101.0.2"
    diagnosis_artifact = "/etc/bird/bird.conf"
    diagnosis_faulty_value = "AS 64520"
    diagnosis_expected_value = "AS 2"
    diagnosis_targets = (container,)
    benchmark_track = "advanced"
    difficulty = "advanced"
    main_score_eligible = False
    quarantine_reason = "级联故障在 advanced 子榜单独计分"
    convergence_timeout = 120

    def get_inject_cmd(self) -> str:
        return (
            f"docker exec {self.container} sed -i "
            "'s/as 2;/as 64520;/g' /etc/bird/bird.conf && "
            f"docker exec {self.container} birdc configure"
        )

    def get_verify_cmd(self) -> str:
        return (
            f"docker exec {self.container} sh -c \""
            "grep -q 'as 2;' /etc/bird/bird.conf && "
            "birdc show protocols | "
            "grep -Eq '^ibgp1[[:space:]]+BGP.*Established' && "
            "birdc show route for 10.150.0.0/24 | "
            "grep -q '10.150.0.0/24' && "
            "echo BGP_ROUTE_CASCADE_OK\""
        )

    def get_fix_cmd(self) -> str:
        return (
            f"docker exec {self.container} sed -Ei "
            "'s/as (64520|999);/as 2;/g' /etc/bird/bird.conf && "
            f"docker exec {self.container} birdc configure"
        )

    def check_verified(self, output: str) -> bool:
        return "BGP_ROUTE_CASCADE_OK" in output
