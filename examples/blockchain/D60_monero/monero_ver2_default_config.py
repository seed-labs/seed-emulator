#!/usr/bin/env python3
# encoding: utf-8

"""Concise MoneroService example using primarily default configuration."""

from __future__ import annotations

import os
import sys

from seedemu import Binding, Filter, Makers
from seedemu.compiler import Docker, Platform
from seedemu.services.MoneroService import (
    MoneroService,
    MoneroMiningTrigger,
)


def _bind(emu, vnode: str, asn: int, host_index: int) -> None:
    emu.addBinding(Binding(vnode, filter=Filter(asn=asn, nodeName=f"host_{host_index}")))

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
network = monero.createNetwork("base-monero")
network.setFixedDifficulty(2000)

seed_asns = [150, 151, 152, 153, 154]
for asn in seed_asns:
    seed_vnode = f"monero-seed-{asn}"
    seed_server = network.createSeedNode(seed_vnode)
    seed_server.setDisplayName(f"Monero-Seed-{asn}")
    _bind(emu, seed_vnode, asn, host_index=0)

    client_vnode = f"monero-client-{asn}"
    client_server = network.createClientNode(client_vnode)
    if asn == 150:
        client_server.enableMining(
            threads=1,
            trigger=MoneroMiningTrigger.AFTER_SEED_REACHABLE,
        )
    client_server.setDisplayName(f"Monero-Client-{asn}")
    _bind(emu, client_vnode, asn, host_index=1)

for asn in [160, 161]:
    vnode = f"monero-client-{asn}"
    server = network.createClientNode(vnode)
    server.setDisplayName(f"Monero-Client-{asn}")
    _bind(emu, vnode, asn, host_index=0)

for asn in [162, 163]:
    vnode = f"monero-light-{asn}"
    server = network.createLightWallet(vnode)
    server.setDisplayName(f"Monero-Light-{asn}")
    _bind(emu, vnode, asn, host_index=0)

pruned_vnode = "monero-pruned-164"
pruned_server = network.createPrunedNode(pruned_vnode)
pruned_server.setDisplayName("Monero-Pruned-164")
_bind(emu, pruned_vnode, 164, host_index=0)

emu.addLayer(monero)
emu.render()

docker = Docker(internetMapEnabled=True, platform=platform)
emu.compile(docker, "./output", override=True)


