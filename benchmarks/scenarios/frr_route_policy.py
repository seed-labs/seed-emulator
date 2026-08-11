#!/usr/bin/env python3
"""FRRouting route-map deny policy scenario."""

from scenarios.strict_network_software import StrictNetworkSoftwareScenario


class FrrRoutePolicyScenario(StrictNetworkSoftwareScenario):
    name = "frr_route_policy_deny_01"
    description = "FRRouting route-map 配置文件策略 lint"
    fault_type = "frr_route_policy_error"
    container = "as150h-host_0-10.150.0.71"
    config = "/tmp/benchmark_frr.conf"
    diagnosis_artifact = "/tmp/benchmark_frr.conf"
    diagnosis_faulty_value = "route-map BENCHMARK deny 10"
    diagnosis_expected_value = "route-map BENCHMARK permit 10"
    benchmark_track = "config_lint"
    difficulty = "basic"
    main_score_eligible = False
    quarantine_reason = "配置 lint 子榜，不计入端到端网络修复主榜"

    def _write(self, action: str) -> str:
        return (
            f"docker exec {self.container} sh -c \""
            f"printf 'route-map BENCHMARK {action} 10\\n"
            " match ip address prefix-list BENCHMARK_PREFIX\\n"
            "ip prefix-list BENCHMARK_PREFIX seq 10 permit 203.0.113.0/24\\n"
            f"' > {self.config}\""
        )

    def get_setup_cmd(self) -> str:
        return self._write("permit")

    def get_inject_cmd(self) -> str:
        return self._write("deny")

    def get_verify_cmd(self) -> str:
        return (
            f"docker exec {self.container} sh -c \""
            f"vtysh -C -f {self.config} >/dev/null 2>&1 && "
            f"grep -q 'route-map BENCHMARK permit 10' {self.config} && "
            "echo FRR_POLICY_OK\""
        )

    def get_fix_cmd(self) -> str:
        return self._write("permit")

    def check_verified(self, output: str) -> bool:
        return "FRR_POLICY_OK" in output
