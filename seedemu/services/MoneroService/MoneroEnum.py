from __future__ import annotations
from enum import Enum

class MoneroNodeKind(Enum):
    """Node type describing how the underlying daemon operates."""

    FULL = "full"  # Runs the full monerod with complete blockchain data; can mine and act as a seed.
    PRUNED = "pruned"  # Full node with ``--prune-blockchain`` enabled; keeps validation ability while trimming history.
    LIGHT = "light"  # Does not run monerod; only runs wallet RPC/CLI as a light wallet.


class MoneroNodeRole(Enum):
    """Logical role assigned to a node, mostly for full/pruned nodes."""

    SEED = "seed"  # Provides network bootstrapping and peer discovery, optionally mines.
    CLIENT = "client"  # Regular peer that participates in block propagation and sync.
    STANDALONE = "standalone"  # Independent node without special role semantics (e.g., light wallet).


class MoneroSeedConnectionMode(Enum):
    """How non-seed nodes connect to seed nodes."""

    EXCLUSIVE = "exclusive"  # Connect only to the specified nodes (monerod ``--add-exclusive-node``).
    PRIORITY = "priority"  # Prefer the specified nodes (monerod ``--add-priority-node``).
    SEED = "seed"  # Temporarily treat the node as a seed (monerod ``--seed-node``) then disconnect.


class MoneroNetworkType(Enum):
    """Monero network type, which influences default ports and flags."""

    MAINNET = "mainnet"  # Production network; default ports 1808x, no extra flags.
    TESTNET = "testnet"  # Official testnet; uses ``--testnet`` and ports 2808x.
    STAGENET = "stagenet"  # Pre-production network; uses ``--stagenet`` and ports 3808x.
    CUSTOM = "custom"  # Custom network with user-provided ports/flags.


class MoneroBinarySource(Enum):
    """How node binaries are obtained."""

    MIRROR = "mirror"  # Use the prebuilt official Monero binaries.
    CUSTOM = "custom"  # Use binaries or images provided by the user.


class MoneroMiningTrigger(Enum):
    """When mining should start."""

    ON_BOOT = "on-boot"  # Start mining immediately when the container starts.
    AFTER_SEED_REACHABLE = "after-seed"  # Start mining after the seed node becomes reachable.
    MANUAL = "manual"  # Mining is not automatic and must be triggered manually.


class MoneroWalletMode(Enum):
    """Available wallet creation strategies."""

    NONE = "none"  # Do not create a wallet (useful for protocol-only scenarios).
    AUTO_GENERATED = "auto-generated"  # Generate a new wallet automatically and save the primary address.
    IMPORT_MNEMONIC = "import-mnemonic"  # Import an existing account using a mnemonic phrase.
    EXISTING_FILE = "existing-file"  # Use an existing wallet file and skip generation.
