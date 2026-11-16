from seedemu.core import Emulator, Layer, Node
from seedemu.core.enums import NetworkType
from typing import List
from ipaddress import ip_address as parse_ip_address

class EtcHosts(Layer):
    """!
    @brief The EtcHosts layer.

    This layer setups host names for all nodes.
    """

    def __init__(self, only_hosts: bool = True):
        """!
        @brief EtcHosts Layer constructor
        @param only_hosts whether or not to create entries
               for all nodes inluding routers etc. or just hosts
        """
        self._only_hosts = only_hosts
        self._records = {}
        super().__init__()
        self.addDependency('Base', False, False)

    def addRecord(self, hostname: str, ip_address: str) -> "EtcHosts":
        """!
        @brief Add a custom /etc/hosts record before rendering.

        @param hostname a nonempty hostname without whitespace or comments.
        @param ip_address an IPv4 or IPv6 address; no node is created.
        @returns self, for chaining API calls.

        Repeated calls for the same custom hostname replace its address.
        Records are written to hosts by default, or all supported node types
        when only_hosts=False. Automatically generated records are retained.
        @raises ValueError if the hostname or IP address is invalid.
        """
        if not isinstance(hostname, str) or not hostname or any(
            char.isspace() or char == "#" for char in hostname
        ):
            raise ValueError("hostname must be nonempty and contain no whitespace or #")
        self._records[hostname] = str(parse_ip_address(ip_address))
        return self

    def getName(self) -> str:
        return "EtcHosts"

    def __getAllIpAddress(self, node: Node) -> list:
        """!
        @brief Get the IP address of the local interface for this node.
        """
        addresses = []
        for iface in node.getInterfaces():
            address = iface.getAddress()
            if iface.getNet().getType() == NetworkType.Bridge:
                pass
            if iface.getNet().getType() == NetworkType.InternetExchange:
                pass
            else:
                addresses.append(address)

        return addresses

    def _getSupportedNodeTypes(self) -> List[str]:
        if self._only_hosts:
            return ['hnode']
        else:
            return ['hnode', 'snode', 'rnode', 'rs']

    def render(self, emulator: Emulator):
        hosts_file_content = []
        nodes = []
        reg = emulator.getRegistry()
        for ((scope, type, name), node) in reg.getAll().items():
            if type in self._getSupportedNodeTypes():
                addresses = self.__getAllIpAddress(node)
                for address in addresses:
                    hosts_file_content.append(f"{address} {' '.join(node.getHostNames())}")
                nodes.append(node)

        sorted_hosts_file_content = sorted(hosts_file_content, key=lambda x: tuple(map(int, x.split()[0].split('.'))))

        sorted_hosts_file_content.extend(
            f"{address} {hostname}" for hostname, address in self._records.items()
        )

        for node in nodes:
            node.setFile("/tmp/etc-hosts", '\n'.join(sorted_hosts_file_content))
            node.insertStartCommand(0, "cat /tmp/etc-hosts >> /etc/hosts")
