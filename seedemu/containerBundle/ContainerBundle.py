"""Container bundles and their independently owned prepared containers."""

from __future__ import annotations
from hashlib import md5
from os import mkdir, chdir
from yaml import safe_dump
from textwrap import indent
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import InitVar, dataclass, field

from seedemu.core.Emulator import Emulator


@dataclass(eq=False)
class ContainerBundle:
    emulator: InitVar[Optional[Emulator]] = None
    suffix: InitVar[str] = ""
    _emulator: Optional[Emulator] = field(default=None, init=False, repr=False)
    _suffix: str = field(default="", init=False)
    _containers: Dict[str, PreparedContainer] = field(default_factory=dict, init=False)
    _default_network: Optional[Tuple[str, str, List[str]]] = field(default=None, init=False)
    _ports: List[int] = field(default_factory=list, init=False)
    _internal_hostname_ip_mappings: Dict[str, str] = field(default_factory=dict, init=False)
    _external_hostname_ip_mappings: Dict[str, str] = field(default_factory=dict, init=False)
    _required_port_number: int = field(default=0, init=False)

    def __post_init__(self, emulator: Optional[Emulator], suffix: str) -> None:
        self._emulator = emulator
        self._suffix = suffix

    def _createContainer(self, local_name: str, suffix: str) -> PreparedContainer:
        container = PreparedContainer(name=local_name, suffix=suffix)
        self._containers.update({local_name: container})

        return container

    def getContainer(self, local_name: str) -> PreparedContainer:
        return self._containers[local_name]

    def getContainers(self) -> Dict[str, PreparedContainer]:
        return self._containers.copy()

    def getEmulator(self) -> Optional[Emulator]:
        return self._emulator

    def getSuffix(self) -> str:
        return self._suffix

    def setDefaultNetwork(self, name: str, prefix: str = "", ip_addresses: Optional[List[str]] = None) -> None:
        self._default_network = (name, prefix, list(ip_addresses or []))

    def getDefaultNetwork(self) -> Optional[Tuple[str, str, List[str]]]:
        if self._default_network is None:
            return None
        return (
            self._default_network[0],
            self._default_network[1],
            self._default_network[2].copy(),
        )

    def setPorts(self, ports: List[int]) -> None:
        self._ports = ports.copy()

    def getPorts(self) -> List[int]:
        return self._ports.copy()

    def getInternalHostnameIpMappings(self) -> Dict[str, str]:
        return self._internal_hostname_ip_mappings.copy()

    def getExternalHostnameIpMappings(self) -> Dict[str, str]:
        return self._external_hostname_ip_mappings.copy()

    def configure(self) -> None:
        if len(self._ports) < self._required_port_number:
            raise ValueError(
                f"At least {self._required_port_number} ports are required; "
                f"got {len(self._ports)}."
            )

    def install(self) -> tuple[str, str]:
        services = {}
        for name, container in self._containers.items():
            services[name] = container.install()
            ports = services[name].get('ports') or container._service_ports
            if not ports:
                continue
            print(f"service {name}: port mapping {ports}")

        if not services:
            return "", ""

        networks = {
            network: {} for service in services.values() for network in service.get("networks", [])
        }
        compose_services_txt = "".join(
            indent(
                safe_dump({name: service}, sort_keys=False, default_flow_style=False, indent=4),
                "    ",
            )
            + "\n"
            for name, service in services.items()
        )
        compose_networks_txt = (
            indent(
                safe_dump(networks, sort_keys=False, default_flow_style=False, indent=4),
                "    ",
            )
            if networks
            else ""
        )
        return compose_services_txt, compose_networks_txt

@dataclass(eq=False)
class PreparedContainer:
    name: InitVar[str] = ""
    suffix: InitVar[str] = ""
    _name: str = field(default="", init=False)
    _suffix: str = field(default="", init=False)
    _internal_networks: List[Tuple[str, str, str, Optional[str]]] = field(default_factory=list, init=False)
    _external_network: List[Tuple[str, str, str]] = field(default_factory=list, init=False)
    _files: Dict[str, str] = field(default_factory=dict, init=False)
    service: Dict[str, Any] = field(default_factory=dict, init=False)
    _service_ports: List[str] = field(default_factory=list, init=False)

    def __post_init__(self, name: str, suffix: str) -> None:
        self._name = name
        self._suffix = suffix
        self.service['container_name'] = name

    def getName(self) -> str:
        return self._name

    def getHostname(self) -> str:
        return self._name + self._suffix

    def getInternalHostnameIpMappings(self) -> Dict[str, str]:
        if not self._internal_networks:
            return {}

        internal_networks = self._internal_networks[0]
        return {internal_networks[1]: internal_networks[2]}

    def getExternalHostnameIpMappings(self) -> Dict[str, str]:
        return {
            external_network[1]: external_network[2]
            for external_network in (self._external_network or [])
        }

    def install(self) -> Dict[str, Any]:
        hostname = self.getHostname()
        mkdir(hostname)
        chdir(hostname)

        dockerfile = self._computeDockerfile()
        if dockerfile:
            print(dockerfile, file=open("Dockerfile", "w"))

        chdir("..")
        return self.service

    def joinInternalNetwork(
        self,
        network: str,
        hostname: str = "",
        ip_address: str = "",
        default_router: Optional[str] = "",
    ) -> None:
        internal_network = (network, hostname, ip_address, default_router)
        if internal_network not in self._internal_networks:
            self._internal_networks.append(internal_network)

        networks = self.service.setdefault("networks", [])
        if network not in networks:
            networks.append(network)

    def joinExternalNetwork(self, network: str, hostname: str = "", ip_address: str = "") -> None:
        """Attach to the bundle's single external network, identified by name."""
        external_network = (network, hostname, ip_address)
        if external_network not in self._external_network:
            self._external_network.append(external_network)

        networks = self.service.setdefault("networks", [])
        if network not in networks:
            networks.append(network)

    def setContentAttribute(self, content: dict) -> None:
        self.service.update(content)

    def setDockerfile(self, content: str) -> None:
        self._files["Dockerfile"] = content

    def setEtcHosts(self, content: str) -> None:
        self._files["__etchosts_file"] = content

    def setFile(self, filename: str, content: str) -> None:
        self._files.update({filename: content})

    def _computeDockerfile(self) -> str:
        if not self._files:
            return ''
        
        dockerfile_lines = [
            "FROM {}".format(self.service.pop("image")),
            "ARG DEBIAN_FRONTEND=noninteractive",
        ]

        for filename, content in self._files.items():
            dockerfile_lines.append(self._addFile(filename, content))

        dockerfile = "\n".join(dockerfile_lines) + "\n"
        return dockerfile

    def _addFile(self, path: str, content: str) -> str:
        staged_path = md5(path.encode("utf-8")).hexdigest()
        print(content, file=open(staged_path, "w"))
        return "COPY {} {}".format(staged_path, path)
