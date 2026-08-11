#!/usr/bin/env python3
"""BIRD export filter deny policy scenario."""

from scenarios.strict_network_software import StrictNetworkSoftwareScenario


class BirdRoutePolicyScenario(StrictNetworkSoftwareScenario):
    name = "bird_route_policy_deny_01"
    description = "BIRD export filter 配置文件策略 lint"
    fault_type = "bird_route_policy_error"
    container = "as151brd-router0-10.151.0.254"
    config = "/tmp/benchmark_bird.conf"
    diagnosis_artifact = "/tmp/benchmark_bird.conf"
    diagnosis_faulty_value = "benchmark_export { reject; }"
    diagnosis_expected_value = "benchmark_export { accept; }"
    benchmark_track = "config_lint"
    difficulty = "basic"
    main_score_eligible = False
    quarantine_reason = "配置 lint 子榜，不计入端到端网络修复主榜"

    def _write(self, decision: str) -> str:
        return (
            f"docker exec {self.container} sh -c \""
            f"printf 'router id 10.151.0.254;\\n"
            f"filter benchmark_export {{ {decision}; }}\\n"
            "protocol device {}\\n"
            f"' > {self.config}\""
        )

    def get_setup_cmd(self) -> str:
        return self._write("accept")

    def get_inject_cmd(self) -> str:
        return self._write("reject")

    def get_verify_cmd(self) -> str:
        return (
            f"docker exec {self.container} sh -c \""
            f"bird -p -c {self.config} >/dev/null 2>&1 && "
            f"grep -q 'benchmark_export {{ accept;' {self.config} && "
            "echo BIRD_POLICY_OK\""
        )

    def get_fix_cmd(self) -> str:
        return self._write("accept")

    def check_verified(self, output: str) -> bool:
        return "BIRD_POLICY_OK" in output
