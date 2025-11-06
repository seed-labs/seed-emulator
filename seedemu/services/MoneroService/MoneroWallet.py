"""钱包配置相关的数据结构与辅助方法。"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import List, Optional

from .MoneroEnum import MoneroWalletMode


@dataclass
class MoneroWalletConfig:
    """描述钱包生成或导入策略。

    Attributes:
        mode: `MoneroWalletMode`，指定钱包来源。
        wallet_path: 钱包文件路径（针对 `EXISTING_FILE` 或自定义目录）。
        password: 钱包密码，若未指定则默认使用 "seedemu"。
        mnemonic: 导入助记词（`IMPORT_MNEMONIC` 模式下必填）。
        restore_height: 恢复高度，可减少同步时间。
        enable_rpc: 是否启动 `monero-wallet-rpc` 服务。
        rpc_bind_ip: RPC 监听地址。
        rpc_bind_port: RPC 监听端口。
        rpc_user: RPC 认证用户名。
        rpc_password: RPC 认证密码。
        allow_external_rpc: 是否允许外部访问 RPC。
        extra_rpc_flags: 附加给 `monero-wallet-rpc` 的参数。
        auto_save_primary_address: 是否将主地址保存到文件，供挖矿流程引用。
    """

    mode: MoneroWalletMode = MoneroWalletMode.AUTO_GENERATED
    wallet_path: str = "/var/lib/monero/wallets/seedemu-wallet"
    password: str = "seedemu"
    mnemonic: Optional[str] = None
    restore_height: int = 0

    enable_rpc: bool = False
    rpc_bind_ip: str = "0.0.0.0"
    rpc_bind_port: int = 18088
    rpc_user: Optional[str] = None
    rpc_password: Optional[str] = None
    allow_external_rpc: bool = True
    extra_rpc_flags: List[str] = field(default_factory=list)

    auto_save_primary_address: bool = True
    primary_address_path: str = "/var/lib/monero/wallets/primary-address.txt"

    def clone(self) -> "MoneroWalletConfig":
        """返回当前配置的浅拷贝。

        使用 dataclasses.asdict 可以深拷贝列表/字典字段，避免不同节点之间共享引用。
        """

        return self.__class__(**asdict(self))

    def needs_wallet_file(self) -> bool:
        """判断是否需要已经存在的钱包文件。"""

        return self.mode == MoneroWalletMode.EXISTING_FILE
