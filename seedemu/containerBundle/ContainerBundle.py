"""API skeletons for the design in docs/designs/container_bundle.md.

All methods are declarations only; container generation is not implemented.
Pseudocode in docstrings describes the intended behavior, not executable code.
"""

from __future__ import annotations
from yaml import safe_dump
from textwrap import indent
from typing import Dict, List, Optional, Tuple, Any

from seedemu.core.Emulator import Emulator
from seedemu.core.Network import Network


class ContainerBundle:
    _emulator: Emulator
    __suffix: str
    __containers: Dict[str, PreparedContainer]
    __default_network: Tuple[str, str, List[str]]
    __ports: List[int]
    __internal_hostname_ip_mappings: Dict[str, str]
    __external_hostname_ip_mappings: Dict[str, str]
    _required_port_number: int

    def __init__(self, emulator: Emulator, suffix: str) -> None:
        pass

    def _createContainer(self, local_name: str, suffix: str) -> PreparedContainer:
        container = PreparedContainer(local_name, suffix)
        self.__containers.update(local_name, container)

        return container

    def getContainer(self, local_name: str) -> PreparedContainer:
        return self.__containers[local_name]

    def getContainers(self) -> Dict[str, PreparedContainer]:
        return self.__containers.copy()

    def getEmulator(self) -> Emulator:
        return self.__emulator

    def getSuffix(self) -> str:
        return self.__suffix

    def setDefaultNetwork(self, name: str, prefix: str, ip_addresses: List[str]) -> None:
        self.__default_network = (name, prefix, ip_addresses.copy())

    def getDefaultNetwork(self) -> Tuple[str, str, List[str]]:
        return (self.__default_network[0], self.__default_network[1], self.__default_network[2].copy())

    def setPorts(self, ports: List[int]) -> None:
        self.__ports = ports.copy()

    def getPorts(self) -> List[int]:
        return self.__ports.copy()

    def getInternalHostnameIpMappings(self) -> Dict[str, str]:
        return self.__internal_hostname_ip_mappings.copy()

    def getExternalHostnameIpMappings(self) -> Dict[str, str]:
        return self.__external_hostname_ip_mappings.copy()

    def configure(self) -> None:
        assert (
            len(self.__ports) < self._required_port_number,
            f"The length of a self.__ports ({self.__ports}) be greater than or equal to {self._required_port_number}.",
        )
        
    def install(self) -> tuple[str, str, dict, dict]:
        services = {}
        files = {}
        etchosts_file = {}
        for name, container in self.__containers.items():
            services[name], files[name], etchosts_file[name] = container.install()

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
        return compose_services_txt, compose_networks_txt, files[name], etchosts_file[name]


class PreparedContainer:
    __emulator: Emulator
    __name: str
    __suffix: str
    __internal_networks: List[Tuple[str, str, str, Optional[str]]] = []
    __external_network: Optional[Tuple[str, str, str]] = []
    __files: Dict[str, str] = {}
    __etchosts_file: str

    service: Dict[str, Any] = {}

    def __init__(self, name: str, suffix: str, etchosts_file: str = "etchosts") -> None:
        self.__name = name
        self.__suffix = suffix
        self.__etchosts_file = etchosts_file

    def getName(self) -> str:
        self.__name

    def getHostname(self) -> str:
        return self.__name + self.__suffix

    def getInternalHostnameIpMappings(self) -> Dict[str, str]:
        if not self.__internal_networks:
            return {}

        internal_networks = self.__internal_networks[0]
        return {
            internal_networks[1]: internal_networks[2]
        }

    def getExternalHostnameIpMappings(self) -> Dict[str, str]:
        return {
            external_network[1]: external_network[2]
            for external_network in (self.__external_network or [])
        }

    def install(self):
        return {
            "service": self.service,
            "files": self.__files,
            "etchosts_file": self.etchosts_file,
        }

    def joinInternalNetwork(
        self,
        network: Network,
        hostname: str = '',
        ip_address: str = '',
        default_router: Optional[str] = '',
    ) -> None:
        internal_network = (network, hostname, ip_address, default_router)
        if internal_network not in self.__internal_network:
            self.__internal_network.append(internal_network)

        networks = self.service.setdefault("networks", [])
        if network not in networks:
            networks.append(network)

    def joinExternalNetwork(self, network: str, hostname: str = '', ip_address: str = '') -> None:
        """Attach to the bundle's single external network, identified by name."""
        external_network = (network, hostname, ip_address)
        if external_network not in self.__external_network:
            self.__external_network.append(external_network)

        networks = self.service.setdefault("networks", [])
        if network not in networks:
            networks.append(network)

    def setComposeContent(self, content: dict) -> None:
        self.service.update(content)

    def setDockerfile(self, content: str) -> None:
        self.__files["Dockerfile"] = content

    def setEtcHosts(self, content: str) -> None:
        self.__files["__etchosts_file"] = content

    def setFile(self, filename: str, content: str) -> str:
        self.__files.update({filename: content})
