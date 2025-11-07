#!/usr/bin/env python3
# encoding: utf-8

"""在基础 10 Stub-AS 网络上部署 MoneroService 的示例脚本。

该示例仿照 `examples/blockchain/D01_ethereum_pos/ethereum_pos.py` 的结构，
利用 `Makers.makeEmulatorBaseWith10StubASAndHosts()` 构建底层拓扑，并按照
预期角色创建以下 Monero 节点：

* AS150-154: host_0 作为种子节点，host_1 作为 full client（仅 AS150 的 client 节点挖矿）。
* AS160-161: 每个 AS 一个 full client 节点。
* AS162-163: 每个 AS 一个 light wallet 节点。
* AS164: 一个 pruned 节点。

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
    emu.addBinding(Binding(vnode, filter=Filter(asn=asn, nodeName=f"host_{host_index}")))


###############################################################################
# Set the platform information
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

hosts_per_stub_as = 3
emu = Makers.makeEmulatorBaseWith10StubASAndHosts(hosts_per_stub_as=hosts_per_stub_as)

monero = MoneroService()
network = monero.createNetwork("base-monero", net_type=MoneroNetworkType.TESTNET)
network.setSeedConnectionMode(MoneroSeedConnectionMode.EXCLUSIVE)
network.setFixedDifficulty(2000)

mining_wallet = MoneroWalletSpec(
    mode=MoneroWalletMode.AUTO_GENERATED,
    password="miner",
    enable_rpc=True,
    rpc_user="miner",
    rpc_password="miner",
    allow_external_rpc=False,
)

light_wallet_template = MoneroWalletSpec(
    mode=MoneroWalletMode.AUTO_GENERATED,
    password="light",
    enable_rpc=True,
    rpc_user="light",
    rpc_password="light",
    allow_external_rpc=True,
)

seed_wallet = MoneroWalletSpec(
    mode=MoneroWalletMode.AUTO_GENERATED,
    password="seedemu",
    enable_rpc=True,
    rpc_user="monero",
    rpc_password="seedemu",
    allow_external_rpc=False,
)

client_wallet = MoneroWalletSpec(
    mode=MoneroWalletMode.AUTO_GENERATED,
    password="client",
    enable_rpc=True,
    rpc_user="client",
    rpc_password="client",
    allow_external_rpc=False,
)

# AS150-154：host_0 为种子节点，host_1 为 full client（仅 AS150 的 client 挖矿）。
seed_asns = [150, 151, 152, 153, 154]
for asn in seed_asns:
    seed_vnode = f"monero-seed-{asn}"
    seed_server = network.createNode(seed_vnode, kind=MoneroNodeKind.FULL, binary_source=MoneroBinarySource.MIRROR)
    seed_server.setSeedRole().setWallet(seed_wallet).enableWalletRpc(
        user=seed_wallet.rpc_user,
        password=seed_wallet.rpc_password,
        allow_external=False,
    )
    seed_server.setDisplayName(f"Monero-Seed-{asn}")
    _bind(emu, seed_vnode, asn, host_index=0)

    client_vnode = f"monero-client-{asn}"
    client_server = network.createNode(client_vnode, kind=MoneroNodeKind.FULL, binary_source=MoneroBinarySource.MIRROR)
    client_server.setClientRole().setWallet(client_wallet)
    client_server.setDisplayName(f"Monero-Client-{asn}")

    if asn == 150:
        client_server.setWallet(mining_wallet).enableWalletRpc(
            user=mining_wallet.rpc_user,
            password=mining_wallet.rpc_password,
            allow_external=False,
        )
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

# AS160-161：各一个 full client 节点。
for asn in [160, 161]:
    vnode = f"monero-client-{asn}"
    server = network.createNode(vnode, kind=MoneroNodeKind.FULL, binary_source=MoneroBinarySource.MIRROR)
    server.setClientRole().setWallet(client_wallet).enableWalletRpc(
        user=client_wallet.rpc_user,
        password=client_wallet.rpc_password,
        allow_external=False,
    )
    server.setDisplayName(f"Monero-Client-{asn}")
    _bind(emu, vnode, asn, host_index=0)

# AS162-163：各一个 light wallet 节点。
for asn in [162, 163]:
    vnode = f"monero-light-{asn}"
    server = network.createNode(vnode, kind=MoneroNodeKind.LIGHT, binary_source=MoneroBinarySource.MIRROR)
    server.setWallet(light_wallet_template).enableWalletRpc(allow_external=True)
    server.setDisplayName(f"Monero-Light-{asn}")
    _bind(emu, vnode, asn, host_index=0)

# AS164：一个 pruned 节点。
pruned_vnode = "monero-pruned-164"
pruned_server = network.createNode(pruned_vnode, kind=MoneroNodeKind.PRUNED)
pruned_server.setClientRole().setWallet(client_wallet).enableWalletRpc(
    user=client_wallet.rpc_user,
    password=client_wallet.rpc_password,
    allow_external=False,
)
pruned_server.setDisplayName("Monero-Pruned-164")
_bind(emu, pruned_vnode, 164, host_index=0)

emu.addLayer(monero)

emu.render()

docker = Docker(internetMapEnabled=True, platform=platform)
emu.compile(docker, './output', override = True)


