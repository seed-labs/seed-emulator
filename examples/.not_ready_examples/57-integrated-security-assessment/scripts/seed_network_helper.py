"""Seed-Emulator 网络辅助脚本。

该模块提供一组实用函数，用于在本地 Docker 环境中将外部安全工具容器
接入 SEED 仿真网络。主要能力包括：

1. 检查并创建指定的 Seed-Emulator Docker 网络。
2. 将容器连接 / 断开到该网络，可选传入别名。
3. 简易 CLI，方便在脚本或命令行中调用。

设计原则：

- 避免引入额外依赖（使用标准库与 Docker CLI 完成操作）。
- 对常见错误给出明确提示，便于教学场景下排障。
- 提供可测试的内部函数，配合单元测试验证命令拼装逻辑。
"""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import subprocess
from dataclasses import dataclass
from typing import Iterable, Optional, Sequence


logger = logging.getLogger(__name__)


class SeedNetworkError(RuntimeError):
    """操作 Seed-Emulator Docker 网络时抛出的异常。"""


@dataclass
class DockerCommandResult:
    """封装 docker 命令的执行结果，便于在测试中断言。"""

    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


def _require_docker() -> str:
    path = shutil.which("docker")
    if not path:
        raise SeedNetworkError("未检测到 docker，可通过 `sudo apt install docker.io` 安装")
    return path


def _run_docker(args: Sequence[str], *, check: bool = False) -> DockerCommandResult:
    docker = _require_docker()
    cmd = [docker, *args]
    logger.debug("执行 docker 命令: %s", " ".join(cmd))
    completed = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    result = DockerCommandResult(
        returncode=completed.returncode,
        stdout=completed.stdout.strip(),
        stderr=completed.stderr.strip(),
    )
    if check and not result.ok:
        raise SeedNetworkError(result.stderr or result.stdout or "docker 命令执行失败")
    return result


def _ensure_network(network_name: str, *, create_if_missing: bool = False) -> None:
    inspect = _run_docker(["network", "inspect", network_name])
    if inspect.ok:
        return

    if not create_if_missing:
        raise SeedNetworkError(
            f"未找到 Docker 网络 `{network_name}`，请先创建或在命令中使用 --create-network"
        )

    logger.info("未检测到网络 %s，正在尝试创建…", network_name)
    create_result = _run_docker(["network", "create", network_name], check=True)
    logger.info("docker network create 返回: %s", create_result.stdout)


def _inspect_container_networks(container_name: str) -> dict[str, dict[str, object]]:
    result = _run_docker(
        [
            "inspect",
            "-f",
            "{{json .NetworkSettings.Networks}}",
            container_name,
        ]
    )

    if not result.ok:
        raise SeedNetworkError(
            f"容器 `{container_name}` 不存在或不可访问：{result.stderr or result.stdout}"
        )

    try:
        return json.loads(result.stdout or "{}")
    except json.JSONDecodeError as exc:  # pragma: no cover - 理论上不会出现
        raise SeedNetworkError(f"解析容器网络信息失败: {exc}") from exc


def _connected(networks: dict[str, dict[str, object]], network_name: str) -> bool:
    return network_name in networks


def link_container_to_seed_network(
    container_name: str,
    network_name: str = "seed_emulator",
    *,
    create_network: bool = False,
    aliases: Optional[Iterable[str]] = None,
) -> bool:
    """将容器连接到 Seed-Emulator Docker 网络。

    返回值
    ----
    bool
        - ``True`` : 成功建立新的连接。
        - ``False`` : 容器已连接，未做额外操作。
    """

    _ensure_network(network_name, create_if_missing=create_network)
    networks = _inspect_container_networks(container_name)

    if _connected(networks, network_name):
        logger.info("容器 %s 已连接到网络 %s", container_name, network_name)
        return False

    args = ["network", "connect", network_name, container_name]
    for alias in aliases or []:
        args.extend(["--alias", alias])

    _run_docker(args, check=True)
    logger.info("已将容器 %s 接入网络 %s", container_name, network_name)
    return True


def unlink_container_from_seed_network(
    container_name: str,
    network_name: str = "seed_emulator",
) -> bool:
    """从 Seed-Emulator Docker 网络断开容器。

    返回 ``True`` 表示发生断开；如果原先未连接则返回 ``False``。
    """

    networks = _inspect_container_networks(container_name)
    if not _connected(networks, network_name):
        logger.info("容器 %s 未连接到网络 %s", container_name, network_name)
        return False

    _run_docker(["network", "disconnect", network_name, container_name], check=True)
    logger.info("已将容器 %s 从网络 %s 中断开", container_name, network_name)
    return True


def _format_aliases(aliases: Optional[Iterable[str]]) -> str:
    return ", ".join(sorted(set(aliases or []))) or "<无>"


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="管理 57 综合安全实验中的 Docker 网络连接",
    )
    parser.add_argument(
        "--network",
        default="seed_emulator",
        help="Seed-Emulator 对应的 Docker 网络名称 (默认: seed_emulator)",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    connect_parser = sub.add_parser("connect", help="将容器加入 Seed 网络")
    connect_parser.add_argument("container", help="目标容器名称")
    connect_parser.add_argument(
        "--alias",
        action="append",
        dest="aliases",
        help="为容器在该网络中设置别名，可多次使用",
    )
    connect_parser.add_argument(
        "--create-network",
        action="store_true",
        help="若网络不存在则自动创建",
    )

    disconnect_parser = sub.add_parser("disconnect", help="将容器从 Seed 网络断开")
    disconnect_parser.add_argument("container", help="目标容器名称")

    status_parser = sub.add_parser("status", help="查询容器与网络的连接状态")
    status_parser.add_argument("container", help="目标容器名称")

    return parser


def handle_cli(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "connect":
            changed = link_container_to_seed_network(
                args.container,
                network_name=args.network,
                create_network=args.create_network,
                aliases=args.aliases,
            )
            alias_str = _format_aliases(args.aliases)
            if changed:
                print(
                    f"[+] 已将容器 {args.container} 接入网络 {args.network} (别名: {alias_str})"
                )
            else:
                print(
                    f"[=] 容器 {args.container} 原本已在网络 {args.network} 中 (别名: {alias_str})"
                )
            return 0

        if args.command == "disconnect":
            changed = unlink_container_from_seed_network(
                args.container,
                network_name=args.network,
            )
            if changed:
                print(f"[-] 已将容器 {args.container} 从网络 {args.network} 断开")
            else:
                print(f"[=] 容器 {args.container} 本就不在网络 {args.network} 中")
            return 0

        if args.command == "status":
            networks = _inspect_container_networks(args.container)
            connected = _connected(networks, args.network)
            aliases = networks.get(args.network, {}).get("Aliases") if connected else []
            alias_str = _format_aliases(aliases) if isinstance(aliases, list) else "<无>"
            print(
                f"[*] 容器 {args.container} {('已' if connected else '未')}连接网络 {args.network} (别名: {alias_str})"
            )
            return 0
    except SeedNetworkError as exc:
        parser.error(str(exc))

    parser.error("未知命令")
    return 2


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    exit_code = handle_cli()
    raise SystemExit(exit_code)


if __name__ == "__main__":  # pragma: no cover
    main()
