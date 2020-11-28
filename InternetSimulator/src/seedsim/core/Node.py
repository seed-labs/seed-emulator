from .Printable import Printable
from .Network import Network
from .enums import NodeRole, NetworkType
from .Registry import Registry, ScopedRegistry, Registrable
from ipaddress import IPv4Address
from typing import List, Dict, Set, Tuple

DEFAULT_SOFTWARES: List[str] = ['curl', 'nano', 'vim-nox', 'mtr-tiny', 'iproute2', 'iputils-ping', 'tcpdump', 'termshark', 'dnsutils', 'jq', 'ipcalc']

class File(Printable):
    """!
    @brief File class.

    This class represents a file on a node.
    """

    __content: str
    __path: str

    def __init__(self, path: str, content: str = ''):
        """!
        @brief File constructor.

        Put a file onto a node.

        @param path path of the file.
        @param content content of the file.
        """
        self.__path = path
        self.__content = content

    def setPath(self, path: str):
        """!
        @brief Update file path.

        @param path new path.
        """
        self.__path = path

    def setContent(self, content: str):
        """!
        @brief Update file content.

        @param content content.
        """
        self.__content = content

    def appendContent(self, content: str):
        """!
        @brief Append to file.

        @param content content.
        """
        self.__content += content

    def get(self) -> (str, str):
        """!
        @brief Get file path and content.

        @returns a tuple where the first element is path and second element is 
        content
        """
        return (self.__path, self.__content)

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += "{}:\n".format(self.__path)
        indent += 4
        for line in self.__content.splitlines():
            out += ' ' * indent
            out += '> '
            out += line
            out += '\n'
        return out

class Interface(Printable):
    """!
    @brief Interface class.

    This class represents a network interface card.
    """

    __network: Network
    __address: IPv4Address

    __latency: int       # in ms
    __bandwidth: int     # in bps
    __drop: float        # percentage

    def __init__(self, net: Network):
        """!
        @brief Interface constructor.

        @param net network to connect to.
        """
        self.__address = None
        self.__network = net
        (l, b, d) = net.getDefaultLinkProperties()
        self.__latency = l
        self.__bandwidth = b
        self.__drop = d

    def setLinkProperties(self, latency: int = 0, bandwidth: int = 0, packetDrop: float = 0):
        """!
        @brief Set link properties.

        @param latency (optional) latency to add to the link in ms, default 0.
        @param bandwidth (optional) egress bandwidth of the link in bps, 0 for unlimited, default 0.
        @param packetDrop (optional) link packet drop as percentage, 0 for unlimited, default 0.
        """

        assert latency >= 0, 'invalid latency'
        assert bandwidth >= 0, 'invalid bandwidth'
        assert packetDrop >= 0 and packetDrop <= 100, 'invalid packet drop'

        self.__latency = latency
        self.__bandwidth = bandwidth
        self.__drop = packetDrop

    def getLinkProperties(self) -> Tuple[int, int, int]:
        """!
        @brief Get link properties.

        @returns tuple (latency, bandwidth, packet drop)
        """
        return (self.__latency, self.__bandwidth, self.__drop)

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
        out += ' ' * indent
        out += 'Link Properties: {}\n'.format(self.__address)

        indent += 4
        out += ' ' * indent
        out += 'Added Latency: {} ms\n'.format(self.__latency)
        out += ' ' * indent
        out += 'Egress Bandwidth Limit: {} bps\n'.format('unlimited' if self.__bandwidth <= 0 else self.__bandwidth)

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
    __files: Dict[str, File]
    __softwares: Set[str]
    __build_commands: List[str]
    __start_commands: List[Tuple[str, bool]]
    __ports: List[Tuple[int, int, str]]
    __privileged: bool
    __common_software: Set[str] = set()

    def __init__(self, name: str, role: NodeRole, asn: int, scope: str = None):
        """!
        @brief Node constructor.

        @name name name of this node.
        @param role role of this node.
        @param asn network that this node belongs to.
        @param scope scope of the node, if not asn.
        """
        self.__interfaces = []
        self.__files = {}
        self.__asn = asn
        self.__reg = ScopedRegistry(scope if scope != None else str(asn))
        self.__role = role
        self.__name = name
        self.__softwares = set()
        self.__build_commands = []
        self.__start_commands = []
        self.__ports = []
        self.__privileged = False

        for soft in DEFAULT_SOFTWARES:
            self.__common_software.add(soft)

    def addPort(self, host: int, node: int, proto: str = 'tcp'):
        """!
        @brief Add port forwarding.

        @param host port of the host.
        @param node port of the node.
        @param proto protocol.
        """
        self.__ports.append((host, node, proto))

    def getPorts(self) -> List[Tuple[int, int]]:
        """!
        @brief Get port forwardings.

        @returns list of tuple of ports (host, node).
        """
        return self.__ports

    def setPrivileged(self, privileged: bool):
        """!
        @brief Set or unset the node as privileged node.

        Some backend like Docker will require the container to be privileged
        in order to do some privileged operations.

        @param privileged (optional) set if node is privileged.
        """
        self.__privileged = privileged

    def isPrivileged(self,) -> bool:
        """!
        @brief Test if node is set to privileged.

        @returns True if privileged, False otherwise.
        """
        return self.__privileged

    def joinNetwork(self, net: Network, address: str = "auto") -> Interface:
        """!
        @brief Connect the node to a network.
        @param net network to connect.
        @param address (optional) override address assigment.

        @throws AssertionError if network does not exist.
        """
        
        if address == "auto": _addr = net.assign(self.__role, self.__asn)
        else: _addr = IPv4Address(address)

        _iface = Interface(net)
        _iface.setAddress(_addr)

        self.__interfaces.append(_iface)
        
        net.associate(self)
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

    def getName(self) -> str:
        """!
        @brief Get node name.

        @returns name.
        """
        return self.__name

    def getAsn(self) -> int:
        """!
        @brief Get node parent AS ASN.

        @returns asm.
        """
        return self.__asn

    def getRole(self) -> NodeRole:
        """!
        @brief Get role of current node.

        Get role type of current node. 

        @returns role.
        """
        return self.__role

    def getFile(self, path: str) -> File:
        """!
        @brief Get a file object, and create if not exist.

        @param path file path.
        @returns file.
        """
        if path in self.__files: return self.__files[path]
        self.__files[path] = File(path)
        return self.__files[path]

    def getFiles(self) -> List[File]:
        """!
        @brief Get all files.

        @return list of files.
        """
        return self.__files.values()

    def setFile(self, path: str, content: str):
        """!
        @brief Set content of the file.

        @param path path of the file. Will be created if not exist, and will be
        override if already exist.
        @param content file content.
        """
        self.getFile(path).setContent(content)

    def appendFile(self, path: str, content: str):
        """!
        @brief Append content to a file.

        @param path path of the file. Will be created if not exist.
        @param content content to append.
        """
        self.getFile(path).appendContent(content)

    def addSoftware(self, name: str):
        """!
        @brief Add new software to node.

        @param name software package name.

        Use this to add software to the node. For example, if using the "docker"
        compiler, this will be added as an "apt-get install" line in Dockerfile.
        """
        self.__softwares.add(name)

    def addCommonSoftware(self, name: str):
        """!
        @brief Add new software to all node.

        @param name software package name.

        Use this to add software to all node. For example, if using the "docker"
        compiler, this will be added as an "apt-get install" line in Dockerfile
        of all nodes.
        """
        self.__common_software.add(name)

    def getSoftwares(self) -> Set[str]:
        """!
        @brief Get set of software.

        @returns set of softwares.
        """
        return self.__softwares

    def getCommonSoftware(self) -> Set[str]:
        """!
        @brief Get set of common software.

        @returns set of softwares.
        """
        return self.__common_software

    def addBuildCommand(self, cmd: str):
        """!
        @brief Add new command to build step.

        @param cmd command to add.

        Use this to add build steps to the node. For example, if using the
        "docker" compiler, this will be added as a "RUN" line in Dockerfile.
        """
        self.__build_commands.append(cmd)
    
    def getBuildCommands(self) -> List[str]:
        """!
        @brief Get build commands.

        @returns list of commands.
        """
        return self.__build_commands

    def addStartCommand(self, cmd: str, fork: bool = False):
        """!
        @brief Add new command to start script.

        The command should not be a blocking command. If you need to run a
        blocking command, set fork to true and fork it to the background so
        that it won't block the execution of other commands.

        @param cmd command to add.
        @param fork (optional) fork to command to background?

        Use this to add start steps to the node. For example, if using the
        "docker" compiler, this will be added to start.sh.
        """
        self.__start_commands.append((cmd, fork))

    def getStartCommands(self) -> List[Tuple[str, bool]]:
        """!
        @brief Get start commands.

        @returns list of tuples, where the first element is command, and the
        second element indicates if this command should be forked.
        """
        return self.__start_commands

    def getInterfaces(self) -> List[Interface]:
        """!
        @brief Get list of interfaces.

        @returns list of interfaces.
        """
        return self.__interfaces
        
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

        out += ' ' * indent
        out += 'Files:\n'
        for file in self.__files.values():
            out += file.print(indent + 4)

        out += ' ' * indent
        out += 'Software:\n'
        indent += 4
        for software in self.__softwares:
            out += ' ' * indent
            out += '{}\n'.format(software)
        indent -= 4

        out += ' ' * indent
        out += 'Additional Build Commands:\n'
        indent += 4
        for cmd in self.__build_commands:
            out += ' ' * indent
            out += '{}\n'.format(cmd)
        indent -= 4

        out += ' ' * indent
        out += 'Additional Start Commands:\n'
        indent += 4
        for (cmd, fork) in self.__start_commands:
            out += ' ' * indent
            out += '{}{}\n'.format(cmd, ' (fork)' if fork else '')
        indent -= 4

        return out
