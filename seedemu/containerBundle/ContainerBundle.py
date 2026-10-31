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
    """!
    @brief YAML dumper that keeps nested mappings consistently indented.
    """

    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow, False)


def safe_dump_pretty(data) -> str:
    """!
    @brief Serialize data as readable YAML without sorting keys.

    @param data mapping or sequence to serialize.
    @returns the generated YAML document.
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
    """
    !
        @brief Base class for a group of independently built Docker containers.

        Subclasses create containers in ``__init__`` and configure their services
        before the Docker compiler calls ``configure`` and ``install``.
    """

    emulator: InitVar[Optional[Emulator]] = None
    suffix: InitVar[str] = ""
    _emulator: Optional[Emulator] = field(default=None, init=False, repr=False)
    _suffix: str = field(default="", init=False)
    _containers: Dict[str, PreparedContainer] = field(default_factory=dict, init=False)
    _default_external_network: Optional[Dict[str, Any]] = field(default=None, init=False)
    _default_internal_network: Optional[Dict[str, Any]] = field(default=None, init=False)
    _ports: List[int] = field(default_factory=list, init=False)
    _internal_hostname_ip_mappings: Dict[str, str] = field(default_factory=dict, init=False)
    _external_hostname_ip_mappings: Dict[str, str] = field(default_factory=dict, init=False)
    _required_port_number: int = field(default=0, init=False)
    _required_emu_network_address_number: int = field(default=0, init=False)

    def __post_init__(self, emulator: Optional[Emulator], suffix: str) -> None:
        """!
        @brief Store the emulator reference and hostname suffix.

        @param emulator emulator associated with this bundle.
        @param suffix suffix appended to generated container hostnames.
        """
        self._emulator = emulator
        self._suffix = suffix

    def _createContainer(self, local_name: str, suffix: str) -> PreparedContainer:
        """!
        @brief Create and register a prepared container.

        @param local_name logical Compose service name.
        @param suffix suffix appended to the generated hostname.
        @returns the newly registered ``PreparedContainer``.
        """
        container = PreparedContainer(name=local_name, suffix=suffix)
        self._containers.update({local_name + suffix: container})

        return container

    def getContainer(self, local_name: str) -> PreparedContainer:
        """!
        @brief Return a registered container by logical service name.

        @param local_name logical service name.
        @returns the matching ``PreparedContainer``.
        """
        return self._containers[local_name]

    def getContainers(self) -> Dict[str, PreparedContainer]:
        """!
        @brief Return a shallow copy of all registered containers.

        @returns mapping from logical service names to prepared containers.
        """
        return self._containers.copy()

    def getEmulator(self) -> Optional[Emulator]:
        """!
        @brief Return the emulator associated with this bundle.

        @returns the associated emulator, or ``None``.
        """
        return self._emulator

    def getSuffix(self) -> str:
        """!
        @brief Return the suffix used for generated hostnames.

        @returns the configured hostname and build-directory suffix.
        """
        return self._suffix

    def setDefaultInternalNetwork(self, name, ip_addresses: List, default_route: str):
        self._default_internal_network = {
            "network": name,
            "ip_addresses": ip_addresses,
            "default_route": default_route,
        }
        return self

    def getDefaultInternalNetwork(self):
        if not self._default_internal_network:
            self._default_internal_network = self.allocateEmuNetworkAddress()

        return {
            **self._default_internal_network,
            "ip_addresses": self._default_internal_network["ip_addresses"][:],
        }

    def setDefaultExternalNetwork(
        self,
        name: str,
        prefix: str,
        ip_addresses: List[str],
        default_router: str,
        type: str = "bridge",
    ):
        """!
        @brief Configure the default Docker network and static addresses.

        @param name Docker Compose network name.
        @param prefix IPv4 subnet in CIDR notation.
        @param ip_addresses static IPv4 addresses in container order.
        @param default_router IPv4 gateway inside ``prefix``.
        @param type Docker network driver, normally ``"bridge"``.
        @returns this bundle for fluent configuration.
        @raises ValueError if network or address values are invalid.
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

        self._default_external_network = {
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

    def getDefaultExternalNetwork(self) -> Optional[Dict[str, Any]]:
        """!
        @brief Return the configured default network.

        @returns the network dictionary, or ``None`` when unset.
        """
        return {
            **self._default_external_network,
            "ip_addresses": self._default_external_network["ip_addresses"][:]
        }

    def setPorts(self, ports: List[int]) -> None:
        """!
        @brief Set the host-port pool consumed during configuration.

        @param ports host ports available to the bundle.
        """
        self._ports = ports.copy()

    def getPorts(self) -> List[int]:
        """!
        @brief Return a copy of the configured host-port pool.

        @returns available host ports.
        """
        return self._ports.copy()

    def getInternalHostnameIpMappings(self) -> Dict[str, str]:
        """!
        @brief Return hostname/IP mappings for emulated networks.

        @returns a copy of internal hostname-to-address mappings.
        """
        for _, container in self._containers.items():
            self._internal_hostname_ip_mappings.update(container.getInternalHostnameIpMappings())
        return self._internal_hostname_ip_mappings.copy()

    def getExternalHostnameIpMappings(self) -> Dict[str, str]:
        """!
        @brief Return hostname/IP mappings for the bundle network.

        @returns a copy of external hostname-to-address mappings.
        """
        for _, container in self._containers.items():
            self._external_hostname_ip_mappings.update(container.getExternalHostnameIpMappings())
        return self._external_hostname_ip_mappings.copy()

    def configure(self) -> None:
        """!
        @brief Validate bundle-wide settings before service generation.

        Subclasses should call this method before configuring their services.
        @raises ValueError when fewer than the required ports are configured.
        """
        if len(self._ports) < self._required_port_number:
            raise ValueError(
                f"At least {self._required_port_number} ports are required; "
                f"got {len(self._ports)}."
            )

    def install(self) -> tuple[str, str]:
        """!
        @brief Install containers and generate Compose YAML fragments.

        @returns a tuple containing service YAML and network YAML.
        """
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
                self._default_external_network["network_config"]
                if self._default_external_network is not None
                and network == self._default_external_network["name"]
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

    def allocateEmuNetworkAddress(self):
        """!
        @brief Reserve addresses starting at host offset 10 on one host network.

        @returns a network dictionary whose ``ip_address`` is a list of
            ``_required_emu_network_address_number`` IPv4 strings, or ``None``
            when no host network has enough capacity. Select one address
            before passing the dictionary to ``joinInternalNetwork``.
        Call after rendering. Reservations are shared across bundles and
        committed only when the full requested count is available.
        """
        count = self._required_emu_network_address_number
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ValueError(
                "Required emulator network address count must be a non-negative integer."
            )
        if self._emulator is None:
            return None

        occupied = set()
        candidates = {}
        for (_, node_type, _), node in self._emulator.getRegistry().getAll().items():
            if node_type not in ("hnode", "rnode", "brdnode"):
                continue
            for interface in node.getInterfaces():
                address = interface.getAddress()
                if address is None:
                    continue
                occupied.add(IPv4Address(address))
                if node_type == "hnode":
                    network = interface.getNet()
                    candidates.setdefault(id(network), (network, node.getName()))

        # All node addresses must be known before selecting a free address.
        # Preserve host order, but inspect each candidate network only once.
        for network, hostname in candidates.values():
            router = network.getDefaultRouter()
            reserved = set(network.getAttribute("container_bundle_reserved_addresses", set()))
            gateway = IPv4Address(router) if router is not None else None
            prefix = network.getPrefix()
            first_address = int(prefix.network_address) + 10
            addresses = []
            if count:
                for ip in prefix.hosts():
                    if (
                        int(ip) < first_address
                        or ip in occupied
                        or ip in reserved
                        or ip == gateway
                        or ip == prefix.network_address
                        or ip == prefix.broadcast_address
                    ):
                        continue
                    addresses.append(str(ip))
                    if len(addresses) == count:
                        break
            if len(addresses) < count:
                continue
            reserved.update(IPv4Address(address) for address in addresses)
            network.setAttribute("container_bundle_reserved_addresses", reserved)
            scope, _, _ = network.getRegistryInfo()
            network_name = network.getName()
            if network.getType() != NetworkType.Bridge:
                network_name = f"net_{scope}_{network_name}"

            self._default_internal_network = {
                "network": network_name,
                "emu_hostname": hostname,
                "ip_addresses": addresses,
                "default_route": str(router) if router is not None else None,
            }
            return self


@dataclass(eq=False)
class PreparedContainer:
    """!
    @brief Mutable description of one container before Compose generation.
    """

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
        """!
        @brief Initialize service identity and Compose metadata.

        @param name logical Compose service name.
        @param suffix suffix appended to the generated hostname.
        """
        self._name = name
        self._suffix = suffix
        self.service["container_name"] = name + suffix

    def getName(self) -> str:
        """!
        @brief Return the logical Compose service name.

        @returns the service name.
        """
        return self._name

    def getHostname(self) -> str:
        """!
        @brief Return the generated hostname.

        @returns the logical name followed by the configured suffix.
        """
        return self._name + self._suffix

    def getInternalHostnameIpMappings(self) -> Dict[str, str]:
        """!
        @brief Return the first emulated-network hostname mapping.

        @returns a hostname-to-IP mapping, or an empty dictionary.
        """
        if not self._internal_networks:
            return {}

        internal_networks = self._internal_networks[0]
        return {internal_networks[1]: internal_networks[2]}

    def getExternalHostnameIpMappings(self) -> Dict[str, str]:
        """!
        @brief Return external-network hostname/IP mappings.

        @returns all configured external hostname-to-address mappings.
        """
        return {
            external_network[1]: external_network[2]
            for external_network in (self._external_network or [])
        }

    def setEntrypointWrapper(
        self,
        original_entrypoint: str,
        commands: List[str],
    ) -> None:
        """!
        @brief Run preparation commands before the original entrypoint.

        @param original_entrypoint entrypoint script from the base image.
        @param commands shell commands to execute before that entrypoint.
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
            self._start_script_name,
        ]

    def install(self) -> Dict[str, Any]:
        """!
        @brief Write build-context files and return the Compose service.

        @returns the generated Compose service mapping.
        """
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
        """!
        @brief Generate commands that replace the container default route.

        @returns shell commands that route traffic through ``_default_route``.
        """
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
        """!
        @brief Attach the container to an emulated network.

        @param network Compose network name.
        @param hostname hostname or node name on that network.
        @param ip_address address assigned by the emulator.
        @param default_route optional gateway used by startup scripts.
        """
        internal_network = (network, hostname, ip_address, default_route)
        if internal_network not in self._internal_networks:
            self._internal_networks.append(internal_network)

        networks = self.service.setdefault("networks", {})
        if network not in networks:
            networks.update({network: {"ipv4_address": ip_address}})

        if default_route and not self._default_route:
            self._default_route = default_route

    def joinExternalNetwork(self, network: str, hostname: str, ip_address: str) -> None:
        """!
        @brief Attach the container to a bundle network with a static IP.

        @param network Compose network name.
        @param hostname hostname represented by the static address.
        @param ip_address static IPv4 address.
        """
        external_network = (network, hostname, ip_address)
        if external_network not in self._external_network:
            self._external_network.append(external_network)

        networks = self.service.setdefault("networks", {})
        if network not in networks:
            networks.update({network: {"ipv4_address": ip_address}})

    def setContentAttribute(self, content: dict) -> None:
        """!
        @brief Merge attributes into the Compose service definition.

        @param content service attributes such as image, ports, or environment.
        """
        self.service.update(content)

    def setEtcHosts(self, content: str) -> None:
        """!
        @brief Stage content to append to the container ``/etc/hosts``.

        @param content newline-separated host entries.
        """
        self._files["__etchosts_file"] = content

    def setFile(self, filename: str, content: str) -> None:
        """!
        @brief Stage a file for the generated image.

        @param filename destination path inside the image.
        @param content file contents.
        """
        self._files.update({filename: content})

    def _computeDockerfile(self) -> str:
        if not self._files:
            return ""
        
        self.service.update({"privileged": True})
        dockerfile_lines = [
            "FROM {}".format(self.service.pop("image", "")),
            "ARG DEBIAN_FRONTEND=noninteractive",
            "RUN apt-get update && apt-get install -y --no-install-recommends iproute2 iputils-ping && rm -rf /var/lib/apt/lists/*",
        ]

        for filename, content in self._files.items():
            dockerfile_lines.append(self._addFile(filename, content))

        dockerfile = "\n".join(dockerfile_lines) + "\n"
        
        return dockerfile

    def _addFile(self, path: str, content: str) -> str:
        """!
        @brief Write a staged file and return its Docker COPY command.

        @param path destination path inside the image.
        @param content file contents.
        @returns a Dockerfile ``COPY`` instruction.
        """
        staged_path = md5(path.encode("utf-8")).hexdigest()
        print(content, file=open(staged_path, "w"))
        if path.endswith(".sh"):
            return "COPY {} {}\nRUN chmod +x {}".format(staged_path, path, path)
        return "COPY {} {}".format(staged_path, path)
