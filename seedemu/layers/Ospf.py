from __future__ import annotations
from seedemu.core import Node, Emulator, Layer
from seedemu.core.enums import NetworkType, NodeRole
from typing import Set, Dict, List, Tuple, Optional
from .Base import Base
from ._bgp_metadata import (
    DEFAULT_OSPF_DEAD,
    DEFAULT_OSPF_HELLO,
    DEFAULT_OSPF_TICK,
    classify_ospf_interfaces,
    normalize_ospf_timers,
    set_ospf_interface_intents,
)

OspfFileTemplates: Dict[str, str] = {}

OSPF_MODE_LEGACY = "legacy"
OSPF_MODE_ROUTER_TRANSIT_ONLY = "router-transit-only"
OSPF_MODES = {OSPF_MODE_LEGACY, OSPF_MODE_ROUTER_TRANSIT_ONLY}

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
    __tick: int
    __hello: int
    __dead: int

    def __init__(self):
        """!
        @brief Ospf (OSPF) layer constructor.
        """
        super().__init__()
        self.__stubs = set()
        self.__masked = set()
        self.__masked_asn = set()
        self.__tick = DEFAULT_OSPF_TICK
        self.__hello = DEFAULT_OSPF_HELLO
        self.__dead = DEFAULT_OSPF_DEAD

        self.addDependency('Routing', False, False)

    def getName(self) -> str:
        return 'Ospf'

    def setTimers(
        self,
        tick: Optional[int] = None,
        hello: Optional[int] = None,
        dead: Optional[int] = None,
    ) -> Ospf:
        """!
        @brief Set default OSPF timers for generated OSPF sessions.

        @param tick BIRD OSPF scheduler tick interval, in seconds.
        @param hello OSPF hello interval, in seconds.
        @param dead OSPF dead interval, in seconds.

        @returns self, for chaining API calls.
        """
        timers = normalize_ospf_timers(
            self.__tick if tick is None else tick,
            self.__hello if hello is None else hello,
            self.__dead if dead is None else dead,
        )
        self.__tick = timers["tick"]
        self.__hello = timers["hello"]
        self.__dead = timers["dead"]
        return self

    def getTimers(self) -> Dict[str, int]:
        """!
        @brief Get OSPF timer defaults used by this layer.

        @returns dict with tick, hello, and dead timer values.
        """
        return {
            "tick": self.__tick,
            "hello": self.__hello,
            "dead": self.__dead,
        }

    def markAsStub(self, asn: int, netname: str) -> Ospf:
        """!
        @brief Set all OSPF interfaces connected to a network as stub
        interfaces.

        By default, all internal networks will be active OSPF interface. This
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

    def maskNetwork(self, asn: int, netname: str) -> Ospf:
        """!
        @brief Remove all OSPF interfaces connected to a network.

        By default, all internal networks will be active OSPF interface. Use
        this method to mask a network and disable OSPF on all connected
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

    def maskAsn(self, asn: int) -> Ospf:
        """!
        @brief Disable OSPF for an AS.

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

    def __is_router_transit_network(self, node: Node, netname: str) -> bool:
        for iface in node.getInterfaces():
            net = iface.getNet()
            if str(net.getName()) != str(netname):
                continue
            if net.getType() != NetworkType.Local:
                return False
            router_count = 0
            for candidate in net.getAssociations():
                role = candidate.getRole()
                if role in {NodeRole.Router, NodeRole.BorderRouter, NodeRole.OpenVpnRouter}:
                    router_count += 1
            return router_count >= 2
        return False

    def __classify_router_transit_interfaces(
        self,
        router: Node,
        stubs: List[str],
        masked: List[str]
    ) -> Tuple[List[str], List[str]]:
        stub_names = {str(name) for name in stubs}
        masked_names = {str(name) for name in masked}
        active: List[str] = []
        passive: List[str] = ["dummy0"]
        for iface in router.getInterfaces():
            net = iface.getNet()
            name = str(net.getName())
            if name in masked_names:
                continue
            if name in stub_names:
                passive.append(name)
                continue
            if self.__is_router_transit_network(router, name):
                active.append(name)
            else:
                passive.append(name)
        return active, passive

    def configure(self, emulator: Emulator):
        reg = emulator.getRegistry()
        base: Base = reg.get('seedemu', 'layer', 'Base')

        for ((scope, type, name), obj) in reg.getAll().items():
            if type != 'rnode': continue
            router: Node = obj
            if router.getAsn() in self.__masked_asn: continue

            self._log('setting up OSPF for router as{}/{}...'.format(scope, name))
            asobj = base.getAutonomousSystem(int(scope))
            stub_networks = [net for (asn, net) in self.__stubs if asn == int(scope)]
            masked_networks = [net for (asn, net) in self.__masked if asn == int(scope)]
            if asobj.getOspfMode() == OSPF_MODE_ROUTER_TRANSIT_ONLY:
                active, stubs = self.__classify_router_transit_interfaces(
                    router,
                    stubs=stub_networks,
                    masked=masked_networks,
                )
            else:
                active, stubs = classify_ospf_interfaces(
                    router,
                    stubs=stub_networks,
                    masked=masked_networks,
                )
            set_ospf_interface_intents(
                router,
                active,
                stubs,
                tick=self.__tick,
                hello=self.__hello,
                dead=self.__dead,
            )

    def render(self, emulator: Emulator):
        pass

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
