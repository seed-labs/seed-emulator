from enum import Enum

from . import (
    TrafficReceiver,
    TrafficGenerator,
    IperfGenerator,
    IperfReceiver,
    DITGReceiver,
    DITGGenerator,
    ScapyGenerator
)
from seedemu.core import Service, Server


class TrafficServiceType(Enum):
    """!
    @brief Traffic Service types.
    """

    IPERF_RECEIVER = "IPERF_RECEIVER"
    IPERF_GENERATOR = "IPERF_GENERATOR"
    DITG_RECEIVER = "DITG_RECEIVER"
    DITG_GENERATOR = "DITG_GENERATOR"
    SCAPY_GENERATOR = "SCAPY_GENERATOR"

class TrafficService(Service):
    def __init__(self):
        """!
        @brief TrafficService constructor.
        """
        super().__init__()
        self.servers = {}
        self.addDependency("Base", False, False)

    def install(self, vnode: str, server_type: TrafficServiceType, **kwargs) -> Server:
        """!
        @brief Install the service.
        @param vnode virtual node.
        @param server_type server type.
        @param kwargs keyword arguments."""
        
        if vnode not in self.servers:
            if server_type in [TrafficServiceType.IPERF_RECEIVER, TrafficServiceType.DITG_RECEIVER]:
                self.servers[vnode] = TrafficReceiver(vnode)
            else:
                self.servers[vnode] = TrafficGenerator(vnode)

        server = None
        if server_type == TrafficServiceType.IPERF_RECEIVER:
            server = IperfReceiver(vnode, **kwargs)
        elif server_type == TrafficServiceType.IPERF_GENERATOR:
            server = IperfGenerator(vnode, **kwargs)
        elif server_type == TrafficServiceType.DITG_RECEIVER:
            server = DITGReceiver(vnode, **kwargs)
        elif server_type == TrafficServiceType.DITG_GENERATOR:
            server = DITGGenerator(vnode, **kwargs)
        elif server_type == TrafficServiceType.SCAPY_GENERATOR:
            server = ScapyGenerator(vnode, **kwargs)
        else:
            raise ValueError(f"Unknown server type {server_type}")
        self.servers[vnode].extend(server)
        self._pending_targets[vnode] = self.servers[vnode]
        return self.servers[vnode]

    def getName(self) -> str:
        return self.__class__.__name__

    def print(self, indent: int) -> str:
        out = " " * indent
        out += "TrafficGeneratorLayer\n"

        return out
