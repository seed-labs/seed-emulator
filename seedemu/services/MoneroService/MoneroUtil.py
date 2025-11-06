"""Monero 服务公共工具函数与数据结构。

设计目标：
    * 为 `MoneroService` 提供可复用的配置数据结构
    * 封装常用的脚本拼装逻辑
    * 尽量保持纯数据、纯函数，方便单元测试
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .MoneroEnum import (
    MoneroBinarySource,
    MoneroMiningTrigger,
    MoneroNetworkType,
    MoneroNodeKind,
    MoneroNodeRole,
    MoneroSeedConnectionMode,
)
from .MoneroWallet import MoneroWalletConfig


class MoneroWalletSpec(MoneroWalletConfig):
    """钱包配置别名。继承后仅是语义上区分“模板”与“运行时配置”。"""

    pass


@dataclass
class MoneroBinaryPaths:
    """节点使用的可执行文件路径集合。"""

    monerod: str = "monerod"
    wallet_cli: str = "monero-wallet-cli"
    wallet_rpc: str = "monero-wallet-rpc"

    def clone(self) -> "MoneroBinaryPaths":
        return MoneroBinaryPaths(
            monerod=self.monerod,
            wallet_cli=self.wallet_cli,
            wallet_rpc=self.wallet_rpc,
        )


@dataclass
class MoneroNodeOptions:
    """描述单个节点的安装与运行选项。"""

    kind: MoneroNodeKind = MoneroNodeKind.FULL
    role: MoneroNodeRole = MoneroNodeRole.CLIENT
    binary_source: MoneroBinarySource = MoneroBinarySource.MIRROR
    binaries: MoneroBinaryPaths = field(default_factory=MoneroBinaryPaths)

    wallet: MoneroWalletSpec = field(default_factory=MoneroWalletSpec)
    enable_wallet: bool = True

    enable_mining: bool = False
    mining_threads: int = 1
    mining_address: Optional[str] = None
    mining_trigger: MoneroMiningTrigger = MoneroMiningTrigger.AFTER_SEED_REACHABLE

    connect_mode: MoneroSeedConnectionMode = MoneroSeedConnectionMode.EXCLUSIVE
    preferred_peers: List[str] = field(default_factory=list)
    upstream_nodes: List[str] = field(default_factory=list)

    p2p_bind_ip: str = "0.0.0.0"
    p2p_bind_port: Optional[int] = None
    rpc_bind_ip: str = "0.0.0.0"
    rpc_bind_port: Optional[int] = None
    zmq_bind_ip: str = "0.0.0.0"
    zmq_bind_port: Optional[int] = None

    data_dir: str = "/var/lib/monero"
    log_dir: str = "/var/log/monero"
    persist_data: bool = True

    wait_for_seed: bool = True
    seed_retry_interval: int = 5
    seed_retry_attempts: int = 60

    rpc_poll_interval: int = 5
    rpc_poll_max_attempts: int = 120

    fixed_difficulty: Optional[int] = None
    extra_daemon_args: List[str] = field(default_factory=list)
    extra_env: Dict[str, str] = field(default_factory=dict)

    expose_p2p: bool = False
    expose_rpc: bool = False
    expose_zmq: bool = False

    name: Optional[str] = None

    def clone(self) -> "MoneroNodeOptions":
        return MoneroNodeOptions(
            kind=self.kind,
            role=self.role,
            binary_source=self.binary_source,
            binaries=self.binaries.clone(),
            wallet=self.wallet.clone(),
            enable_wallet=self.enable_wallet,
            enable_mining=self.enable_mining,
            mining_threads=self.mining_threads,
            mining_address=self.mining_address,
            mining_trigger=self.mining_trigger,
            connect_mode=self.connect_mode,
            preferred_peers=list(self.preferred_peers),
            upstream_nodes=list(self.upstream_nodes),
            p2p_bind_ip=self.p2p_bind_ip,
            p2p_bind_port=self.p2p_bind_port,
            rpc_bind_ip=self.rpc_bind_ip,
            rpc_bind_port=self.rpc_bind_port,
            zmq_bind_ip=self.zmq_bind_ip,
            zmq_bind_port=self.zmq_bind_port,
            data_dir=self.data_dir,
            log_dir=self.log_dir,
            persist_data=self.persist_data,
            wait_for_seed=self.wait_for_seed,
            seed_retry_interval=self.seed_retry_interval,
            seed_retry_attempts=self.seed_retry_attempts,
            rpc_poll_interval=self.rpc_poll_interval,
            rpc_poll_max_attempts=self.rpc_poll_max_attempts,
            fixed_difficulty=self.fixed_difficulty,
            extra_daemon_args=list(self.extra_daemon_args),
            extra_env=dict(self.extra_env),
            expose_p2p=self.expose_p2p,
            expose_rpc=self.expose_rpc,
            expose_zmq=self.expose_zmq,
            name=self.name,
        )


@dataclass
class MoneroNetworkDefaults:
    """网络级默认配置。"""

    net_type: MoneroNetworkType = MoneroNetworkType.TESTNET
    binary_source: MoneroBinarySource = MoneroBinarySource.MIRROR
    wallet: MoneroWalletSpec = field(default_factory=MoneroWalletSpec)
    mining_trigger: MoneroMiningTrigger = MoneroMiningTrigger.AFTER_SEED_REACHABLE
    seed_connection_mode: MoneroSeedConnectionMode = MoneroSeedConnectionMode.EXCLUSIVE

    default_p2p_port: int = 28080
    default_rpc_port: int = 28081
    default_zmq_port: int = 28082

    light_wallet_rpc_start: int = 38088
    auto_assign_ports: bool = True

    fixed_difficulty: Optional[int] = None
    default_mining_threads: int = 1

    persist_data: bool = True

    def clone(self) -> "MoneroNetworkDefaults":
        return MoneroNetworkDefaults(
            net_type=self.net_type,
            binary_source=self.binary_source,
            wallet=self.wallet.clone(),
            mining_trigger=self.mining_trigger,
            seed_connection_mode=self.seed_connection_mode,
            default_p2p_port=self.default_p2p_port,
            default_rpc_port=self.default_rpc_port,
            default_zmq_port=self.default_zmq_port,
            light_wallet_rpc_start=self.light_wallet_rpc_start,
            auto_assign_ports=self.auto_assign_ports,
            fixed_difficulty=self.fixed_difficulty,
            default_mining_threads=self.default_mining_threads,
            persist_data=self.persist_data,
        )


def infer_default_ports(net_type: MoneroNetworkType) -> MoneroNetworkDefaults:
    """根据网络类型生成默认端口配置。"""

    if net_type == MoneroNetworkType.MAINNET:
        return MoneroNetworkDefaults(
            net_type=net_type,
            default_p2p_port=18080,
            default_rpc_port=18081,
            default_zmq_port=18082,
            light_wallet_rpc_start=28089,
        )

    if net_type == MoneroNetworkType.STAGENET:
        return MoneroNetworkDefaults(
            net_type=net_type,
            default_p2p_port=38080,
            default_rpc_port=38081,
            default_zmq_port=38082,
            light_wallet_rpc_start=48088,
        )

    if net_type == MoneroNetworkType.CUSTOM:
        return MoneroNetworkDefaults(
            net_type=net_type,
            default_p2p_port=28080,
            default_rpc_port=28081,
            default_zmq_port=28082,
            light_wallet_rpc_start=38088,
        )

    # 默认为 testnet
    return MoneroNetworkDefaults(
        net_type=MoneroNetworkType.TESTNET,
        default_p2p_port=28080,
        default_rpc_port=28081,
        default_zmq_port=28082,
        light_wallet_rpc_start=38088,
    )


def build_endpoint(address: str, port: int) -> str:
    """将 IP 与端口组合成 `host:port` 形式。"""

    return f"{address}:{port}"


def sanitize_extra_args(args: List[str]) -> List[str]:
    """过滤空字符串，确保生成的命令更紧凑。"""

    return [item.strip() for item in args if item and item.strip()]


