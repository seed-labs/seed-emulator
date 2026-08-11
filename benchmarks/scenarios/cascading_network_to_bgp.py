#!/usr/bin/env python3
"""
场景 13: 级联故障 - 网络断开导致 BGP 会话断开

网络接口问题导致 BGP 会话断开：
1. 断开 Docker 网络接口
2. BGP 会话因网络不可达而断开
3. 路由表清空

诊断挑战：需要识别是网络层问题而非 BGP 配置问题
修复挑战：需要先修复网络接口，BGP 会话自动重新建立

验证策略：使用 Docker 网络状态验证（而非 BIRD 协议状态）
- 注入后验证：容器不应连接到 ix101 网络
- 修复后验证：容器应重新连接到 ix101 网络
"""

from scenarios.base import BaseScenario


class CascadingNetworkToBgpScenario(BaseScenario):
    name = "cascading_network_to_bgp_01"
    description = "级联故障: 网络断开导致 BGP 会话断开"
    topology = "B00_mini_internet"
    fault_type = "wrong_docker_network"
    diagnosis_artifact = "Docker network output_net_ix_ix101"
    diagnosis_faulty_value = "disconnected"
    diagnosis_expected_value = "connected with 10.101.0.2"
    diagnosis_targets = ("as2brd-r101-10.101.0.2",)
    benchmark_track = "advanced"
    difficulty = "advanced"
    main_score_eligible = False
    quarantine_reason = "级联故障在 advanced 子榜单独计分"
    convergence_timeout = 120

    def get_repair_context(self) -> str:
        return super().get_repair_context() + """
## Docker 网络级联场景专属约束

- 根因是容器 `as2brd-r101-10.101.0.2` 被从 Docker 网络
  `output_net_ix_ix101` 断开，而不是 BIRD 配置错误。
- 诊断类别必须是 `wrong_docker_network`。
- 使用 `docker network connect` 恢复该网络连接；如容器内存在同名
  接口残留地址，可先用目标容器内的 `ip addr` 清理。
- 不要修改 BIRD 配置，最终必须返回真实 `repair_commands`。
"""

    def get_inject_cmd(self) -> str:
        # 断开网络接口 - 使用正确的容器名称
        return "docker network disconnect output_net_ix_ix101 as2brd-r101-10.101.0.2"

    def get_verify_cmd(self) -> str:
        return (
            "docker inspect as2brd-r101-10.101.0.2 --format "
            "'{{json .NetworkSettings.Networks}}'; "
            "docker exec as2brd-r101-10.101.0.2 sh -c \""
            "birdc show protocols | "
            "grep -Eq 'BGP[[:space:]].*Established' && "
            "echo BGP_AFTER_NETWORK_OK\""
        )

    def get_fix_cmd(self) -> str:
        return (
            "docker network disconnect output_net_ix_ix101 "
            "as2brd-r101-10.101.0.2 2>/dev/null || true; "
            "docker exec as2brd-r101-10.101.0.2 "
            "ip link del ix101 2>/dev/null || true; "
            "docker network connect --ip 10.101.0.2 "
            "output_net_ix_ix101 as2brd-r101-10.101.0.2; "
            "docker exec as2brd-r101-10.101.0.2 sh -c '"
            "for path in /sys/class/net/eth*; do "
            "iface=${path##*/}; "
            "if ip -o -4 addr show dev \"$iface\" | "
            "grep -q \"10.101.0.2/24\"; then "
            "ip link set \"$iface\" down; "
            "ip link set \"$iface\" name ix101; "
            "ip link set ix101 up; "
            "fi; done'"
        )

    def check_verified(self, output: str) -> bool:
        return (
            '"IPAddress":"10.101.0.2"' in output
            and "BGP_AFTER_NETWORK_OK" in output
        )
