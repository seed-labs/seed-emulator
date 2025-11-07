from __future__ import annotations
from enum import Enum

class MoneroNodeKind(Enum):
    """节点类别：决定底层守护进程运行模式。"""

    FULL = "full"  # 运行完整 monerod/全量区块数据，可挖矿、可作为 seed。
    PRUNED = "pruned"  # 启用 --prune-blockchain 的全节点，保留验证能力但裁剪历史。
    LIGHT = "light"  # 不运行 monerod，仅运行 monero-wallet-rpc/CLI 作为轻钱包。


class MoneroNodeRole(Enum):
    """节点角色：主要用于 Full/Pruned 节点的职责划分。"""

    SEED = "seed"  # 负责网络引导/节点发现，可选挖矿能力。
    CLIENT = "client"  # 普通对等节点，参与区块传播与同步。
    STANDALONE = "standalone"  # 不依赖角色语义的独立节点（轻钱包等）。


class MoneroSeedConnectionMode(Enum):
    """非种子节点如何连接到种子节点。"""

    EXCLUSIVE = "exclusive"  # 只连接指定节点，等价于 monerod --add-exclusive-node。
    PRIORITY = "priority"  # 优先连接指定节点，使用 --add-priority-node。
    SEED = "seed"  # 作为临时种子，通过 --seed-node 获取拓扑后可断开。


class MoneroNetworkType(Enum):
    """Monero 网络类型，影响默认端口与启动参数。"""

    MAINNET = "mainnet"  # 生产网络，默认端口 1808x 系列，无额外 flag。
    TESTNET = "testnet"  # 官方测试网，对应 --testnet 及 2808x 端口。
    STAGENET = "stagenet"  # 介于测试与主网之间，对应 --stagenet 与 3808x 端口。
    CUSTOM = "custom"  # 自定义网络，使用用户提供的端口/flag。


class MoneroBinarySource(Enum):
    """守护进程安装方式。"""

    MIRROR = "mirror"  # 使用预构建的官方 Monero 镜像。
    CUSTOM = "custom"  # 用户自行提供二进制或镜像。


class MoneroMiningTrigger(Enum):
    """挖矿启动时机。"""

    ON_BOOT = "on-boot"  # 容器启动后立即触发挖矿（不等待网络）。
    AFTER_SEED_REACHABLE = "after-seed"  # 等待种子节点可达后调用 start_mining。
    MANUAL = "manual"  # 不自动挖矿，由用户手动触发。


class MoneroWalletMode(Enum):
    """钱包创建策略。"""

    NONE = "none"  # 不创建钱包，适用于纯协议或外部钱包场景。
    AUTO_GENERATED = "auto-generated"  # 自动生成新钱包并保存主地址。
    IMPORT_MNEMONIC = "import-mnemonic"  # 根据助记词导入既有账户。
    EXISTING_FILE = "existing-file"  # 使用已有的钱包文件并跳过生成流程。
