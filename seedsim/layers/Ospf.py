from seedsim.core import Node, Simulator, Layer
from seedsim.core.enums import NetworkType
from typing import Set, Dict, List, Tuple

OspfFileTemplates: Dict[str, str] = {}

OspfFileTemplates['ospf_body'] = """
    ipv4 {{
        table t_ospf;
        import all;
        export all;
    }};
    area 0 {{
{interfaces}
    }};
"""

OspfFileTemplates['ospf_interface'] = """\
        interface "{interfaceName}" {{ hello 1; dead count 2; }};
"""

OspfFileTemplates['ospf_stub_interface'] = """\
        interface "{interfaceName}" {{ stub; }};
"""

class Ospf(Layer):
    """!
    @brief Ospf (OSPF) layer.

    @todo allow mask as

    This layer enables OSPF on all router nodes. By default, this will make all
    internal network interfaces (interfaces that are connected to a network
    created by BaseLayer::createNetwork) OSPF interface. Other interfaces like
    the IX interface will also be added as stub interface.
    """

    __stubs: Set[Tuple[int, str]]
    __masked: Set[Tuple[int, str]]
    __masked_asn: Set[int]

    def __init__(self):
        """!
        @brief Ospf (OSPF) layer conscrutor.

        @param simulator simulator.
        """
        super().__init__()
        self.__stubs = set()
        self.__masked = set()
        self.__masked_asn = set()

        self.addDependency('Routing', False, False)

    def getName(self) -> str:
        return 'Ospf'

    def markAsStub(self, asn: int, netname: str):
        """!
        @brief Set all OSPF interfaces connected to a network as stub
        interfaces.

        By default, all internal networks will be active OSPF interface. This
        method can be used to override the behavior and make the interface
        stub interface (i.e., passive). For example, you can mark host-only 
        internal networks as a stub.

        @param asn ASN to operate on.
        @param netname name of the network.
        """
        self.__stubs.add((asn, netname))

    def maskNetwork(self, asn: int, netname: str):
        """!
        @brief Remove all OSPF interfaces connected to a network.

        By default, all internal networks will be active OSPF interface. Use
        this method to mask a network and disable OSPF on all connected
        interface.

        @todo handle IX LAN masking?

        @param net network.
        @throws AssertionError if network is not local.
        """
        self.__masked.add((asn, netname))

    def maskAsn(self, asn: int):
        """!
        @brief Disable OSPF for an AS.

        @param asn asn.
        """
        self.__masked_asn.add(asn)

    def isMasked(self, asn: int, netname: str) -> bool:
        """!
        @brief Test if a network is masked.

        @param net network to test.
        
        @returns if net is masked.
        """
        return (asn, netname) in self.__masked

    def render(self, simulator: Simulator):
        reg = simulator.getRegistry()

        for ((scope, type, name), obj) in reg.getAll().items():
            if type != 'rnode': continue
            router: Node = obj
            if router.getAsn() in self.__masked_asn: continue

            stubs: List[str] = ['dummy0']
            active: List[str] = []

            self._log('setting up OSPF for router as{}/{}...'.format(scope, name))
            for iface in router.getInterfaces():
                net = iface.getNet()

                if (int(scope), net.getName()) in self.__masked: continue

                if (int(scope), net.getName()) in self.__stubs or net.getType() == NetworkType.InternetExchange:
                    stubs.append(net.getName())
                    continue

                active.append(net.getName())
            
            ospf_interfaces = ''
            for name in stubs: ospf_interfaces += OspfFileTemplates['ospf_stub_interface'].format(
                interfaceName = name
            )
            for name in active: ospf_interfaces += OspfFileTemplates['ospf_interface'].format(
                interfaceName = name
            )

            if ospf_interfaces != '':
                router.addTable('t_ospf')
                router.addProtocol('ospf', 'ospf1', OspfFileTemplates['ospf_body'].format(
                    interfaces = ospf_interfaces
                ))
                router.addTablePipe('t_ospf')

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'OspfLayer:\n'

        indent += 4

        out += ' ' * indent
        out += 'Stub Networks:\n'
        indent += 4
        for (scope, netname) in self.__stubs:
            out += ' ' * indent
            out += 'as{}/{}\n'.format(scope, netname)
        indent -= 4

        out += ' ' * indent
        out += 'Masked Networks:\n'
        indent += 4
        for (scope, netname) in self.__masked:
            out += ' ' * indent
            out += 'as{}/{}\n'.format(scope, netname)
        indent -= 4

        out += ' ' * indent
        out += 'Masked AS:\n'
        indent += 4
        for asn in self.__masked_asn:
            out += ' ' * indent
            out += 'as{}\n'.format(asn)

        return out

