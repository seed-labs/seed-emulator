from .Printable import Printable
from .Network import Network
from .enums import NodeRole, NetworkType, InterfaceType
from .Registry import Registry, ScopedRegistry, Registrable
from ipaddress import IPv4Address
from typing import List

class File(Printable):
    """!
    @brief File class.

    This class represents a file on a node.
    """

    __content: str
    __path: str

    def __init__(self, path: str, content: str):
        """!
        @brief File constructor.

        Put a file onto a node.

        @param path path of the file.
        @param content content of the file.
        """

    def setPath(self, path: str):
        """!
        @brief Update file path.

        @param path new path.
        """
        self.__path = path

    def setContent(self, content: str):
        """!
        @brief Update file content.

        @param path new path.
        """
        self.__content = content

    def get(self) -> (str, str):
        """!
        @brief Get file path and content.

        @returns a tuple where the first element is path and second element is 
        content
        """
        return (self.__path, self.__content)

class Interface(Printable):
    """!
    @brief Interface class.

    This class represents a network interface card.
    """

    __network: Network
    __type: InterfaceType
    __address: IPv4Address

    def __init__(self, net: Network, type: InterfaceType = None):
        """!
        @brief Interface constructor.

        @param net network to connect to.
        @param type optionally, override interface type. For example, one may
        choose to override the router's interface type in a host network, so the
        IP assignment assigns the correct address for the router.
        """
        self.__address = None
        self.__network = net
        self.__type = type
        if self.__type == None:
            if net.getType() == NetworkType.Host: self.__type = InterfaceType.Host
            if net.getType() == NetworkType.InternetExchange: self.__type = InterfaceType.InternetExchange
            if net.getType() == NetworkType.Local: self.__type = InterfaceType.Local

    def getType(self) -> InterfaceType:
        """!
        @brief Get type of this interface.

        This will be used in some automation
        cases. For example, AddressAssignmentConstraint will use the node type
        to decide how to assign IP addresses to nodes.

        @returns interface type
        """
        return self.__type
    
    def getNet(self) -> Network:
        """!
        @brief Get the network that this interface attached to.

        @returns network.
        """
        return self.__network

    def setAddress(self, address: IPv4Address):
        """!
        @brief Set IPv4 address of this interface.

        @param address address.
        """
        self.__address = address

    def getAddress(self):
        """!
        @brief Get IPv4 address of this interface.

        @returns address.
        """
        return self.__address

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'Interface:\n'

        indent += 4
        out += ' ' * indent
        out += 'Connected to: {}\n'.format(self.__network.getName())
        out += ' ' * indent
        out += 'Address: {}\n'.format(self.__address)

        return out

class Node(Printable, Registrable):
    """!
    @brief Node base class.

    This class represents a generic node.
    """

    __name: str
    __asn: int
    __role: NodeRole
    __reg: ScopedRegistry
    __greg = Registry()
    __interfaces: List[Interface]

    def __init__(self, name: str, role: NodeRole, asn: int, scope: str = None):
        """!
        @brief Node constructor.

        @name name name of this node.
        @param role role of this node.
        @param asn network that this node belongs to.
        @param scope scope of the node, if not asn.
        """
        self.__interfaces = []
        self.__asn = asn
        self.__reg = ScopedRegistry(scope if scope != None else str(asn))
        self.__role = role
        self.__name = name

    def joinNetwork(self, net: Network, address: str = "auto") -> Interface:
        """!
        @brief Connect the node to a network.
        @param net network to connect.
        @param address (optional) override address assigment.

        @throws AssertionError if network does not exist.
        """
        _addr: IPv4Address = None
        _itype: InterfaceType = None
        if self.__role == NodeRole.Host: _itype = InterfaceType.Host
        if self.__role == NodeRole.Router:
            _ntype = net.getType()
            if _ntype == NetworkType.InternetExchange:
                _itype = InterfaceType.InternetExchange

            if _ntype == NetworkType.Host or _ntype == NetworkType.Local:
                _itype = InterfaceType.Local

        if self.__role == NodeRole.RouteServer:
            _itype = InterfaceType.InternetExchange
        
        if address == "auto": _addr = net.assign(_itype, self.__asn)
        else: _addr = IPv4Address(address)

        _iface = Interface(net, _itype)
        _iface.setAddress(_addr)

        self.__interfaces.append(_iface)

        return _iface

    def joinNetworkByName(self, netname: str, address: str = "auto") -> Interface:
        """!
        @brief Connect the node to a network.
        @param netname name of the network.
        @param address (optional) override address assigment.

        @throws AssertionError if network does not exist.
        """
        if self.__reg.has("net", netname):
            return self.joinNetwork(self.__reg.get("net", netname), address)

        if self.__greg.has("ix", "net", netname):
            return self.joinNetwork(self.__greg.get("ix", "net", netname), address)
        
        assert False, 'No such network: {}'.format(netname)

    def getRole(self) -> NodeRole:
        """!
        @brief Get role of current node.

        Get role type of current node. 

        @returns role.
        """
        return this.__role

    def getFile(self, path: str) -> File:
        """!
        @brief Get a file object, and create if not exist.

        @param path file path.
        """
        pass

    def setFile(self, path: str, content: str):
        """!
        @brief Set content of the file.

        @param path path of the file. Will be created if not exist, and will be
        override if already exist.
        @param content file content.
        """
        pass

    def appendFile(self, path: str, content: str):
        """!
        @brief Append content to a file.

        @param path path of the file. Will be created if not exist.
        @param content content to append.
        """
        pass
        
    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'Node {}:\n'.format(self.__name)

        indent += 4
        out += ' ' * indent
        out += 'Role: {}\n'.format(self.__role)
        out += ' ' * indent
        out += 'Interfaces:\n'
        for interface in self.__interfaces:
            out += interface.print(indent + 4)


        return out
