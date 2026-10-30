#!/usr/bin/env python3
# encoding: utf-8

from seedemu import *
from examples.internet.B00_mini_internet import mini_internet
import os, sys

###############################################################################
# Set the platform information
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

mini_internet.run(dumpfile='./base_internet.bin')

emu = Emulator()

# Load the pre-built component
emu.load('./base_internet.bin')

# Render the emulation
emu.render()

docker = Docker(platform=platform)

# Create the first InternetMap bundle with an isolated Docker bridge network.
# Its emulator-service backend can communicate with the other visualization
# containers on this bundle network, but it is not attached to an emulator
# network. The suffix keeps its generated container names unique.
bundle = InternetMap(emu, ".map.seed")
# Customize the bundle network; provide at least one IP per container, in creation order.
# All IPs must belong to the configured subnet, which should not overlap other networks.
bundle.setDefaultExternalNetwork(
    name="internetMap_network",
    prefix="172.30.0.0/24",
    ip_addresses=[f"172.30.0.{i}" for i in range(10, 14)],
    default_router="172.30.0.1"
)
# Provide a host port pool (range excludes the stop value); InternetMap needs at least 3 ports.
bundle.setPorts(list(range(8081, 8089)))
# Register the isolated bundle; Docker will configure and install it during
docker.addContainerBundle(bundle)

# Create a second InternetMap instance. Its suffix, bridge network, and host
# port range are different from the first instance.
bundle_join_emu_network = InternetMap(emu, ".map.seed.emu")
bundle_join_emu_network.setDefaultExternalNetwork(
    name="internetMap_network_emu",
    prefix="172.40.0.0/24",
    ip_addresses=[f"172.40.0.{i}" for i in range(10, 14)],
    default_router="172.40.0.1"
)
# Attach seedemu_emulator_service_backend to the selected emulator network.
# This adds a second network interface to that container, allowing the
# emulator service API to communicate with containers on the emulated network.
# The first bundle does not make this attachment and remains bridge-only.
bundle_join_emu_network.enableInternalNetwork()
bundle_join_emu_network.setPorts(list(range(8091, 8099)))
docker.addContainerBundle(bundle_join_emu_network)

# Compile the emulation and generate both InternetMap deployments.
emu.compile(docker, './output', override=True)
