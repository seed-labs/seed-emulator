#!/usr/bin/env python3
"""
场景 11: 双重故障 - DNS 错误 + 网络断开

同时注入两个独立故障：
1. DNS 配置错误（修改 resolv.conf）
2. 网络接口断开（断开 Docker 网络）

诊断挑战：需要区分是 DNS 问题还是网络问题
修复挑战：需要先修复网络，再修复 DNS
"""

from scenarios.base import BaseScenario


class DualFaultDnsNetworkScenario(BaseScenario):
    name = "dual_fault_dns_network_01"
    description = "双重故障: DNS 错误 + 网络断开"
    topology = "B00_mini_internet"
    fault_type = "multiple_faults"
    container = "as150h-host_0-10.150.0.71"
    network = "output_net_150_net0"
    diagnosis_targets = (container,)
    diagnosis_artifact = "/etc/resolv.conf and Docker network attachment"
    diagnosis_faulty_value = "bad nameserver and disconnected network"
    diagnosis_expected_value = "Docker DNS and connected network"
    benchmark_track = "advanced"
    difficulty = "advanced"
    main_score_eligible = False
    quarantine_reason = "多根因场景仅在 advanced 子榜计分"
    convergence_timeout = 60

    def __init__(self):
        super().__init__()
        self.bad_nameserver = self.choose_variant(
            ("192.0.2.1", "198.51.100.1", "203.0.113.1")
        )
        self.expected_root_causes = (
            {
                "category": "dns_failure",
                "target_container": [self.container],
                "artifact": "/etc/resolv.conf",
                "faulty_value": f"nameserver {self.bad_nameserver}",
                "expected_value": "nameserver 127.0.0.11",
            },
            {
                "category": "wrong_docker_network",
                "target_container": [self.container],
                "artifact": f"Docker network {self.network}",
                "faulty_value": "disconnected",
                "expected_value": "connected with 10.150.0.71",
            },
        )

    def get_repair_context(self) -> str:
        return super().get_repair_context() + """
## 双故障场景专属约束

- 必须分别恢复 Docker 网络附件和容器的 `127.0.0.11` DNS。
- 最终验证同时要求正确 IP 附件和同网络容器名解析成功。
"""

    def get_inject_cmd(self) -> str:
        return (
            f"docker exec {self.container} sh -c "
            f"'printf \"nameserver {self.bad_nameserver}\\n\" "
            "> /etc/resolv.conf' && "
            f"docker network disconnect {self.network} {self.container}"
        )

    def get_verify_cmd(self) -> str:
        return (
            f"docker inspect {self.container} --format "
            "'{{json .NetworkSettings.Networks}}'; "
            f"docker exec {self.container} sh -c '"
            "grep -Eq \"^nameserver[[:space:]]+127[.]0[.]0[.]11$\" "
            "/etc/resolv.conf && "
            "getent hosts as150brd-router0-10.150.0.254 "
            "| grep -q \"^10[.]150[.]0[.]254[[:space:]]\" && "
            "echo DNS_AFTER_NETWORK_OK'"
        )

    def get_fix_cmd(self) -> str:
        return (
            f"docker network disconnect {self.network} {self.container} "
            "2>/dev/null || true; "
            f"docker exec {self.container} ip link del net0 "
            "2>/dev/null || true; "
            f"docker network connect --ip 10.150.0.71 "
            f"{self.network} {self.container}; "
            f"docker exec {self.container} sh -c '"
            "for path in /sys/class/net/eth*; do "
            "iface=${path##*/}; "
            "if ip -o -4 addr show dev \"$iface\" | "
            "grep -q \"10.150.0.71/24\"; then "
            "ip link set \"$iface\" down; "
            "ip link set \"$iface\" name net0; "
            "ip link set net0 up; "
            "fi; done'; "
            f"docker exec {self.container} sh -c "
            "'printf \"nameserver 127.0.0.11\\noptions ndots:0\\n\" "
            "> /etc/resolv.conf'"
        )

    def check_verified(self, output: str) -> bool:
        return (
            '"IPAddress":"10.150.0.71"' in output
            and "DNS_AFTER_NETWORK_OK" in output
        )
