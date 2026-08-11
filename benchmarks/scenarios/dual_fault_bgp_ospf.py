#!/usr/bin/env python3
"""
场景 10: 双重故障 - BGP ASN 错误 + OSPF 区域错误

同时注入两个独立故障：
1. BGP ASN 配置错误（修改 AS 号）
2. OSPF 区域配置错误（修改 area ID）

诊断挑战：需要同时识别两个独立故障
修复挑战：需要按正确顺序修复
"""

from scenarios.base import BaseScenario


class DualFaultBgpOspfScenario(BaseScenario):
    name = "dual_fault_bgp_ospf_01"
    description = "双重故障: BGP ASN 错误 + OSPF 区域错误"
    topology = "B00_mini_internet"
    fault_type = "multiple_faults"
    container = "as2brd-r101-10.101.0.2"
    diagnosis_targets = (container,)
    diagnosis_artifact = "/etc/bird/bird.conf"
    diagnosis_faulty_value = "AS 64521 and OSPF area 99"
    diagnosis_expected_value = "AS 2 and OSPF area 0"
    benchmark_track = "advanced"
    difficulty = "advanced"
    main_score_eligible = False
    quarantine_reason = "多根因场景仅在 advanced 子榜计分"
    convergence_timeout = 120
    expected_root_causes = (
        {
            "category": "wrong_asn",
            "target_container": [container],
            "artifact": "/etc/bird/bird.conf",
            "faulty_value": "AS 64521",
            "expected_value": "AS 2",
        },
        {
            "category": "missing_ospf_adjacency",
            "target_container": [container],
            "artifact": "/etc/bird/bird.conf",
            "faulty_value": "area 99",
            "expected_value": "area 0",
        },
    )

    def get_inject_cmd(self) -> str:
        return (
            f"docker exec {self.container} sed -i "
            "'s/as 2;/as 64521;/g; s/area 0/area 99/g' "
            "/etc/bird/bird.conf && "
            f"docker exec {self.container} birdc configure"
        )

    def get_verify_cmd(self) -> str:
        return (
            f"docker exec {self.container} sh -c \""
            "grep -q 'as 2;' /etc/bird/bird.conf && "
            "grep -q 'area 0' /etc/bird/bird.conf && "
            "birdc show protocols | "
            "grep -Eq 'BGP[[:space:]].*Established' && "
            "birdc show ospf neighbors | grep -q 'Full/' && "
            "echo DUAL_BGP_OSPF_OK\""
        )

    def get_fix_cmd(self) -> str:
        return (
            f"docker exec {self.container} sed -Ei "
            "'s/as (64521|999);/as 2;/g; "
            "s/area (42|77|99)/area 0/g' /etc/bird/bird.conf && "
            f"docker exec {self.container} birdc configure"
        )

    def check_verified(self, output: str) -> bool:
        return "DUAL_BGP_OSPF_OK" in output
