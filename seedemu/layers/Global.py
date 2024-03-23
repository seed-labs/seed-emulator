from ipaddress import (
    IPv4Network,
    IPv6Network,
    IPv4Address,
    IPv6Address,
    ip_address,
    ip_network,
)
import re
from typing import Callable, Iterable, List, Tuple
from seedemu.core import Filter, Graphable, Layer, Node
from seedemu.core.Emulator import Emulator


def ipsInNetwork(ips: Iterable, network: str) -> bool:
    """!
    @brief Check if any of the IPs in the iterable is in the network.
    This function supports both IPv4 and IPv6 via IPv4-Mapped IPv6 Address.

    @param ips The iterable of IPs.

    @param network The network.

    @return True if any of the IPs is in the network, False otherwise.
    """
    net = ip_network(network)
    map6to4 = int(IPv6Address('::ffff:0:0'))
    if isinstance(net, IPv4Network):
        net = IPv6Network(
            # convert to IPv4-Mapped IPv6 Address for computation
            #   ::ffff:V4ADDR
            # 80 + 16 +  32
            # https://datatracker.ietf.org/doc/html/rfc4291#section-2.5.5.2
            f'{IPv6Address(map6to4 | int(net.network_address))}/{96 + net.prefixlen}'
        )
    for ip in ips:
        ip = ip_address(ip)
        if isinstance(ip, IPv4Address):
            ip = IPv6Address(map6to4 | int(ip))
        if ip in net:
            return True
    return False


class Global(Layer, Graphable):
    """!
    @brief The global layer.
    """

    applyFunctionsWithFilters: List[Tuple[Callable[[Node], None], Filter]] = []

    def __init__(self):
        """!
        @brief The constructor of the Global layer.
        Example Usage: world = Global()
        Do not use `global` as the variable name because it is a reserved keyword in Python.
        """
        super().__init__()
        self.addDependency('Base', False, False)

    def getName(self) -> str:
        return 'Global'

    def apply(self, func: Callable[[Node], None], filter: Filter = None):
        """!
        @brief Apply a function to nodes that matches the filter.
        Calling the `apply` method multiple times will apply the configurations
        in the order they are called.

        @param func The function to be applied. It takes a node as its argument.
        If you want to add a function that takes more than one argument,
        you can use a lambda function to wrap it.
        e.g. world.apply(lambda node: ldns.setNameServers(node, ["1.14.5.14"]))

        @param filter The filter to filter nodes that satisfy the requirement.
        If None, apply to all nodes.
        """
        if filter:
            assert (
                not filter.allowBound
            ), 'allowBound filter is not supported in the global layer.'
        self.applyFunctionsWithFilters.append((func, filter))

    def configure(self, emulator: Emulator):
        allNodesItems = emulator.getRegistry().getAll().items()
        for func, filter in self.applyFunctionsWithFilters:
            for (_, type, name), obj in allNodesItems:
                if type not in ['rs', 'rnode', 'hnode', 'csnode']:
                    continue
                node: Node = obj
                if filter:
                    if filter.asn and filter.asn != node.getAsn():
                        continue
                    if filter.nodeName and not re.compile(filter.nodeName).match(name):
                        continue
                    if filter.ip and filter.ip not in map(
                        lambda x: x.getAddress(), node.getInterfaces()
                    ):
                        continue
                    if filter.prefix:
                        ips = {
                            host
                            for host in map(
                                lambda x: x.getAddress(), node.getInterfaces()
                            )
                        }
                        if not ipsInNetwork(ips, filter.prefix):
                            continue
                    if filter.custom and not filter.custom(node.getName(), node):
                        continue
                func(node)

    def render(self, emulator: Emulator) -> None:
        pass
