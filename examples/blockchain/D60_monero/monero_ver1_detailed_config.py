#!/usr/bin/env python3
# encoding: utf-8

"""Deploy a Monero blockchain on the 10 Stub-AS base topology.

Topology plan:
- AS150-154: host_0 is seed; host_1 is client (only AS150 client mines)
- AS160-161: one client per AS
- AS162-163: one light wallet per AS
- AS164: one pruned node
"""

from __future__ import annotations

import os
import sys

from seedemu import Binding, Filter, Makers
from seedemu.compiler import Docker, Platform
from seedemu.services.MoneroService import (
    MoneroBinarySource,
    MoneroMiningTrigger,
    MoneroNetworkType,
    MoneroNodeKind,
    MoneroSeedConnectionMode,
    MoneroService,
    MoneroWalletMode,
    MoneroWalletSpec,
)


def _bind(emu, vnode: str, asn: int, host_index: int):
    # Bind a virtual node to a specific host under the given AS (host_index starts from 0)
    emu.addBinding(Binding(vnode, filter=Filter(asn=asn, nodeName=f"^host_{host_index}$")))


###############################################################################
# Set the platform information (select amd/arm via CLI argument)
script_name = os.path.basename(__file__)

if len(sys.argv) == 1:
    platform = Platform.AMD64
elif len(sys.argv) == 2:
    if sys.argv[1].lower() == 'amd':
        platform = Platform.AMD64
    elif sys.argv[1].lower() == 'arm':
        platform = Platform.ARM64
    else:
        print(f"Usage:  {script_name} amd|arm")
        sys.exit(1)
else:
    print(f"Usage:  {script_name} amd|arm")
    sys.exit(1)

###############################################################################
# Global configuration

hosts_per_stub_as = 3
emu = Makers.makeEmulatorBaseWith10StubASAndHosts(hosts_per_stub_as=hosts_per_stub_as)

monero = MoneroService()                                                                 # Add the Monero service as a layer
blockchain = monero.createBlockchain("base-monero", net_type=MoneroNetworkType.TESTNET)  # Create a blockchain named base-monero
blockchain.setSeedConnectionMode(MoneroSeedConnectionMode.EXCLUSIVE)                     # EXCLUSIVE: Connect only to the specified nodes (monerod ``--add-exclusive-node``).
blockchain.setFixedDifficulty(2000)                                                      # Set a small difficulty for quick blocks in demos

# Configure the mining wallet
mining_wallet = MoneroWalletSpec(
    mode=MoneroWalletMode.AUTO_GENERATED, # AUTO_GENERATED: Generate a new wallet automatically.
    password="seed",                      # The password for the wallet.
    enable_rpc=True,                      # Enable the wallet RPC.
    rpc_user="seed",                      # The username for the wallet RPC.
    rpc_password="seed",                  # The password for the wallet RPC.
    allow_external_rpc=False,             # Do not allow external RPC connections.
)

# Configure the light wallet
light_wallet_template = MoneroWalletSpec(
    mode=MoneroWalletMode.AUTO_GENERATED,
    password="seed",
    enable_rpc=True,
    rpc_user="seed",
    rpc_password="seed",
    allow_external_rpc=True,
)

# Configure the seed wallet
seed_wallet = MoneroWalletSpec(
    mode=MoneroWalletMode.AUTO_GENERATED,
    password="seed",
    enable_rpc=True,
    rpc_user="seed",
    rpc_password="seed",
    allow_external_rpc=False,
)

# Configure the client wallet
client_wallet = MoneroWalletSpec(
    mode=MoneroWalletMode.AUTO_GENERATED,
    password="seed",
    enable_rpc=True,
    rpc_user="seed",
    rpc_password="seed",
    allow_external_rpc=False,
)

###############################################################################
# Detailed configuration for each node

# AS150-154: host_0 is the seed node; host_1 is the full client (only AS150 mines).
seed_asns = [150, 151, 152, 153, 154]
for asn in seed_asns:
    seed_vnode = f"monero-seed-{asn}"
    seed_server = blockchain.createNode(seed_vnode, kind=MoneroNodeKind.FULL, binary_source=MoneroBinarySource.MIRROR)
    seed_server.setSeedRole().setWallet(seed_wallet).enableWalletRpc(
        user=seed_wallet.rpc_user,
        password=seed_wallet.rpc_password,
        allow_external=False,
    )
    seed_server.setDisplayName(f"Monero-Seed-{asn}")
    _bind(emu, seed_vnode, asn, host_index=0)

    client_vnode = f"monero-client-{asn}"
    client_server = blockchain.createNode(client_vnode, kind=MoneroNodeKind.FULL, binary_source=MoneroBinarySource.MIRROR)
    client_server.setClientRole().setWallet(client_wallet)
    client_server.setDisplayName(f"Monero-Client-{asn}")

    if asn == 150:
        client_server.setWallet(mining_wallet).enableWalletRpc(
            user=mining_wallet.rpc_user,
            password=mining_wallet.rpc_password,
            allow_external=False,
        )
        # Start mining after the seed becomes reachable; 1 mining thread for demo-friendliness
        client_server.enableMining(
            threads=1,
            trigger=MoneroMiningTrigger.AFTER_SEED_REACHABLE,
        )
    else:
        client_server.enableWalletRpc(
            user=client_wallet.rpc_user,
            password=client_wallet.rpc_password,
            allow_external=False,
        )

    _bind(emu, client_vnode, asn, host_index=1)

# AS160-161: one full client per AS
for asn in [160, 161]:
    vnode = f"monero-client-{asn}"
    server = blockchain.createNode(vnode, kind=MoneroNodeKind.FULL, binary_source=MoneroBinarySource.MIRROR)
    server.setClientRole().setWallet(client_wallet).enableWalletRpc(
        user=client_wallet.rpc_user,
        password=client_wallet.rpc_password,
        allow_external=False,
    )
    server.setDisplayName(f"Monero-Client-{asn}")
    _bind(emu, vnode, asn, host_index=0)

# AS162-163: one light wallet per AS (wallet RPC enabled; allow external access)
for asn in [162, 163]:
    vnode = f"monero-light-{asn}"
    server = blockchain.createNode(vnode, kind=MoneroNodeKind.LIGHT, binary_source=MoneroBinarySource.MIRROR)
    server.setWallet(light_wallet_template).enableWalletRpc(allow_external=True)
    server.setDisplayName(f"Monero-Light-{asn}")
    _bind(emu, vnode, asn, host_index=0)

# AS164: one pruned node (reduced disk usage; mining disabled)
pruned_vnode = "monero-pruned-164"
pruned_server = blockchain.createNode(pruned_vnode, kind=MoneroNodeKind.PRUNED)
pruned_server.setClientRole().setWallet(client_wallet).enableWalletRpc(
    user=client_wallet.rpc_user,
    password=client_wallet.rpc_password,
    allow_external=False,
)
pruned_server.setDisplayName("Monero-Pruned-164")
_bind(emu, pruned_vnode, 164, host_index=0)

###############################################################################
# Add the Monero service as a layer, then render
emu.addLayer(monero)
emu.render()
# Compile docker-compose and build context into ./output
docker = Docker(internetMapEnabled=True, platform=platform)
emu.compile(docker, './output', override = True)


