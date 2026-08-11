#!/usr/bin/env python3
"""
场景 9: IPv6 路由缺失

故障注入：删除全局 IPv6 路由
验证：检查是否存在全局 IPv6 路由
修复：添加全局 IPv6 路由
"""

from scenarios.base import BaseScenario


class Ipv6RouteMissingScenario(BaseScenario):
    name = "ipv6_route_missing_01"
    description = "IPv6 路由缺失"
    topology = "B00_mini_internet"
    fault_type = "ipv6_route_missing"
    diagnosis_artifact = "IPv6 route table"
    diagnosis_faulty_value = "missing 2001:db8:151::/64"
    diagnosis_expected_value = "2001:db8:151::/64 dev dummy0"
    difficulty = "core"

    def __init__(self):
        super().__init__()
        subnet_id = self.choose_variant((151, 2151, 3151))
        self.prefix = f"2001:db8:{subnet_id}::/64"
        self.address = f"2001:db8:{subnet_id}::1/64"
        self.probe = f"2001:db8:{subnet_id}::2"
        self.container = "as151brd-router0-10.151.0.254"
        self.diagnosis_targets = (self.container,)
        self.diagnosis_faulty_value = f"missing {self.prefix}"
        self.diagnosis_expected_value = f"{self.prefix} dev dummy0"

    def get_repair_context(self) -> str:
        return super().get_repair_context() + f"""
## IPv6 场景专属约束

- 缺失的目标前缀是 `{self.prefix}`，目标接口是 `dummy0`。
- 当前故障与 BGP/OSPF 无关；不要因普通 IPv4 协议状态改变类别。
- 最终必须返回使用 `docker exec` 和 `ip -6 route` 恢复该前缀的
  `repair_commands`，并用 `ip -6 route show` 检查。
"""

    def get_inject_cmd(self) -> str:
        return (
            f"docker exec {self.container} "
            f"ip -6 addr del {self.address} dev dummy0"
        )

    def get_verify_cmd(self) -> str:
        return (
            f"docker exec {self.container} sh -c \""
            f"ip -6 route show {self.prefix} | "
            f"grep -q '{self.prefix} dev dummy0' && "
            f"ip -6 route get {self.probe} | grep -q 'dev dummy0' && "
            "echo IPV6_ROUTE_OK\""
        )

    def get_fix_cmd(self) -> str:
        return (
            f"docker exec {self.container} sh -c '"
            f"ip -6 route del {self.prefix} dev dummy0 "
            "2>/dev/null || true; "
            f"ip -6 addr del {self.address} dev dummy0 "
            "2>/dev/null || true; "
            f"ip -6 addr add {self.address} dev dummy0'"
        )

    def check_verified(self, output: str) -> bool:
        return "IPV6_ROUTE_OK" in output
