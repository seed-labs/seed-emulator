from .Layer import Layer
from seedsim.core import Network, Registry
from seedsim.core.enums import NetworkType
from typing import Set

class Ospf(Layer):
    """!
    @brief Ospf (OSPF) layer.

    This layer enables OSPF on all router nodes. By default, this will make all
    internal network interfaces (interfaces that are connected to a network
    created by BaseLayer::createNetwork) OSPF interface. Other interfaces like
    the IX interface will also be added as stub interface.
    """

    __stubs: Set[Network]
    __masked: Set[Network]
    __reg = Registry()

    def __init__(self):
        """!
        @brief Ospf (OSPF) layer conscrutor.
        """

        self.__stubs = set()
        self.__masked = set()

    def getName(self) -> str:
        return 'Ospf'

    def getDependencies(self) -> List[str]:
        return ['Routing']

    def markStub(self, net: Network):
        """!
        @brief Set all OSPF interfaces connected to a network as stub
        interfaces.

        By default, all internal networks will be active OSPF interface. This
        method can be used to override the behavior and make the interface
        stub interface (i.e., passive). For example, you can mark host-only 
        internal networks as a stub.

        @param net Network.
        @throws AssertionError if network is not local
        """
        assert net.getType() != NetworkType.InternetExchange, 'cannot operator on IX network.'
        self.__stubs.add(net)

    def markStubByName(self, asn: int, netname: str):
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
        self.markStub(self.__reg.get(str(asn), 'net', netname))

    def mask(self, net: Network):
        """!
        @brief Remove all OSPF interfaces connected to a network.

        By default, all internal networks will be active OSPF interface. Use
        this method to mask a network and disable OSPF on all connected
        interface.

        @todo handle IX LAN masking?

        @param net network.
        @throws AssertionError if network is not local.
        """
        assert net.getType() != NetworkType.InternetExchange, 'cannot operator on IX network.'
        self.__masked.add(net)

    def maskByName(self, asn: int, netname: str):
        """!
        @brief Remove all OSPF interfaces connected to a network.

        By default, all internal networks will be active OSPF interface. Use
        this method to mask a network and disable OSPF on all connected
        interface.

        @param asn ASN to operate on.
        @param netname name of the network.
        """
        self.mask(self.__reg.get(str(asn), 'net', netname))

