from __future__ import annotations
from seedemu.core import Node, Emulator, Layer
from seedemu.core.enums import NetworkType
from typing import Set, Dict, List, Tuple
from ipaddress import IPv4Network


BabelFileTemplates: Dict[str, str] = {}

BabelFileTemplates['babel_body'] = """
    ipv4 {{
        table t_babel;
        import filter {{
            krt_prefsrc={src_ip};
            accept;
        }};
        export all;
    }};
{interfaces}
"""

BabelFileTemplates['dummy_direct'] = """
    ipv4 {
        table t_direct;
        import all;
    };
    interface "wireless_id";
"""

BabelFileTemplates['babel_interface'] = """\
    interface "{interfaceName}" {{ type {networkType}; }};
"""

BabelFileTemplates['babel_stub_interface'] = """\
    interface "{interfaceName}";
"""

class Babel(Layer):
    """!
    @brief Babel layer (for Babel routing protocol).

    @todo allow mask as

    This layer enables Babel on all router nodes. By default, this will make all
    internal network interfaces (interfaces that are connected to a network
    created by BaseLayer::createNetwork) Babel interface. 

    Note: this layer has only been tested inside a single AS. How it works
    with BGP, OSPF, and other protocol has not been tested yet. 
    """

    __stubs: Set[Tuple[int, str]]
    __masked: Set[Tuple[int, str]]
    __masked_asn: Set[int]
    __id_assigner: IPv4Network
    __id_pos: int

    def __init__(self, network_type: str = 'wired'):
        """!
        @brief Babel layer constructor.
        """
        super().__init__()
        self.__stubs = set()
        self.__masked = set()
        self.__masked_asn = set()
        self.__network_type = network_type
        self.__id_assigner = IPv4Network('10.0.0.0/16')
        self.__id_pos = 100


        self.addDependency('Routing', False, False)

    def getName(self) -> str:
        return 'Babel'

    def markAsStub(self, asn: int, netname: str) -> Babel:
        """!
        @brief Set all Babel interfaces connected to a network as stub
        interfaces.

        By default, all internal networks will be active Babel interface. This
        method can be used to override the behavior and make the interface
        stub interface (i.e., passive). For example, you can mark host-only 
        internal networks as a stub.

        @param asn ASN to operate on.
        @param netname name of the network.
        @returns self, for chaining API calls.

        @returns self, for chaining API calls.
        """
        self.__stubs.add((asn, netname))

        return self

    def getStubs(self) -> Set[Tuple[int, str]]:
        """!
        @brief Get set of networks that have been marked as stub.

        @returns set of tuple of asn and netname
        """
        return self.__stubs

    def maskNetwork(self, asn: int, netname: str) -> Babel:
        """!
        @brief Remove all Babel interfaces connected to a network.

        By default, all internal networks will be active Babel interface. Use
        this method to mask a network and disable Babel on all connected
        interface.

        @todo handle IX LAN masking?

        @param asn asn of the net.
        @param netname name of the net.
        
        @throws AssertionError if network is not local.

        @returns self, for chaining API calls.
        """
        self.__masked.add((asn, netname))

        return self

    def getMaskedNetworks(self) -> Set[Tuple[int, str]]:
        """!
        @brief Get set of masked network.

        @returns set of tuple of asn and netname
        """
        return self.__masked

    def maskAsn(self, asn: int) -> Babel:
        """!
        @brief Disable Babel for an AS.

        @param asn asn.

        @returns self, for chaining API calls.
        """
        self.__masked_asn.add(asn)

        return self

    def getMaskedAsns(self) -> Set[int]:
        """!
        @brief Get list of masked ASNs.

        @returns set of ASNs.
        """
        return self.__masked_asn

    def isMasked(self, asn: int, netname: str) -> bool:
        """!
        @brief Test if a network is masked.

        @param asn to test.
        @param netname net name in the given as.
        
        @returns if net is masked.
        """
        return (asn, netname) in self.__masked

    def render(self, emulator: Emulator):
        reg = emulator.getRegistry()

        for ((scope, type, name), obj) in reg.getAll().items():
            if type != 'rnode': continue
            router: Node = obj
            if router.getAsn() in self.__masked_asn: continue

            self._log("Setting up wireless id interface for AS{} Wireless Router {}...".format(scope, name))

            router_default_addr = self.__id_assigner[self.__id_pos]

            router.appendStartCommand('ip li add wireless_id type dummy')
            router.appendStartCommand('ip li set wireless_id up')
            router.appendStartCommand('ip addr add {}/32 dev wireless_id'.format(router_default_addr))
            self.__id_pos += 1


            stubs: List[str] = ['dummy0']
            active: List[str] = []

            self._log('setting up Babel for router as{}/{}...'.format(scope, name))
            for iface in router.getInterfaces():
                net = iface.getNet()

                if (int(scope), net.getName()) in self.__masked: continue

                if (int(scope), net.getName()) in self.__stubs or net.getType() != NetworkType.Local:
                    stubs.append(net.getName())
                    continue

                active.append(net.getName())
            
            babel_interfaces = ''
            for name in stubs: babel_interfaces += BabelFileTemplates['babel_stub_interface'].format(
                interfaceName = name
            )
            for name in active: babel_interfaces += BabelFileTemplates['babel_interface'].format(
                interfaceName = name, networkType = self.__network_type
            )

            if babel_interfaces != '':
                router.addTable('t_babel')
                router.addProtocol('babel', 'babel1', BabelFileTemplates['babel_body'].format(
                    src_ip = router_default_addr,
                    interfaces = babel_interfaces
                ))
                router.addTablePipe('t_babel')
                
                # Import all the routes from the local table to the babel table.
                # This is needed for RIP and Babel, but not for OSPF (OSPF will
                # generate the routes directly from the interfaces). 
                router.addTablePipe(src='t_direct', dst='t_babel', ignoreExist=False,
                                    importFilter='none', exportFilter = 'all')
                
                # Add dummy interface to its direct. 
                router.addProtocol('direct', 'dummy', BabelFileTemplates['dummy_direct'])

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'BabelLayer:\n'

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

