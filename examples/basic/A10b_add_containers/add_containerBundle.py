#!/usr/bin/env python3
# encoding: utf-8

from seedemu.compiler import Docker, Platform
from seedemu.core import Emulator
import sys, os
from examples.internet.B00_mini_internet import mini_internet
from seedemu.containerBundle import ContainerBundle


class DemoContainerBundle(ContainerBundle):
    """!
    @brief Small bundle demonstrating ContainerBundle extension points.
    """

    def __init__(self, emulator, suffix=".demo.seed"):
        """!
        @brief Create the demonstration bundle and its containers.

        @param emulator emulator to which this bundle is attached.
        @param suffix suffix appended to generated container hostnames.
        """
        super().__init__(emulator=emulator, suffix=suffix)
        self._createContainer("demo-app", suffix)
        self._createContainer("demo-helper", suffix)
        # Only demo-app needs an internal address and a published host port.
        self._required_emu_network_address_number = 1
        self._required_port_number = 1

    def configure(self):
        """!
        @brief Configure services, networks, files and startup routing.

        @raises RuntimeError when no default bundle network was configured.
        @raises ValueError when the configured host-port pool is too small.
        """
        super().configure()

        network = self.getDefaultExternalNetwork()
        if network is None:
            raise RuntimeError("DemoContainerBundle requires a default network")

        # Registration keys include the suffix; getName() keeps the logical name.
        containers = self.getContainers()
        app = self.getContainer("demo-app" + self._suffix)
        helper = containers["demo-helper" + self._suffix]
        app.getName()
        app.getHostname()

        app.setContentAttribute(
            {
                "image": "debian:bookworm-slim",
                "environment": {"DEMO_SUFFIX": self.getSuffix()},
                "ports": [f"{self._ports.pop()}:8080"],
                "build": f"./{app.getHostname()}",
            }
        )
        helper.setContentAttribute(
            {
                "image": "debian:bookworm-slim",
                "command": "sleep infinity",
            }
        )

        app.joinExternalNetwork(network["name"], app.getHostname(), network["ip_addresses"][0])
        helper.joinExternalNetwork(
            network["name"], helper.getHostname(), network["ip_addresses"][1]
        )

        # Prefer the caller's manual internal network. Otherwise reserve one
        # free address from a rendered host network, starting at host offset 10.
        # Allocation stores the dictionary and returns self, not a dictionary.
        # This demo requires allocation to succeed; it has no failure fallback.
        if not self._default_internal_network:
            self.allocateEmuNetworkAddress()
        app.joinInternalNetwork(
            hostname=app.getHostname(),
            network=self._default_internal_network["network"],
            ip_address=self._default_internal_network["ip_addresses"][0],
            default_route=self._default_internal_network["default_route"],
        )

        # Inspect mappings after the network attachments have been configured.
        app.getInternalHostnameIpMappings()
        app.getExternalHostnameIpMappings()
        helper.getExternalHostnameIpMappings()

        app.setEtcHosts(f"{helper.getHostname()} {network['ip_addresses'][1]}\n")
        # Stage this script in the image; the wrapper does not execute it.
        app.setFile(
            "/usr/local/bin/demo-message.sh",
            "#!/bin/sh\necho 'ContainerBundle demo is running'\n",
        )
        # Keep the demo alive after printing a message. No HTTP server is
        # started on the published container port 8080.
        app.setEntrypointWrapper(
            original_entrypoint="/bin/sh",
            commands=[
                'echo "service=$0 hostname=$(hostname)"',
                "sleep infinity",
            ],
        )


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
demo_bundle.setDefaultExternalNetwork(
    name="demo_bundle_network",
    prefix="172.31.0.0/24",
    ip_addresses=["172.31.0.10", "172.31.0.11"],
    default_router="172.31.0.1",
)
demo_bundle.setPorts([8090])
# Select the application's second interface and emulator gateway explicitly.
# The network must exist and the address must be free: this setter neither
# validates nor reserves it. Remove this call to use automatic allocation.
demo_bundle.setDefaultInternalNetwork(
    name="net_151_net0", ip_addresses=["10.151.0.16"], default_route="10.151.0.254"
)
# These mappings are empty before configure() attaches the containers.
# Inspect them after compilation to see the configured hostname/IP mappings.
demo_bundle.getInternalHostnameIpMappings()
demo_bundle.getExternalHostnameIpMappings()
docker.addContainerBundle(demo_bundle)
###############################################################################
# Compilation
emu.compile(docker, "./output", override=True)
