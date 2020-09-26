from .Layer import Layer
from seedsim.core import Network
from typing import List

class Ospf(Layer):
    """!
    @brief Ospf (OSPF) layer.

    This layer enables OSPF on all router nodes. By default, this will make all
    internal network interfaces (interfaces that are connected to a network
    created by BaseLayer::createNetwork) OSPF interface. Other interfaces like
    the IX interface will also be added as stub interface.
    """

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
        """
        pass

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
        pass

    def mask(self, asn: int, net: Network):
        """!
        @brief Remove all OSPF interfaces connected to a network.

        By default, all internal networks will be active OSPF interface, and all
        IX interface will be stub (i.e., passive) OSPF interface. Use this
        method to mask a network and disable OSPF on connected interface.

        @param asn scope of the mask. For example, if you are trying to mask an
        IX peering LAN for a specific AS.
        @param net network.
        """
        pass

    def maskByName(self, asn: int, netname: str):
        """!
        @brief Remove all OSPF interfaces connected to a network.

        By default, all internal networks will be active OSPF interface, and all
        IX interface will be stub (i.e., passive) OSPF interface. Use this
        method to mask a network and disable OSPF on connected interface.

        @param asn ASN to operate on.
        @param netname name of the network.
        """
        pass

