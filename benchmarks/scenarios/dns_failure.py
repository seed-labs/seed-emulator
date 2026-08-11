#!/usr/bin/env python3
"""
场景 3: DNS 故障
"""

from scenarios.base import BaseScenario


class DnsFailureScenario(BaseScenario):
    name = "dns_failure_01"
    description = "DNS 故障"
    topology = "B00_mini_internet"
    fault_type = "dns_failure"
    diagnosis_artifact = "/etc/resolv.conf"
    diagnosis_faulty_value = "nameserver 192.0.2.1"
    diagnosis_expected_value = "nameserver 127.0.0.11"
    diagnosis_expected_value_aliases = ("Docker embedded DNS 127.0.0.11",)
    difficulty = "core"

    def __init__(self):
        super().__init__()
        self.bad_nameserver = self.choose_variant(
            ("192.0.2.1", "198.51.100.1", "203.0.113.1")
        )
        self.diagnosis_faulty_value = f"nameserver {self.bad_nameserver}"

    def get_repair_context(self) -> str:
        return super().get_repair_context() + """
## DNS 场景专属约束

- 目标容器使用 Docker 嵌入式 DNS `127.0.0.11`。
- 修复后必须既检查 `/etc/resolv.conf`，也实际解析同网络容器名。
"""

    def get_inject_cmd(self) -> str:
        return (
            "docker exec as150h-host_0-10.150.0.71 sh -c "
            f"'printf \"nameserver {self.bad_nameserver}\\n\" "
            "> /etc/resolv.conf'"
        )

    def get_verify_cmd(self) -> str:
        return (
            "docker exec as150h-host_0-10.150.0.71 sh -c '"
            "grep -Eq \"^nameserver[[:space:]]+127[.]0[.]0[.]11$\" "
            "/etc/resolv.conf && "
            "getent hosts as150brd-router0-10.150.0.254 "
            "| grep -q \"^10[.]150[.]0[.]254[[:space:]]\" && "
            "echo DNS_FUNCTIONAL_OK'"
        )

    def get_fix_cmd(self) -> str:
        return (
            "docker exec as150h-host_0-10.150.0.71 sh -c "
            "'printf \"nameserver 127.0.0.11\\noptions ndots:0\\n\" "
            "> /etc/resolv.conf'"
        )

    def check_verified(self, output: str) -> bool:
        return "DNS_FUNCTIONAL_OK" in output
