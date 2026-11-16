#!/usr/bin/env python3
# encoding: utf-8

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from seedemu.compiler import Docker, Platform
from seedemu.core import Emulator
import os
from examples.internet.B00_mini_internet import mini_internet
from demoContainerBundle import DemoContainerBundle


# Set the platform information
script_name = os.path.basename(__file__)

platform = None
if len(sys.argv) == 1:
    platform = Platform.AMD64
elif len(sys.argv) == 2:
    if sys.argv[1].lower() == "amd":
        platform = Platform.AMD64
    elif sys.argv[1].lower() == "arm":
        platform = Platform.ARM64
    else:
        print(f"Usage:  {script_name} amd|arm")
        sys.exit(1)
else:
    print(f"Usage:  {script_name} amd|arm")
    sys.exit(1)

mini_internet.run(dumpfile="./base_internet.bin")

emu = Emulator()

# Load the pre-built component
emu.load("./base_internet.bin")
# Render the emulation
emu.render()

docker = Docker(platform=platform)
# Register a custom bundle. The demo bundle shows
# how to configure service attributes, attach containers to external and
# emulator networks, stage files and /etc/hosts entries, and wrap an
# image entrypoint. It uses a separate Docker network and port.
demo_bundle = DemoContainerBundle(emu, ".demo.seed")
demo_bundle.addExternalNetwork(
    network_name="demo_bundle_network",
    prefix="172.31.0.0/24",
    ip_addresses=["172.31.0.10", "172.31.0.11"],
    default_route="172.31.0.1",
)
demo_bundle.setPorts([8090])
# Attach the app to AS151 and AS152 in addition to the private bridge.
# The setter checks the required addresses and any explicit router against
# rendered interfaces, but does not reserve addresses or allocate new ones.
demo_bundle.addInternalNetwork(
    asn="151", network_name="net0", ip_addresses=["10.151.0.16"], default_route="10.151.0.254"
)
demo_bundle.addInternalNetwork(
    asn="152", network_name="net0", ip_addresses=["10.152.0.16"],
)
# Registration does not call configure(). Docker configures and installs the
# prepared containers later, during emu.compile().
docker.addContainerBundle(demo_bundle)
###############################################################################
# Compilation
emu.compile(docker, "./output", override=True)
demo_bundle.printEtcHostsRecords()
