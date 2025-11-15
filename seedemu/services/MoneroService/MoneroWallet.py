from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import List, Optional

from .MoneroEnum import MoneroWalletMode


@dataclass
class MoneroWalletConfig:
    """Describe how a wallet should be generated or imported.

    Attributes:
        mode: :class:`MoneroWalletMode` specifying how the wallet is sourced.
        wallet_path: Location of the wallet file (used for ``EXISTING_FILE`` or custom directories).
        password: Wallet password, defaults to ``"seedemu"`` when not provided.
        mnemonic: Mnemonic phrase used in ``IMPORT_MNEMONIC`` mode.
        restore_height: Block height to start scanning from to reduce sync time.
        enable_rpc: Whether to start ``monero-wallet-rpc``.
        rpc_bind_ip: IP address for the wallet RPC service.
        rpc_bind_port: Port for the wallet RPC service.
        rpc_user: Username for RPC authentication.
        rpc_password: Password for RPC authentication.
        allow_external_rpc: Whether remote RPC connections are accepted.
        extra_rpc_flags: Additional flags passed to ``monero-wallet-rpc``.
        auto_save_primary_address: Save the primary address to a file for mining automation.
    """

    mode: MoneroWalletMode = MoneroWalletMode.AUTO_GENERATED
    wallet_path: str = "/var/lib/monero/wallets/seedemu-wallet"
    password: str = "seed"
    mnemonic: Optional[str] = None
    restore_height: int = 0

    enable_rpc: bool = False
    rpc_bind_ip: str = "0.0.0.0"
    rpc_bind_port: int = 18088
    rpc_user: Optional[str] = "seed"
    rpc_password: Optional[str] = "seed"
    allow_external_rpc: bool = True
    extra_rpc_flags: List[str] = field(default_factory=list)

    auto_save_primary_address: bool = True
    primary_address_path: str = "/var/lib/monero/wallets/primary-address.txt"

    def clone(self) -> "MoneroWalletConfig":
        """Return a shallow copy of the current configuration.

        ``dataclasses.asdict`` performs deep copies for list/dict fields, avoiding
        shared references between nodes.
        """

        return self.__class__(**asdict(self))

    def needs_wallet_file(self) -> bool:
        """Return ``True`` if an existing wallet file is required."""

        return self.mode == MoneroWalletMode.EXISTING_FILE
