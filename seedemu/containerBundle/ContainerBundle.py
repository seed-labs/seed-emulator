"""Container bundles and their independently owned prepared containers."""

from __future__ import annotations
import yaml
from hashlib import md5
from os import mkdir, chdir
from textwrap import indent
from ipaddress import IPv4Address, IPv4Network
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import InitVar, dataclass, field

from seedemu.core.Emulator import Emulator
from seedemu.core.enums import NetworkType

SED_ETCHOSTS = """
echo "{}" >> /etc/hosts
"""


class IndentDumper(yaml.SafeDumper):
    """YAML dumper that keeps nested mappings consistently indented."""

    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow, False)


def safe_dump_pretty(data) -> str:
    """Serialize ``data`` as readable YAML without sorting mapping keys.

    Args:
        data: Mapping or sequence to serialize.

    Returns:
        The generated YAML document.
    """
    return yaml.dump(
        data,
        Dumper=IndentDumper,
        sort_keys=False,
        default_flow_style=False,
        indent=2,
    )


@dataclass(eq=False)
class ContainerBundle:
    """Base class for a group of independently built Docker containers.

    Subclasses create containers in ``__init__`` and populate their service
    definitions in ``configure``. The Docker compiler calls ``configure`` and
    ``install`` to generate Compose services and network definitions.
    """

    emulator: InitVar[Optional[Emulator]] = None
    suffix: InitVar[str] = ""
    _emulator: Optional[Emulator] = field(default=None, init=False, repr=False)
    _suffix: str = field(default="", init=False)
    _containers: Dict[str, PreparedContainer] = field(default_factory=dict, init=False)
    _default_network: Optional[Dict[str, Any]] = field(default=None, init=False)
    _ports: List[int] = field(default_factory=list, init=False)
    _internal_hostname_ip_mappings: Dict[str, str] = field(default_factory=dict, init=False)
    _external_hostname_ip_mappings: Dict[str, str] = field(default_factory=dict, init=False)
    _required_port_number: int = field(default=0, init=False)

    def __post_init__(self, emulator: Optional[Emulator], suffix: str) -> None:
        """Store the emulator reference and hostname/build-directory suffix."""
        self._emulator = emulator
        self._suffix = suffix

    def _createContainer(self, local_name: str, suffix: str) -> PreparedContainer:
        """Create and register a prepared container.

        Args:
            local_name: Logical service name used in Compose.
            suffix: Suffix appended to the generated hostname.

        Returns:
            The newly registered :class:`PreparedContainer`.
        """
        container = PreparedContainer(name=local_name, suffix=suffix)
        self._containers.update({local_name: container})

        return container

    def getContainer(self, local_name: str) -> PreparedContainer:
        """Return a registered container by its logical service name."""
        return self._containers[local_name]

    def getContainers(self) -> Dict[str, PreparedContainer]:
        """Return a shallow copy of all registered containers."""
        return self._containers.copy()

    def getEmulator(self) -> Optional[Emulator]:
        """Return the emulator associated with this bundle, if any."""
        return self._emulator

    def getSuffix(self) -> str:
        """Return the suffix used for generated container hostnames."""
        return self._suffix

    def setDefaultNetwork(
        self,
        name: str,
        prefix: str,
        ip_addresses: List[str],
        default_router: str,
        type: str = "bridge",
    ):
        """Configure the default Docker network and static container addresses.

        Args:
            name: Docker Compose network name.
            prefix: IPv4 subnet in CIDR notation, such as ``172.20.0.0/24``.
            ip_addresses: Static IPv4 addresses assigned in container order.
            default_router: IPv4 gateway address inside ``prefix``.
            type: Docker network driver, normally ``"bridge"``.

        Returns:
            This bundle, allowing fluent configuration.

        Raises:
            ValueError: If the subnet, gateway, or container addresses are
                invalid or inconsistent.
        """
        subnet = IPv4Network(prefix, strict=True)
        gateway = IPv4Address(default_router)

        if not ip_addresses:
            raise ValueError('The "ip_addresses" field cannot be left blank.')

        if len(ip_addresses) < len(self._containers):
            raise ValueError(
                f"The number of IP addresses ({len(ip_addresses)}) "
                f"cannot be less than the number of containers "
                f"({len(self._containers)})."
            )

        if gateway not in subnet:
            raise ValueError(f"default_router {default_router!r} is outside subnet {prefix!r}.")

        normalized_addresses = []
        for address in ip_addresses:
            ip = IPv4Address(address)

            if ip not in subnet:
                raise ValueError(f"IP address {address!r} is outside subnet {prefix!r}.")

            if ip == gateway:
                raise ValueError(f"IP address {address!r} cannot be the default router.")

            normalized_addresses.append(str(ip))

        if len(set(normalized_addresses)) != len(normalized_addresses):
            raise ValueError("Container IP addresses must be unique.")

        self._default_network = {
            "name": name,
            "prefix": prefix,
            "ip_addresses": normalized_addresses,
            "default_router": str(gateway),
            "type": type,
            "network_config": {
                "driver": type,
                "ipam": {
                    "config": [
                        {
                            "subnet": prefix,
                            "gateway": str(gateway),
                        }
                    ]
                },
            },
        }

        return self

    def getDefaultNetwork(self) -> Optional[Dict[str, Any]]:
        """Return the configured default network, or ``None`` if unset."""
        return self._default_network

    def setPorts(self, ports: List[int]) -> None:
        """Set the host-port pool consumed by the bundle during configuration."""
        self._ports = ports.copy()

    def getPorts(self) -> List[int]:
        """Return a copy of the currently configured host-port pool."""
        return self._ports.copy()

    def getInternalHostnameIpMappings(self) -> Dict[str, str]:
        """Return mappings for services attached to emulated networks."""
        return self._internal_hostname_ip_mappings.copy()

    def getExternalHostnameIpMappings(self) -> Dict[str, str]:
        """Return mappings for services attached to the bundle network."""
        return self._external_hostname_ip_mappings.copy()

    def configure(self) -> None:
        """Validate bundle-wide settings before service generation.

        Subclasses should call this method before configuring their services.
        """
        if len(self._ports) < self._required_port_number:
            raise ValueError(
                f"At least {self._required_port_number} ports are required; "
                f"got {len(self._ports)}."
            )

    def install(self) -> tuple[str, str]:
        """Install containers and return Compose service and network YAML."""
        services = {}
        for name, container in self._containers.items():
            services[name] = container.install()
            ports = services[name].get("ports") or container._service_ports
            if not ports:
                continue
            print(f"service {name}: port mapping {ports}")

        if not services:
            return "", ""

        emulator_networks = set()
        if self._emulator is not None:
            for (_, object_type, _), network in self._emulator.getRegistry().getAll().items():
                if object_type != "net":
                    continue
                scope, _, _ = network.getRegistryInfo()
                network_name = network.getName()
                if network.getType() != NetworkType.Bridge:
                    network_name = f"net_{scope}_{network_name}"
                emulator_networks.add(network_name)

        networks = {
            network: (
                self._default_network["network_config"]
                if self._default_network is not None and network == self._default_network["name"]
                else {}
            )
            for service in services.values()
            for network in service.get("networks", [])
            if network not in emulator_networks
        }
        compose_services_txt = "".join(
            indent(
                safe_dump_pretty({name: service}),
                "    ",
            )
            + "\n"
            for name, service in services.items()
        )

        compose_networks_txt = (
            indent(
                safe_dump_pretty(networks),
                "    ",
            )
            if networks
            else ""
        )
        return compose_services_txt, compose_networks_txt

    def getEmuHostNetworkInfo(self):
        """Return the first usable emulated host network and default route.

        Returns:
            A dictionary containing ``network``, ``hostname``, ``ip_address``
            and ``default_route``, or ``None`` when no suitable host exists.
        """
        for (_, node_type, _), node in self._emulator.getRegistry().getAll().items():
            if node_type != "hnode":
                continue

            for interface in node.getInterfaces():
                address = interface.getAddress()
                if address is None:
                    continue

                network = interface.getNet()
                router = network.getDefaultRouter()
                scope, _, _ = network.getRegistryInfo()
                network_name = network.getName()
                if network.getType() != NetworkType.Bridge:
                    network_name = f"net_{scope}_{network_name}"

                return {
                    "network": network_name,
                    "hostname": node.getName(),
                    "ip_address": str(address),
                    "default_route": str(router) if router is not None else None,
                }


@dataclass(eq=False)
class PreparedContainer:
    """Mutable description of one container before Compose generation."""

    name: InitVar[str] = ""
    suffix: InitVar[str] = ""
    _name: str = field(default="", init=False)
    _suffix: str = field(default="", init=False)
    _internal_networks: List[Tuple[str, str, str, Optional[str]]] = field(
        default_factory=list, init=False
    )
    _external_network: List[Tuple[str, str, str]] = field(default_factory=list, init=False)
    _files: Dict[str, str] = field(default_factory=dict, init=False)
    service: Dict[str, Any] = field(default_factory=dict, init=False)
    _service_ports: List[str] = field(default_factory=list, init=False)
    _start_commands: List[str] = field(default_factory=list, init=False)
    _start_script_name: str = field(default="/start.sh", init=False)
    _default_route: str = field(default="", init=False)

    def __post_init__(self, name: str, suffix: str) -> None:
        """Initialize the logical service name and Compose service metadata."""
        self._name = name
        self._suffix = suffix
        self.service["container_name"] = name

    def getName(self) -> str:
        """Return the logical Compose service name."""
        return self._name

    def getHostname(self) -> str:
        """Return the generated hostname including the configured suffix."""
        return self._name + self._suffix

    def getInternalHostnameIpMappings(self) -> Dict[str, str]:
        """Return the first emulated-network hostname-to-IP mapping."""
        if not self._internal_networks:
            return {}

        internal_networks = self._internal_networks[0]
        return {internal_networks[1]: internal_networks[2]}

    def getExternalHostnameIpMappings(self) -> Dict[str, str]:
        """Return external-network hostname-to-IP mappings."""
        return {
            external_network[1]: external_network[2]
            for external_network in (self._external_network or [])
        }

    def setEntrypointWrapper(
        self,
        original_entrypoint: str,
        commands: List[str],
    ) -> None:
        """
        Run preparation commands before delegating to the original entrypoint.

        Args:
            original_entrypoint: Entrypoint script from the base image.
            commands: Shell commands to run before the original entrypoint.
        """
        wrapper_commands = [
            "#!/bin/sh",
            "set -eu",
            *commands,
            f'exec sh "{original_entrypoint}" "$@"',
        ]

        self._start_commands = wrapper_commands
        self._start_script_name = "/new-entrypoint.sh"

        self.service["entrypoint"] = [
            "sh",
            "/new-entrypoint.sh",
        ]

    def install(self) -> Dict[str, Any]:
        """Write build context files and return the Compose service mapping."""
        hostname = self.getHostname()
        mkdir(hostname)
        chdir(hostname)

        etchosts_content = self._files.pop("__etchosts_file", "")
        if etchosts_content:
            self.setFile("/tmp/etc-hosts", etchosts_content)
            etc_hosts_command = "cat /tmp/etc-hosts >> /etc/hosts"
            if etc_hosts_command not in self._start_commands:
                insert_index = 0
                if len(self._start_commands) > 1:
                    if self._start_commands[1] == "set -eu":
                        insert_index = 2
                    else:
                        insert_index = 1
                self._start_commands.insert(insert_index, etc_hosts_command)

        if self._default_route:
            insert_index = 0
            if len(self._start_commands) > 1:
                if self._start_commands[1] == "set -eu":
                    insert_index = 2
                else:
                    insert_index = 1
            self._start_commands[insert_index:insert_index] = self._getDefaultRouteCommands()

        if self._start_commands:
            if not self._start_commands[0].startswith("#!"):
                self.setEntrypointWrapper(
                    original_entrypoint=self._start_script_name, commands=self._start_commands
                )
            self.setFile(self._start_script_name, "\n".join(self._start_commands))

        dockerfile = self._computeDockerfile()
        if dockerfile:
            print(dockerfile, file=open("Dockerfile", "w"))

        chdir("..")
        return self.service

    def _getDefaultRouteCommands(self) -> List[str]:
        """Return shell commands for switching the container default route."""
        return [
            f'DEFAULT_ROUTE="{self._default_route}"',
            'IFACE=$(ip route get "$DEFAULT_ROUTE" | '
            "awk '{for (i=1;i<=NF;i++) if ($i==\"dev\") print $(i+1); exit}')",
            'echo "gateway=$DEFAULT_ROUTE interface=$IFACE"',
            "ip route del default 2>/dev/null || true",
            'ip route add default via "$DEFAULT_ROUTE" dev "$IFACE"',
        ]

    def joinInternalNetwork(
        self,
        network: str,
        hostname: str = "",
        ip_address: str = "",
        default_route: Optional[str] = "",
    ) -> None:
        """Attach the container to an emulated network.

        Args:
            network: Compose network name.
            hostname: Hostname or node name on that network.
            ip_address: Address assigned by the emulator.
            default_route: Optional gateway used by startup scripts.
        """
        internal_network = (network, hostname, ip_address, default_route)
        if internal_network not in self._internal_networks:
            self._internal_networks.append(internal_network)

        networks = self.service.setdefault("networks", [])
        if network not in networks:
            networks.update({network: {}})

        if default_route and not self._default_route:
            self._default_route = default_route

    def joinExternalNetwork(self, network: str, hostname: str, ip_address: str) -> None:
        """Attach the container to a bundle-managed network with a static IP."""
        external_network = (network, hostname, ip_address)
        if external_network not in self._external_network:
            self._external_network.append(external_network)

        networks = self.service.setdefault("networks", {})
        if network not in networks:
            networks.update({network: {"ipv4_address": ip_address}})

    def setContentAttribute(self, content: dict) -> None:
        """Merge Docker Compose service attributes into this container."""
        self.service.update(content)

    def setEtcHosts(self, content: str) -> None:
        """Stage content that will be appended to the container's ``/etc/hosts``."""
        self._files["__etchosts_file"] = content

    def setFile(self, filename: str, content: str) -> None:
        """Stage a file to be copied into the generated image."""
        self._files.update({filename: content})

    def _computeDockerfile(self) -> str:
        if not self._files:
            return ""

        dockerfile_lines = [
            "FROM {}".format(self.service.pop("image", "")),
            "ARG DEBIAN_FRONTEND=noninteractive",
            "RUN apt-get update && apt-get install -y --no-install-recommends iproute2 && rm -rf /var/lib/apt/lists/*",
        ]

        for filename, content in self._files.items():
            dockerfile_lines.append(self._addFile(filename, content))

        dockerfile = "\n".join(dockerfile_lines) + "\n"
        return dockerfile

    def _addFile(self, path: str, content: str) -> str:
        staged_path = md5(path.encode("utf-8")).hexdigest()
        print(content, file=open(staged_path, "w"))
        if path.endswith(".sh"):
            return "COPY {} {}\nRUN chmod +x {}".format(staged_path, path, path)
        return "COPY {} {}".format(staged_path, path)
