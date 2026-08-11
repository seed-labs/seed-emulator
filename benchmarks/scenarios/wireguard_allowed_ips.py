#!/usr/bin/env python3
"""WireGuard AllowedIPs mismatch scenario."""

import re

from scenarios.strict_network_software import StrictNetworkSoftwareScenario


class WireGuardAllowedIpsScenario(StrictNetworkSoftwareScenario):
    name = "wireguard_allowed_ips_error_01"
    description = "WireGuard peer AllowedIPs 错误导致隧道地址不可达"
    fault_type = "wireguard_config_error"
    left = "as153h-host_0-10.153.0.71"
    right = "as153h-host_1-10.153.0.72"
    diagnosis_targets = ("as153h-host_0-10.153.0.71",)
    diagnosis_artifact = "wg0 peer AllowedIPs"
    diagnosis_artifact_aliases = (
        "WireGuard peer allowed ips configuration",
        "WireGuard peer allowed ips",
    )
    diagnosis_faulty_value = "10.254.0.2/32"
    diagnosis_expected_value = "10.253.0.2/32"
    difficulty = "core"

    def get_setup_cmd(self) -> str:
        return (
            f"docker exec {self.left} sh -c 'ip link del wg0 2>/dev/null || true; "
            "wg genkey > /tmp/wg.key'; "
            f"docker exec {self.right} sh -c 'ip link del wg0 2>/dev/null || true; "
            "wg genkey > /tmp/wg.key'; "
            f"LKEY=$(docker exec {self.left} cat /tmp/wg.key); "
            f"RKEY=$(docker exec {self.right} cat /tmp/wg.key); "
            f"LPUB=$(docker exec {self.left} sh -c 'wg pubkey < /tmp/wg.key'); "
            f"RPUB=$(docker exec {self.right} sh -c 'wg pubkey < /tmp/wg.key'); "
            f"docker exec {self.left} sh -c \"ip link add wg0 type wireguard; "
            "ip addr add 10.253.0.1/24 dev wg0; "
            "wg set wg0 private-key /tmp/wg.key peer $RPUB "
            "allowed-ips 10.253.0.2/32 endpoint 10.153.0.72:51820; "
            "ip link set wg0 up\"; "
            f"docker exec {self.right} sh -c \"ip link add wg0 type wireguard; "
            "ip addr add 10.253.0.2/24 dev wg0; "
            "wg set wg0 listen-port 51820 private-key /tmp/wg.key peer $LPUB "
            "allowed-ips 10.253.0.1/32 endpoint 10.153.0.71:51820; "
            "ip link set wg0 up\""
        )

    def get_inject_cmd(self) -> str:
        return (
            f"RPUB=$(docker exec {self.right} sh -c 'wg pubkey < /tmp/wg.key'); "
            f"docker exec {self.left} wg set wg0 peer $RPUB "
            "allowed-ips 10.254.0.2/32"
        )

    def get_verify_cmd(self) -> str:
        return f"docker exec {self.left} ping -c 2 -W 1 10.253.0.2"

    def get_fix_cmd(self) -> str:
        return (
            f"RPUB=$(docker exec {self.right} sh -c 'wg pubkey < /tmp/wg.key'); "
            f"docker exec {self.left} wg set wg0 peer $RPUB "
            "allowed-ips 10.253.0.2/32"
        )

    def check_verified(self, output: str) -> bool:
        return re.search(r"(?<!\d)0% packet loss", output) is not None
