from seedemu.core import Node
from seedemu.core.Node import Node
from . import (
    IperfReceiver,
    IperfGenerator,
    DITGGenerator,
    DITGReceiver,
    TrafficReceiver,
    TrafficGenerator,
)


class HybridTrafficReceiver(TrafficReceiver):
    def __init__(self, name: str = None):
        """!
        @brief HybridTrafficReceiver constructor.

        @param name name of the receiver.
        """
        super().__init__(name, log_file=None)
        self.iperf_receiver = IperfReceiver(
            name=name, log_file="/root/hybrid_iperf3_receiver.log"
        )
        self.ditg_receiver = DITGReceiver(
            name=name, log_file="/root/hybrid_ditg_receiver.log"
        )

    def install(self, node: Node):
        """!
        @brief Install the service.
        """
        self.iperf_receiver.install(node)
        self.ditg_receiver.install(node)


class HybridTrafficGenerator(TrafficGenerator):
    def __init__(self, name: str = None, auto_start: bool = True):
        """!
        @brief HybridTrafficGenerator constructor.

        @param name name of the generator.
        @param auto_start start the traffic generator script automatically.
        """
        super().__init__(name=name, auto_start=auto_start)
        self.iperf_generator = IperfGenerator(
            name=name,
            log_file="/root/hybrid_iperf3_generator.log",
            duration=600,
            rate=0,
            protocol="UDP",
            auto_start=False,
        )
        self.ditg_generator = DITGGenerator(
            name=name,
            log_file="/root/hybrid_ditg_generator.log",
            duration=600,
            rate=5000,
            protocol="TCP",
            auto_start=False,
        )

    def install(self, node: Node):
        """!
        @brief Install the service.
        """
        self.iperf_generator.install(node)
        self.ditg_generator.install(node)
        super().install(node)
        if self.auto_start:
            self.iperf_generator.start(node)
            self.ditg_generator.start(node)
