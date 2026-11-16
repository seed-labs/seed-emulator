#!/usr/bin/env python3
# encoding: utf-8

from pathlib import Path
import sys

# Allow repository imports when running this file directly from its directory.
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from seedemu import *
from examples.internet.B00_mini_internet import mini_internet
import os

###############################################################################
# Accept an optional amd/arm argument; default to AMD64.
script_name = os.path.basename(__file__)

platform = None
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

# Generate a reusable mini-Internet component without compiling it here.
# Relative paths use the current working directory; run from this example folder.
mini_internet.run(dumpfile='./base_internet.bin')

emu = Emulator()

# Load the component just generated above into a separate emulator instance.
emu.load('./base_internet.bin')

# Configure node interfaces before checking static address availability and
# looking up the internal network's default router.
emu.render()

docker = Docker(platform=platform)

# Create one stack: emulator API, topology UI, geographic UI, and traffic observer.
# The suffix distinguishes generated services, container names, and build folders;
# it does not select a subnet. With no explicit addExternalNetwork(), configure()
# registers the default internetMap_network bridge (172.30.0.0/24, gateway .1).
# API and UIs use .10, .11, and .12; the observer uses host networking.
internet_map = InternetMap(emu, ".map.seed.emu")
# Give the API an emulator-facing interface on AS151/net0 at an explicit IP.
# Without it, the API retains bridge and Docker-socket access, but has no direct
# emulator-network attachment. Availability checks do not reserve this address.
# Omitting default_route requests the gateway from the rendered registry.
internet_map.addInternalNetwork(asn="151", network_name="net0", ip_addresses=["10.151.0.16"])
# AS161
internet_map.addInternalNetwork(asn="161", network_name="net0", ip_addresses=["10.161.0.16"])
# Only the API uses the first address of the first internal pool. The UIs reach
# the API over the private bridge; the observer remains on the host network.
# Three host ports are required in this order: observer control, topology HTTP,
# geographic HTTP (for example [8091, 8092, 8093]); shorter lists fail validation.
internet_map.setPorts([8091, 8092, 8093])
# Registration only: configure() and install() run later during emu.compile().
docker.addContainerBundle(internet_map)

# Generate one InternetMap deployment alongside the emulator nodes, replacing
# existing output. Compilation writes files; it does not build or start Docker.
emu.compile(docker, './output', override=True)
