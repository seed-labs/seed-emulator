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
        self._required_internal_address_count = 1
        self._required_port_count = 1

    def configure(self):
        """!
        @brief Configure services, networks, files and startup routing.

        @raises AssertionError when the configured host-port pool is too small.
        """
        super().configure()

        # Lookup keys are logical names; getHostname() appends the suffix.
        app = self._containers["demo-app"]
        helper = self._containers["demo-helper"]

        app.updateServiceConfig(
            {
                "image": "debian:bookworm-slim",
                "environment": {"DEMO_SUFFIX": self.getSuffix()},
                "ports": [f"{self._ports[0]}:8080"],
                "build": f"./{app.getHostname()}",
            }
        )
        for index, network in enumerate(self._external_networks):
            network_name = network["network_name"]
            ip_addresses = network["ip_addresses"]
            app.joinExternalNetwork(
                network_name=network_name,
                hostname=app.getHostname(),
                ip_address=ip_addresses[0],
            )
            helper.joinExternalNetwork(
                network_name=network_name,
                hostname=helper.getHostname(),
                ip_address=ip_addresses[1],
            )
            # Add the short name-e<suffix> aliases only for the first external
            # network; network-specific aliases below are added for every network.
            if index == 0:
                self.addEtcHostsRecord(app.getName() + "-e" + self._suffix, network["ip_addresses"][0])
                self.addEtcHostsRecord(helper.getName() + "-e" + self._suffix, network["ip_addresses"][1])
            self.addEtcHostsRecord(f"{app.getName()}-{network_name}", ip_addresses[0])
            self.addEtcHostsRecord(f"{helper.getName()}-{network_name}", ip_addresses[1])

        helper.updateServiceConfig(
            {
                "image": "debian:bookworm-slim",
                "command": "sleep infinity",
            }
        )
        # Install a complete startup script for hosts injection. exec sleep keeps
        # the helper running; the trailing /bin/sh delegation is never reached.
        helper.setEntrypointWrapper(
            original_entrypoint="/bin/sh",
            commands=["exec sleep infinity"],
        )
        for index, network in enumerate(self._internal_networks):
            app.joinInternalNetwork(
                asn=network["asn"],
                hostname=app.getHostname(),
                network_name=network["network_name"],
                ip_address=network["ip_addresses"][0],
                default_route=network["default_route"],
            )
            # Map the app's generated hostname to its first internal address.
            # The network-specific alias below is added for every internal network.
            if index == 0:
                self.addEtcHostsRecord(app.getHostname(), network["ip_addresses"][0])
            self.addEtcHostsRecord(f"{app.getName()}-{network['full_network_name']}", network["ip_addresses"][0])

        # Stage this script in the image; the wrapper does not execute it.
        app.setFile(
            "/usr/local/bin/demo-message.sh",
            "#!/bin/sh\necho 'ContainerBundle demo is running'\n",
        )
        # Print a message and stay in sleep infinity before any /bin/sh
        # delegation. No HTTP server listens on the published container port.
        app.setEntrypointWrapper(
            original_entrypoint="/bin/sh",
            commands=[
                'echo "service=$0 hostname=$(hostname)"',
                "sleep infinity",
            ],
        )