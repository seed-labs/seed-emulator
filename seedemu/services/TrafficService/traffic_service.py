from enum import Enum
from . import IperfGenerator, IperfReceiver, DITGReceiver, DITGGenerator, ScapyGenerator, HybridTrafficReceiver, HybridTrafficGenerator 
from seedemu.core import Service

class TrafficServiceType(Enum):
    """!
    @brief Traffic Service types.
    """
    IPERF_RECEIVER = "IPERF_RECEIVER"
    IPERF_GENERATOR = "IPERF_GENERATOR"
    DITG_RECEIVER = "DITG_RECEIVER"
    DITG_GENERATOR = "DITG_GENERATOR"
    SCAPY_GENERATOR = "SCAPY_GENERATOR"
    HYBRID_RECEIVER = "HYBRID_RECEIVER"
    HYBRID_GENERATOR = "HYBRID_GENERATOR"

class TrafficService(Service):
    def __init__(self):
        super().__init__()
        self.servers = {}
        self.addDependency('Base', False, False)

    def install(self, vnode, server_type):
        server = None
        if server_type == TrafficServiceType.IPERF_RECEIVER:
            server = IperfReceiver(vnode)
        elif server_type == TrafficServiceType.IPERF_GENERATOR:
            server = IperfGenerator(vnode)
        elif server_type == TrafficServiceType.DITG_RECEIVER:
            server = DITGReceiver(vnode)
        elif server_type == TrafficServiceType.DITG_GENERATOR:
            server = DITGGenerator(vnode)
        elif server_type == TrafficServiceType.SCAPY_RECEIVER:
            server = ScapyGenerator(vnode)
        elif server_type == TrafficServiceType.HYBRID_RECEIVER:
            server = HybridTrafficReceiver(vnode)
        elif server_type == TrafficServiceType.HYBRID_GENERATOR:
            server = HybridTrafficGenerator(vnode)

        if server:
            self._pending_targets[vnode] = server
        return server

    def getName(self) -> str:
        return self.__class__.__name__
  
    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'TrafficGeneratorLayer\n'

        return out
