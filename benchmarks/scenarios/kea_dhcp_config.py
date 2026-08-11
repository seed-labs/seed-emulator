#!/usr/bin/env python3
"""Kea DHCP invalid subnet configuration scenario."""

import base64

from scenarios.strict_network_software import StrictNetworkSoftwareScenario


class KeaDhcpConfigScenario(StrictNetworkSoftwareScenario):
    name = "kea_dhcp_config_error_01"
    description = "Kea DHCPv4 子网和地址池配置不一致"
    fault_type = "kea_dhcp_config_error"
    container = "as160h-host_0-10.160.0.71"
    config = "/tmp/benchmark_kea.json"
    diagnosis_artifact = "/tmp/benchmark_kea.json"
    diagnosis_faulty_value = "pool 10.161.0.100-10.161.0.120"
    diagnosis_expected_value = "pool 10.160.0.100-10.160.0.120"
    benchmark_track = "config_lint"
    difficulty = "basic"
    main_score_eligible = False
    quarantine_reason = "配置 lint 子榜，不计入端到端网络修复主榜"

    def get_repair_context(self) -> str:
        return super().get_repair_context() + """
## Kea DHCP 场景专属修复约束

- `/tmp/benchmark_kea.json` 是单行 JSON；故障是 pool 地址段不属于
  `10.160.0.0/24` subnet。
- 修复现有 benchmark 文件即可，不要修改 `/etc/kea/kea-dhcp4.conf`，
  不要启动或重启 Kea 服务。
- 避免在 `sh -c 'echo ...'` 中直接嵌套 JSON 双引号和单引号，这很容易
  生成被 shell 截断的无效 JSON。
- 优先使用对现有文件进行精确字符串替换的 `sed -i` 命令；如需重写
  整个 JSON，应先将内容编码为 Base64，再在容器内解码。
- `repair_commands` 的最后一条命令必须运行
  `kea-dhcp4 -t /tmp/benchmark_kea.json`，只有配置检查成功才算完成。
"""

    def _write(self, subnet: str, pool: str) -> str:
        payload = (
            '{"Dhcp4":{"interfaces-config":{"interfaces":["net0"]},'
            f'"subnet4":[{{"subnet":"{subnet}",'
            f'"pools":[{{"pool":"{pool}"}}]}}]}}}}'
        )
        encoded = base64.b64encode(payload.encode("utf-8")).decode("ascii")
        return (
            f"docker exec {self.container} sh -c '"
            f"echo {encoded} | base64 -d > {self.config}'"
        )

    def get_setup_cmd(self) -> str:
        return self._write("10.160.0.0/24", "10.160.0.100-10.160.0.120")

    def get_inject_cmd(self) -> str:
        return self._write("10.160.0.0/24", "10.161.0.100-10.161.0.120")

    def get_verify_cmd(self) -> str:
        return (
            f"docker exec {self.container} sh -c '"
            f"kea-dhcp4 -t {self.config} >/dev/null 2>&1 && "
            "echo KEA_CONFIG_OK'"
        )

    def get_fix_cmd(self) -> str:
        return self._write("10.160.0.0/24", "10.160.0.100-10.160.0.120")

    def check_verified(self, output: str) -> bool:
        return "KEA_CONFIG_OK" in output
