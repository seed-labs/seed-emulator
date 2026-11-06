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
    """!
    @brief Base class for a group of independently built Docker containers.

    Subclasses create containers in ``__init__``. Callers supply networks
    and host ports, then register the bundle with Docker. During compilation,
    Docker calls ``configure`` followed by ``install``; registration alone
    does not configure services. See docs/designs/container_bundle.md.
    """

    emulator: InitVar[Optional[Emulator]] = None
    suffix: InitVar[str] = ""
    _emulator: Optional[Emulator] = field(default=None, init=False, repr=False)
    _suffix: str = field(default="", init=False)
    _containers: Dict[str, PreparedContainer] = field(default_factory=dict, init=False)
    _internal_networks: list[Dict[str, str]] = field(default_factory=list, init=False)
    _external_networks: list[Dict[str, str]] = field(default_factory=list, init=False)
    _ports: List[int] = field(default_factory=list, init=False)
    _required_port_count: int = field(default=0, init=False)
    _required_internal_address_count: int = field(default=0, init=False)
    _is_configured: bool = field(default=False, init=False)
    _shared_etc_hosts_records: List[Tuple[str, str]] = field(default_factory=list, init=False)

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
        container = PreparedContainer(name=local_name, suffix=suffix, emulator=self._emulator)
        self._containers.update({local_name: container})

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

    def addInternalNetwork(
        self, asn: str, network_name: str, ip_addresses: List, default_route: str = ""
    ):
        """!
        @brief Validate and store an explicit AS network address pool.

        Requires the Base layer and the named AS/network. Router and address
        checks use configured interfaces, normally available after render().
        A supplied gateway must belong to a router on this network. If empty,
        the gateway is looked up in the registry and may remain empty if no
        matching entry is found. Only the first required number of addresses
        are checked for availability; no addresses are allocated or reserved.
        Subclasses decide which containers consume this pool.

        @param asn autonomous system containing the network.
        @param network_name Base-layer network name, for example net0.
        @param ip_addresses caller-selected address pool.
        @param default_route gateway address, or empty for registry lookup.
        @returns this bundle for chaining.
        @raises ValueError when the address pool is smaller than required.
        @raises AssertionError for an invalid supplied gateway or an unavailable
            address among the checked entries.
        """
        network_obj = self._emulator.getLayer("Base").getAutonomousSystem(int(asn)).getNetwork(network_name)
        if default_route:
            assert network_obj.isValidRouter(default_route), "The 'default_route' is invalid"
        else:
            for (scope, object_type, name), obj in self._emulator.getRegistry().getAll().items():
                if object_type == "net" and scope == asn and name == network_name:
                    default_route = obj.getDefaultRouter()
                    break

        if len(ip_addresses) < self._required_internal_address_count:
            raise ValueError(
                f"At least {self._required_internal_address_count} ip are required; "
                f"got {len(ip_addresses)}."
            )
        assert all([network_obj.isIpAddressAvailable(ip_address) for ip_address in ip_addresses[:self._required_internal_address_count]]), "The 'ip_address' must be fully available."

        self._internal_networks.append(
            {
                "asn": asn,
                "network_name": network_name,
                "full_network_name": network_obj.getFullName(),
                "ip_addresses": ip_addresses,
                "default_route": default_route,
            }
        )
        return self

    def getInternalNetworks(self) -> List[Dict[str, Any]]:
        """!
        @brief Return internal network entries with copied address lists.
        """
        return [
            {**network, "ip_addresses": network["ip_addresses"][:]}
            for network in self._internal_networks
        ]

    def addExternalNetwork(
        self,
        network_name: str,
        prefix: str,
        ip_addresses: List[str],
        default_route: str,
        driver: str = "bridge",
    ):
        """!
        @brief Append a Compose network with validated static IPv4 addresses.

        Supply at least one address per prepared container, including containers
        using host networking. Addresses must be unique, within the subnet, and
        different from the gateway. This stores a pool; it does not attach
        containers or reserve addresses on the Docker host.

        @param network_name generated Compose network key.
        @param prefix IPv4 subnet in canonical CIDR notation.
        @param ip_addresses static address pool used by the subclass.
        @param default_route gateway address within the subnet.
        @param driver Compose network driver, bridge by default.
        @returns this bundle for chaining.
        @raises ValueError for an invalid subnet or IPv4 address.
        @raises AssertionError for an insufficient pool, addresses outside the
            subnet, duplicate addresses, or addresses equal to the gateway.
        """
        subnet = IPv4Network(prefix, strict=True)
        gateway = IPv4Address(default_route)
        assert ip_addresses, 'The "ip_addresses" field cannot be blank.'
        assert len(ip_addresses) >= len(self._containers), (
            f"The number of IP addresses ({len(ip_addresses)}) "
            f"cannot be less than the number of containers "
            f"({len(self._containers)})."
        )
        assert gateway in subnet, f"default_route {default_route!r} is outside subnet {prefix!r}."

        normalized_addresses = []
        for address in ip_addresses:
            ip = IPv4Address(address)
            assert ip in subnet, f"IP address {address!r} is outside subnet {prefix!r}."
            assert ip != gateway, f"IP address {address!r} cannot be the default router."
            normalized_addresses.append(str(ip))

        assert len(set(normalized_addresses)) == len(
            normalized_addresses
        ), "Container IP addresses must be unique."

        self._external_networks.append(
            {
                "network_name": network_name,
                "prefix": prefix,
                "ip_addresses": normalized_addresses,
                "default_route": str(gateway),
                "type": driver,
                "network_config": {
                    "driver": driver,
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
        )

        return self

    def getExternalNetworks(self) -> List[Dict[str, Any]]:
        """!
        @brief Return all explicitly configured external networks.

        @returns network entries with copied address lists; nested network_config
            dictionaries remain shared. An unset pool returns an empty list.
        """
        return [
            {**network, "ip_addresses": network["ip_addresses"][:]}
            for network in self._external_networks
        ]

    def setPorts(self, ports: List[int]) -> None:
        """!
        @brief Set the host-port pool consumed during configuration.

        @param ports host ports available to the bundle.
        """
        self._ports = ports[:]

    def getPorts(self) -> List[int]:
        """!
        @brief Return a copy of the configured host-port pool.

        @returns available host ports.
        """
        return self._ports[:]

    def printEtcHostsRecords(self) -> None:
        """!
        @brief Print deduplicated shared records as ``IP<TAB>hostname``.

        Container-specific records are not included. Requires _is_configured
        to be true. The base configure() sets this flag after validating ports,
        before subclass configuration finishes; call after successful compilation.

        @raises AssertionError when _is_configured is false.
        """
        assert self._is_configured, "Call configure() successfully before printEtcHostsRecords()."
        for domain_name, ip in dict.fromkeys(self._shared_etc_hosts_records):
            print(f"{ip}\t{domain_name}")

    def addEtcHostsRecord(self, name: str, ip: str) -> None:
        """!
        @brief Add a shared hostname/IP pair for every container in this bundle.

        Bundle installation appends these records to each container's record
        list. Container installation removes exact duplicate pairs using a set,
        so generated line order is unspecified. Different IPs for the same name
        remain separate entries. Records do not apply to emulator nodes.

        @param name hostname or alias to resolve.
        @param ip address associated with the name.
        """
        self._shared_etc_hosts_records.append((name, ip))

    def configure(self) -> None:
        """!
        @brief Validate bundle-wide settings before service generation.

        Subclasses should call this method before configuring their services.
        After validating the port count, this sets _is_configured to true.
        The flag does not indicate that the remaining subclass setup succeeded.
        @raises AssertionError when fewer than the required ports are configured.
        """
        assert len(self._ports) >= self._required_port_count, (
            f"At least {self._required_port_count} ports are required; "
            f"got {len(self._ports)}."
        )

        self._is_configured = True

    def install(self) -> tuple[str, str]:
        """!
        @brief Install containers and generate Compose YAML fragments.

        Shared records are appended to each container's existing record list.
        The shared list is unchanged, but each container's record list is mutated.
        @returns a tuple containing service YAML and network YAML.
        """
        services = {}
        for container in self._containers.values():
            name = container.getHostname()
            for record in self._shared_etc_hosts_records:
                container.addEtcHostsRecord(*record)
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
            network: next(
                (
                    external_network["network_config"]
                    for external_network in self._external_networks
                    if external_network["network_name"] == network
                ),
                {},
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


@dataclass(eq=False)
class PreparedContainer:
    """!
    @brief Mutable description of one container before Compose generation.
    """

    name: InitVar[str] = ""
    suffix: InitVar[str] = ""
    emulator: InitVar[Optional[Emulator]] = None
    _name: str = field(default="", init=False)
    _suffix: str = field(default="", init=False)
    _emulator: Optional[Emulator] = field(default=None, init=False, repr=False)
    _internal_networks: List[Dict[str, str]] = field(default_factory=list, init=False)
    _external_networks: List[Dict[str, str]] = field(default_factory=list, init=False)
    _files: Dict[str, str] = field(default_factory=dict, init=False)
    _service: Dict[str, Any] = field(default_factory=dict, init=False)
    _service_ports: List[str] = field(default_factory=list, init=False)
    _start_commands: List[str] = field(default_factory=list, init=False)
    _start_script_name: str = field(default="/start.sh", init=False)
    _default_route: str = field(default="", init=False)
    _etc_hosts_records: List[Tuple[str, str]] = field(default_factory=list, init=False)

    def __post_init__(self, name: str, suffix: str, emulator: Optional[Emulator]) -> None:
        """!
        @brief Initialize service identity and Compose metadata.

        @param name logical Compose service name.
        @param suffix suffix appended to the generated hostname.
        @param emulator owner used to resolve Base-layer networks and interfaces.
        """
        self._name = name
        self._suffix = suffix
        self._service["container_name"] = name
        self._emulator = emulator

    def getName(self) -> str:
        """!
        @brief Return the logical Compose service name.

        @returns the service name.
        """
        return self._name

    def getHostname(self) -> str:
        """!
        @brief Return the logical name with the configured suffix.

        This identifies the Compose service, container name, and build directory.
        It does not set Docker's hostname attribute or the container's OS hostname.
        @returns the logical name followed by the configured suffix.
        """
        return self._name + self._suffix

    def setStartScriptName(self, name: str):
        self._start_script_name = name

    def setEntrypointWrapper(
        self,
        original_entrypoint: str,
        commands: List[str],
    ) -> None:
        """!
        @brief Run preparation commands before the original entrypoint.

        @param original_entrypoint shell-readable file delegated to with sh.
        @param commands shell commands to execute before that entrypoint.

        Delegation happens only after all supplied commands return. A command
        such as exec sleep infinity replaces the wrapper instead of delegating.
        """
        wrapper_commands = [
            "#!/bin/sh",
            "set -eu",
            *commands,
            f'exec sh "{original_entrypoint}" "$@"',
        ]

        self._start_commands = wrapper_commands
        self._start_script_name = "/new-entrypoint.sh"

        self._service["entrypoint"] = [
            "sh",
            self._start_script_name,
        ]

    def install(self) -> Dict[str, Any]:
        """!
        @brief Write build-context files and return the Compose service.

        Serializes the container's current records, including any shared entries
        already appended by ContainerBundle.install(). Exact duplicate pairs
        are removed using a set; generated hosts-file order is unspecified.
        A startup command appends /tmp/etc-hosts to /etc/hosts at container start.
        @returns the generated Compose service mapping.
        """
        hostname = self.getHostname()
        mkdir(hostname)
        chdir(hostname)
        if self._start_script_name:
            if self._etc_hosts_records:
                etchosts_content = "\n".join(
                    f"{ip}\t{hostname}"
                    for hostname, ip in set(self._etc_hosts_records)
                )
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
                if not self._start_commands[0].startswith("#!") :
                    self.setEntrypointWrapper(
                        original_entrypoint=self._start_script_name, commands=self._start_commands
                    )
                self.setFile(self._start_script_name, "\n".join(self._start_commands))

        dockerfile = self._generateDockerfile()
        if dockerfile:
            print(dockerfile, file=open("Dockerfile", "w"))
            self.updateServiceConfig({"build": f"./{self.getHostname()}"})

        chdir("..")

        return {
            **self._service,
            "container_name": self.getHostname(),
        }

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
        asn,
        network_name: str,
        ip_address: str,
        hostname: str,
        default_route: str,
    ) -> None:
        """!
        @brief Attach the container to an emulated network.

        @param asn autonomous system containing the network.
        @param network_name Base-layer network name (for example, net0).
        @param hostname attachment metadata, normally logical name + suffix.
        @param ip_address caller-selected address checked against this network.
        @param default_route gateway address, or empty for registry lookup.

        Validates a supplied gateway and the address using configured network
        interfaces; it does not reserve the address. This method only records
        the attachment and the first nonempty gateway. It does not add hosts
        records or register/render an EtcHosts layer.
        """
        network_obj = self._emulator.getLayer("Base").getAutonomousSystem(int(asn)).getNetwork(network_name)
        full_network_name = network_obj.getFullName()
        if default_route:
            assert network_obj.isValidRouter(default_route), "The 'default_route' is invalid."
        else:
            for (scope, object_type, name), obj in self._emulator.getRegistry().getAll().items():
                if object_type == "net" and scope == asn and name == network_name:
                    default_route = obj.getDefaultRouter()
                    break
        assert network_obj.isIpAddressAvailable(ip_address), "The 'ip_address' is invalid."

        internal_network = {
            "asn": asn,
            "network_name": network_name,
            "hostname": hostname,
            "ip_address": ip_address,
            "default_route": default_route,
            "full_network_name": full_network_name,
        }
        self._internal_networks.append(internal_network)
        # Preserve existing service network attachments and an existing address.
        # setdefault:
        # If the key exists, return its current value without changing it.
        # Otherwise, insert and return the supplied default value ({} here).
        # If no default argument is supplied, the default value is None.
        networks = self._service.setdefault("networks", {})
        if full_network_name not in networks:
            networks.update({full_network_name: {"ipv4_address": ip_address}})

        # Keep the first nonempty gateway supplied by an internal attachment.
        if not self._default_route:
            self._default_route = default_route

    def joinExternalNetwork(self, network_name: str, hostname: str, ip_address: str) -> None:
        """!
        @brief Attach the container to a bundle network with a static IP.

        @param network_name Compose network key.
        @param hostname attachment metadata, normally logical name + suffix.
        @param ip_address static IPv4 address; only IPv4 syntax is checked here.

        Records the attachment and preserves an existing Compose address for
        this network. This method does not create hosts aliases; register those
        separately through bundle.addEtcHostsRecord() or addEtcHostsRecord().
        """
        address = IPv4Address(ip_address)
        external_network = {
            "network_name": network_name,
            "hostname": hostname,
            "ip_address": str(address),
        }
        self._external_networks.append(external_network)

        networks = self._service.setdefault("networks", {})
        if network_name not in networks:
            networks.update({network_name: {"ipv4_address": ip_address}})

    def updateServiceConfig(self, content: dict) -> None:
        """!
        @brief Shallowly merge top-level Compose service attributes.

        @param content service attributes such as image, ports, or environment.
            Existing values for supplied keys are replaced, not recursively merged.
        """
        self._service.update(content)

    def addEtcHostsRecord(self, name: str, ip: str) -> None:
        """!
        @brief Add a hostname/IP pair for this container only.

        Bundle installation appends shared records to this list before calling
        install(). Adding a local record does not affect sibling containers or
        emulator nodes. Container installation removes exact duplicate pairs.

        @param name hostname or alias to resolve.
        @param ip address associated with the name.
        """
        self._etc_hosts_records.append((name, ip))

    def setEtcHosts(self, content: str) -> None:
        """!
        @brief Store legacy host-file content under the __etchosts_file key.

        @param content newline-separated host entries.

        The current installer treats this key as an ordinary staged file and
        does not append its contents to /etc/hosts. Use addEtcHostsRecord().
        """
        self._files["__etchosts_file"] = content

    def setFile(self, filename: str, content: str) -> None:
        """!
        @brief Stage a file for the generated image.

        @param filename destination path inside the image.
        @param content file contents.
        """
        self._files.update({filename: content})

    def _generateDockerfile(self) -> str:
        """!
        @brief Stage configured files and generate derived-image instructions.

        Enables privileged mode and consumes the service's image attribute for
        FROM. The base image must support apt-based dependency installation.
        @returns Dockerfile text, or an empty string when no files are staged.
        """
        if not self._files:
            return ""

        self._service.update({"privileged": True})
        image = self._service.pop("image", "")
        assert image, f"Container {self.getHostname()!r} has no base image."
        dockerfile_lines = [
            f"FROM {image}",
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
