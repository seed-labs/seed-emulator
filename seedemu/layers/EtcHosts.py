from seedemu.core import Emulator, Layer, Node
from seedemu.core.enums import NetworkType

class EtcHosts(Layer):
    """!
    @brief The EtcHosts layer.

    This layer setups host names for all nodes.
    """

    def __init__(self):
        """!
        @brief EtcHosts Layer constructor
        """
        super().__init__()
        self.addDependency('Base', False, False)

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

    def render(self, emulator: Emulator):
        hosts_file_content = []
        nodes = []
        reg = emulator.getRegistry()
        for ((scope, type, name), node) in reg.getAll().items():
            if type in ['hnode', 'snode', 'rnode', 'rs']:
                addresses = self.__getAllIpAddress(node)
                for address in addresses:
                    hosts_file_content.append(f"{address} {' '.join(node.getHostNames())}")
                nodes.append(node)

        sorted_hosts_file_content = sorted(hosts_file_content, key=lambda x: tuple(map(int, x.split()[0].split('.'))))
        
        for node in nodes:
            node.setFile("/tmp/etc-hosts", '\n'.join(sorted_hosts_file_content))
            node.insertStartCommand(0, "cat /tmp/etc-hosts >> /etc/hosts")
