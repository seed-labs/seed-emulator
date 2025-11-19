from .Printable import Printable
from .enums import NetworkType, NodeRole
from .Node import Node,Router
from .Network import Network
from .AddressAssignmentConstraint import AddressAssignmentConstraint
from .Emulator import Emulator
from .Configurable import Configurable
from ipaddress import IPv4Network

class InternetExchange(Printable, Configurable):
    """!
    @brief InternetExchange class.

    This class represents an internet exchange.
    """

    __id: int
    __net: Network
    __rs: Node
    __name: str

    def __init__(self, id: int, prefix: str = "auto", aac: AddressAssignmentConstraint = None, create_rs = True, rsAdress = None):
        """!
        @brief InternetExchange constructor.

        @param id ID (ASN) for the IX.
        @param prefix (optional) prefix to use as peering LAN.
        @param aac (option) AddressAssignmentConstraint to use.
        @param create_rs (optional) create route server node for the IX or not.
          ( route servers are only relevant for BGP, thus the default is True. But RSes can be disabled for SCION)
        """
        if create_rs== True and id>254 :
            assert rsAdress!=None, "rsAdress can't be None"
        self.__id = id

        assert prefix != "auto" or self.__id <= 255, "can't use auto: id > 255"
        network = IPv4Network(prefix) if prefix != "auto" else IPv4Network("10.{}.0.0/24".format(self.__id))

        self.__name = 'ix{}'.format(str(self.__id))
        self.__net = Network(self.__name, NetworkType.InternetExchange, network, aac, False)

        if create_rs:
            self.__rs = Router(self.__name, NodeRole.RouteServer, self.__id) 
            if rsAdress == None: 
                self.__rs.joinNetwork(self.__name)
            else:
                self.__rs.joinNetwork(self.__name, rsAdress)
        else:
            self.__rs = None

    def configure(self, emulator: Emulator):
        reg = emulator.getRegistry()

        reg.register('ix', 'net', self.__name, self.__net)
        if self.__rs != None:
            reg.register('ix', 'rs', self.__name, self.__rs)
            self.__rs.configure(emulator)

    def getId(self) -> int:
        """!
        @brief Get internet exchange ID.

        @returns ID.
        """
        return self.__id

    def getPeeringLan(self) -> Network:
        """!
        @brief Get the peering lan network for this IX.

        @returns Peering network.
        """
        return self.__net

    def getRouteServerNode(self) -> Node:
        """!
        @brief Get route server node.

        @returns RS node.
        """
        return self.__rs
    
    def getNetwork(self) -> Network:
        """!
        @brief Get the network of Internet Exchange.

        @returns Network.
        """

        return self.__net

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'InternetExchange {}:\n'.format(self.__id)

        indent += 4
        out += ' ' * indent
        out += 'Peering LAN Prefix: {}\n'.format(self.__net.getPrefix())

        return out