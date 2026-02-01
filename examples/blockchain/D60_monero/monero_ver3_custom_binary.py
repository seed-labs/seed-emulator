#!/usr/bin/env python3
# encoding: utf-8

"""Custom binaries example: deploy a blockchain using your own Monero executables."""

from __future__ import annotations

import os
import sys

from seedemu import Binding, Filter, Makers
from seedemu.compiler import Docker, Platform
from seedemu.services.MoneroService import MoneroBinarySource, MoneroMiningTrigger, MoneroService

CUSTOM_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "custom")) # The directory containing your custom Monero binaries
CUSTOM_BIN_FILES = {
    "/usr/local/bin/monerod": "monerod",                                        # The path to the monerod binary in the custom directory
    "/usr/local/bin/monero-wallet-cli": "monero-wallet-cli",                    # The path to the monero-wallet-cli binary in the custom directory
    "/usr/local/bin/monero-wallet-rpc": "monero-wallet-rpc",                    # The path to the monero-wallet-rpc binary in the custom directory
} # The mapping of container paths to custom binary filenames


def _bind(emu, vnode: str, asn: int, host_index: int) -> None:
    """Bind a virtual node to a specific host under a given AS."""
    emu.addBinding(Binding(vnode, filter=Filter(asn=asn, nodeName=f"^host_{host_index}$")))

def _apply_custom_binaries(server) -> None:
    """Mark node to use custom binaries and provide the file mapping."""
    server.options.binary_source = MoneroBinarySource.CUSTOM
    server.options.custom_binary_imports = {
        container_path: os.path.join(CUSTOM_DIR, filename)
        for container_path, filename in CUSTOM_BIN_FILES.items()
    }

# Basic validation that the expected custom binaries are present.
# Validate that all required custom binaries exist before proceeding
missing = [
    os.path.join(CUSTOM_DIR, filename)
    for filename in CUSTOM_BIN_FILES.values()
    if not os.path.isfile(os.path.join(CUSTOM_DIR, filename))
]
if missing:
    print("Missing custom Monero binaries:", ", ".join(missing))
    sys.exit(1)

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

monero = MoneroService()
blockchain = monero.createBlockchain("base-monero")
blockchain.setFixedDifficulty(2000)

seed_asns = [150, 151, 152, 153, 154]
for asn in seed_asns:
    seed_vnode = f"monero-seed-{asn}"
    seed_server = blockchain.createSeedNode(seed_vnode)
    _apply_custom_binaries(seed_server)
    seed_server.setDisplayName(f"Monero-Seed-{asn}")
    _bind(emu, seed_vnode, asn, host_index=0)

    client_vnode = f"monero-client-{asn}"
    client_server = blockchain.createClientNode(client_vnode)
    if asn == 150:
        # Only AS150 client mines; 1 thread; start after seed becomes reachable
        client_server.enableMining(
            threads=1,
            trigger=MoneroMiningTrigger.AFTER_SEED_REACHABLE,
        )
    _apply_custom_binaries(client_server) # Mark node to use custom binaries and provide the file mapping.
    client_server.setDisplayName(f"Monero-Client-{asn}")
    _bind(emu, client_vnode, asn, host_index=1)

for asn in [160, 161]:
    vnode = f"monero-client-{asn}"
    server = blockchain.createClientNode(vnode)
    _apply_custom_binaries(server)
    server.setDisplayName(f"Monero-Client-{asn}")
    _bind(emu, vnode, asn, host_index=0)

for asn in [162, 163]:
    vnode = f"monero-light-{asn}"
    server = blockchain.createLightWallet(vnode)
    _apply_custom_binaries(server)
    server.setDisplayName(f"Monero-Light-{asn}")
    _bind(emu, vnode, asn, host_index=0)

pruned_vnode = "monero-pruned-164"
pruned_server = blockchain.createPrunedNode(pruned_vnode)
_apply_custom_binaries(pruned_server)
pruned_server.setDisplayName("Monero-Pruned-164")
_bind(emu, pruned_vnode, 164, host_index=0)

emu.addLayer(monero)
emu.render()

docker = Docker(internetMapEnabled=True, platform=platform)
emu.compile(docker, "./output", override=True)


