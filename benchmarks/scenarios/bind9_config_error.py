#!/usr/bin/env python3
"""BIND9 invalid recursion option scenario."""

from scenarios.strict_network_software import StrictNetworkSoftwareScenario


class Bind9ConfigErrorScenario(StrictNetworkSoftwareScenario):
    name = "bind9_config_error_01"
    description = "BIND9 options 中出现非法 recursion 值，配置校验失败"
    fault_type = "bind9_config_error"
    container = "as152h-host_0-10.152.0.71"
    config = "/tmp/benchmark_named.conf"
    diagnosis_artifact = "/tmp/benchmark_named.conf"
    diagnosis_faulty_value = "recursion maybe"
    diagnosis_expected_value = "recursion yes"
    diagnosis_artifact_aliases = (
        "BIND9 configuration",
        "named.conf",
    )
    benchmark_track = "config_lint"
    difficulty = "basic"
    main_score_eligible = False
    quarantine_reason = "配置 lint 子榜，不计入端到端网络修复主榜"

    def _write(self, recursion: str) -> str:
        return (
            f"docker exec {self.container} sh -c \""
            "printf 'options { directory \\\"/tmp\\\"; "
            f"recursion {recursion}; listen-on {{ 127.0.0.1; }}; }};\\n"
            f"' > {self.config}\""
        )

    def get_setup_cmd(self) -> str:
        return self._write("yes")

    def get_inject_cmd(self) -> str:
        return self._write("maybe")

    def get_verify_cmd(self) -> str:
        return (
            f"docker exec {self.container} sh -c '"
            f"named-checkconf {self.config} >/dev/null 2>&1 && "
            "echo BIND_CONFIG_OK'"
        )

    def get_fix_cmd(self) -> str:
        return self._write("yes")

    def check_verified(self, output: str) -> bool:
        return "BIND_CONFIG_OK" in output
