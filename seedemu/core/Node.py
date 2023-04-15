from __future__ import annotations
from .Printable import Printable
from .Network import Network
from .enums import NodeRole
from .Registry import Registrable
from .Emulator import Emulator
from .Configurable import Configurable
from .enums import NetworkType
from .Visualization import Vertex
from ipaddress import IPv4Address, IPv4Interface
from typing import List, Dict, Set, Tuple
from string import ascii_letters
from random import choice
from .BaseSystem import BaseSystem

DEFAULT_SOFTWARE: List[str] = ['zsh', 'curl', 'nano', 'vim-nox', 'mtr-tiny', 'iproute2', 'iputils-ping', 'tcpdump', 'termshark', 'dnsutils', 'jq', 'ipcalc', 'netcat']

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

    def setPath(self, path: str) -> File:
        """!
        @brief Update file path.

        @param path new path.

        @returns self, for chaining API calls.
        """
        self.__path = path

        return self

    def setContent(self, content: str) -> File:
        """!
        @brief Update file content.

        @param content content.

        @returns self, for chaining API calls.
        """
        self.__content = content

        return self

    def appendContent(self, content: str) -> File:
        """!
        @brief Append to file.

        @param content content.

        @returns self, for chaining API calls.
        """
        self.__content += content

        return self

    def get(self) -> Tuple[str, str]:
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

    def setLinkProperties(self, latency: int = 0, bandwidth: int = 0, packetDrop: float = 0) -> Interface:
        """!
        @brief Set link properties.

        @param latency (optional) latency to add to the link in ms, default 0.
        @param bandwidth (optional) egress bandwidth of the link in bps, 0 for unlimited, default 0.
        @param packetDrop (optional) link packet drop as percentage, 0 for unlimited, default 0.

        @returns self, for chaining API calls.
        """

        assert latency >= 0, 'invalid latency'
        assert bandwidth >= 0, 'invalid bandwidth'
        assert packetDrop >= 0 and packetDrop <= 100, 'invalid packet drop'

        self.__latency = latency
        self.__bandwidth = bandwidth
        self.__drop = packetDrop

        return self

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

    def setAddress(self, address: IPv4Address) -> Interface:
        """!
        @brief Set IPv4 address of this interface.

        @param address address.

        @returns self, for chaining API calls.
        """
        self.__address = address

        return self

    def getAddress(self) -> IPv4Address:
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

class Node(Printable, Registrable, Configurable, Vertex):
    """!
    @brief Node base class.

    This class represents a generic node.
    """

    __name: str
    __base_system: BaseSystem
    __asn: int
    __scope: str
    __role: NodeRole
    __classes: List[str]
    __label: Dict[str, str]
    __interfaces: List[Interface]
    __files: Dict[str, File]
    __imported_files: Dict[str, str]
    __softwares: Set[str]
    __build_commands: List[str]
    __start_commands: List[Tuple[str, bool]]
    __ports: List[Tuple[int, int, str]]
    __privileged: bool

    __configured: bool
    __pending_nets: List[Tuple[str, str]]
    __xcs: Dict[Tuple[str, int], Tuple[IPv4Interface, str]]

    __shared_folders: Dict[str, str]
    __persistent_storages: List[str]

    __name_servers: List[str]

    def __init__(self, name: str, role: NodeRole, asn: int, scope: str = None):
        """!
        @brief Node constructor.

        @name name name of this node.
        @param role role of this node.
        @param asn network that this node belongs to.
        @param scope scope of the node, if not asn.
        """
        super().__init__()

        self.__interfaces = []
        self.__files = {}
        self.__imported_files = {}
        self.__asn = asn
        self.__role = role
        self.__name = name
        self.__classes = []
        self.__label = {}
        self.__scope = scope if scope != None else str(asn)
        self.__softwares = set()
        self.__build_commands = []
        self.__start_commands = []
        self.__ports = []
        self.__privileged = False
        self.__base_system = BaseSystem.DEFAULT

        self.__pending_nets = []
        self.__xcs = {}
        self.__configured = False

        self.__shared_folders = {}
        self.__persistent_storages = []

        # for soft in DEFAULT_SOFTWARE:
        #     self.__softwares.add(soft)

        self.__name_servers = []

    def configure(self, emulator: Emulator):
        """!
        @brief configure the node. This is called when rendering.

        NICs will be setup during the configuring process. No new interfaces
        can be added after configuration.

        @param emulator Emulator object to use to configure.
        """
        assert not self.__configured, 'Node already configured.'
        assert not self.__asn == 0, 'Virtual physical node must not be used in render/configure'

        reg = emulator.getRegistry()

        for (netname, address) in self.__pending_nets:

            hit = False

            if reg.has(self.__scope, "net", netname):
                hit = True
                self.__joinNetwork(reg.get(self.__scope, "net", netname), address)

            if not hit and reg.has("ix", "net", netname):
                hit = True
                self.__joinNetwork(reg.get("ix", "net", netname), address)

            if not hit and reg.has("seedemu", "net", netname):
                hit = True
                self.__joinNetwork(reg.get("seedemu", "net", netname), address)

            assert hit, 'no network matched for name {}'.format(netname)

        for (peername, peerasn) in list(self.__xcs.keys()):
            peer: Node = None

            if reg.has(str(peerasn), 'rnode', peername): peer = reg.get(str(peerasn), 'rnode', peername)
            elif reg.has(str(peerasn), 'hnode', peername): peer = reg.get(str(peerasn), 'hnode', peername)
            else: assert False, 'as{}/{}: cannot xc to node as{}/{}: no such node'.format(self.getAsn(), self.getName(), peerasn, peername)

            (peeraddr, netname) = peer.getCrossConnect(self.getAsn(), self.getName())
            (localaddr, _) = self.__xcs[(peername, peerasn)]
            assert localaddr.network == peeraddr.network, 'as{}/{}: cannot xc to node as{}/{}: {}.net != {}.net'.format(self.getAsn(), self.getName(), peerasn, peername, localaddr, peeraddr)

            if netname != None:
                self.__joinNetwork(reg.get('xc', 'net', netname), str(localaddr.ip))
                self.__xcs[(peername, peerasn)] = (localaddr, netname)
            else:
                # netname = 'as{}.{}_as{}.{}'.format(self.getAsn(), self.getName(), peerasn, peername)
                netname = ''.join(choice(ascii_letters) for i in range(10))
                net = Network(netname, NetworkType.CrossConnect, localaddr.network, direct = False) # TODO: XC nets w/ direct flag?
                self.__joinNetwork(reg.register('xc', 'net', netname, net), str(localaddr.ip))
                self.__xcs[(peername, peerasn)] = (localaddr, netname)

        if len(self.__name_servers) == 0:
            return

        self.insertStartCommand(0,': > /etc/resolv.conf')
        for idx, s in enumerate(self.__name_servers, start=1):
            self.insertStartCommand(idx, 'echo "nameserver {}" >> /etc/resolv.conf'.format(s))

    def setNameServers(self, servers: List[str]) -> Node:
        """!
        @brief set recursive name servers to use on this node. Overwrites
        AS-level and emulator-level settings.

        @param servers list of IP addresses of recursive name servers. Set to
        empty list to use default (i.e., do not change, or use
        AS-level/emulator-level settings)

        @returns self, for chaining API calls.
        """
        assert not self.__asn == 0, 'This API is only available on a real physical node.'

        self.__name_servers = servers

        return self

    def getNameServers(self) -> List[str]:
        """!
        @brief get configured recursive name servers on this node.

        @returns list of IP addresses of recursive name servers
        """
        assert not self.__asn == 0, 'This API is only available on a real physical node.'

        return self.__name_servers

    def addPort(self, host: int, node: int, proto: str = 'tcp') -> Node:
        """!
        @brief Add port forwarding.

        @param host port of the host.
        @param node port of the node.
        @param proto protocol.

        @returns self, for chaining API calls.
        """
        self.__ports.append((host, node, proto))

    def addPortForwarding(self, host: int, node: int, proto:str = 'tcp') -> Node:
        """!
        @brief Achieves the same as the addPort function.
        @brief Keeping addPort to avoid breaking other examples.
        @brief Just a more descriptive name.
        """
        self.__ports.append((host, node, proto))

    def getPorts(self) -> List[Tuple[int, int, str]]:
        """!
        @brief Get port forwardings.

        @returns list of tuple of ports (host, node).

        """
        return self.__ports

    def setPrivileged(self, privileged: bool) -> Node:
        """!
        @brief Set or unset the node as privileged node.

        Some backend like Docker will require the container to be privileged
        in order to do some privileged operations.

        @param privileged (optional) set if node is privileged.

        @returns self, for chaining API calls.
        """
        self.__privileged = privileged

    def isPrivileged(self) -> bool:
        """!
        @brief Test if node is set to privileged.

        @returns True if privileged, False otherwise.
        """
        return self.__privileged

    def setBaseSystem(self, base_system: BaseSystem) -> Node:
        """!
        @brief Set a base_system of a node.

        @param base_system base_system to use.

        @returns self, for chaining API calls.
        """
        self.__base_system = base_system

    def getBaseSystem(self) -> BaseSystem:
        """!
        @brief Get configured base system on this node.

        @returns base system.
        """
        return self.__base_system

    def __joinNetwork(self, net: Network, address: str = "auto"):
        """!
        @brief Connect the node to a network.
        @param net network to connect.
        @param address (optional) override address assignment.

        @throws AssertionError if network does not exist.
        """

        if address == "auto": _addr = net.assign(self.__role, self.__asn)
        elif address == "dhcp":
            _addr = None
            self.__name_servers = []
            self.addSoftware('isc-dhcp-client')
            self.setFile('dhclient.sh', '''\
            #!/bin/bash
            ip addr flush {iface}
            err=$(dhclient {iface} 2>&1)

            if [ -z "$err" ]
            then
                    echo "dhclient success"
            else
                    filename=$(echo $err | cut -d "'" -f 2)
                    cp $filename /etc/resolv.conf
                    rm $filename
            fi
            '''.format(iface=net.getName()))
            self.appendStartCommand('chmod +x dhclient.sh; ./dhclient.sh')

        else: _addr = IPv4Address(address)

        _iface = Interface(net)
        _iface.setAddress(_addr)

        self.__interfaces.append(_iface)

        net.associate(self)

    def joinNetwork(self, netname: str, address: str = "auto") -> Node:
        """!
        @brief Connect the node to a network.
        @param netname name of the network.
        @param address (optional) override address assignment.

        @returns assigned IP address

        @returns self, for chaining API calls.
        """
        assert not self.__asn == 0, 'This API is only available on a real physical node.'
        assert not self.__configured, 'Node already configured.'

        self.__pending_nets.append((netname, address))

        return self

    def updateNetwork(self, netname:str, address: str= "auto") -> Node:
        """!
        @brief Update connection of the node to a network.
        @param netname name of the network.
        @param address (optional) override address assignment.

        @returns assigned IP address

        @returns self, for chaining API calls.
        """
        assert not self.__asn == 0, 'This API is only available on a real physical node.'

        for pending_netname, pending_address in self.__pending_nets:
            if pending_netname == netname:
                self.__pending_nets.remove((pending_netname, pending_address))

        self.__pending_nets.append((netname, address))

        return self

    def crossConnect(self, peerasn: int, peername: str, address: str) -> Node:
        """!
        @brief create new p2p cross-connect connection to a remote node.
        @param peername node name of the peer node.
        @param peerasn asn of the peer node.
        @param address address to use on the interface in CIDR notation. Must
        be within the same subnet.

        @returns self, for chaining API calls.
        """
        assert not self.__asn == 0, 'This API is only available on a real physical node.'
        assert peername != self.getName() or peerasn != self.getName(), 'cannot XC to self.'
        self.__xcs[(peername, peerasn)] = (IPv4Interface(address), None)

    def getCrossConnect(self, peerasn: int, peername: str) -> Tuple[IPv4Interface, str]:
        """!
        @brief retrieve IP address for the given peer.
        @param peername node name of the peer node.
        @param peerasn asn of the peer node.

        @returns tuple of IP address and XC network name. XC network name will
        be None if the network has not yet been created.
        """
        assert not self.__asn == 0, 'This API is only available on a real physical node.'
        assert (peername, peerasn) in self.__xcs, 'as{}/{} is not in the XC list.'.format(peerasn, peername)
        return self.__xcs[(peername, peerasn)]

    def getCrossConnects(self) -> Dict[Tuple[str, int], Tuple[IPv4Interface, str]]:
        """!
        @brief get all cross connects on this node.

        @returns dict, where key is (peer node name, peer node asn) and value is (address on interface, netname)
        """
        assert not self.__asn == 0, 'This API is only available on a real physical node.'
        return self.__xcs

    def getName(self) -> str:
        """!
        @brief Get node name.

        @returns name.
        """
        return self.__name

    def getAsn(self) -> int:
        """!
        @brief Get node parent AS ASN.

        @returns asn.
        """
        return self.__asn

    def getRole(self) -> NodeRole:
        """!
        @brief Get role of current node.

        Get role type of current node.

        @returns role.
        """
        return self.__role

    def appendClassName(self, className:str) -> Node:
        """!
        @brief Append class to a current node

        @returns self, for chaining API calls.
        """
        self.__classes.append(className)

        return self

    def getClasses(self) -> list:
        """!
        @brief Get service of current node

        @returns service
        """

        return self.__classes

    def setClasses(self, classes:list) -> list:
        """!
        @brief Set service of current node

        @returns self for chaining API calls.
        """
        self.__classes = classes
        return self

    def setLabel(self, key:str, value:str) -> Node:
        """!
        @brief Add Label to a current node

        @returns self, for chaining API calls.
        """

        self.__label[key] = value
        return self

    def getLabel(self) -> dict:
        return self.__label

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

    def setFile(self, path: str, content: str) -> Node:
        """!
        @brief Set content of the file.

        @param path path of the file. Will be created if not exist, and will be
        override if already exist.
        @param content file content.

        @returns self, for chaining API calls.
        """
        self.getFile(path).setContent(content)

        return self

    def appendFile(self, path: str, content: str) -> Node:
        """!
        @brief Append content to a file.

        @param path path of the file. Will be created if not exist.
        @param content content to append.

        @returns self, for chaining API calls.
        """
        self.getFile(path).appendContent(content)

        return self

    def getImportedFiles(self) -> Dict[str, str]:
        """!
        @brief Get imported files.

        @returns dict of imported files, where key = path of the file in the
        container, value = path of the file on the host.
        """
        return self.__imported_files

    def importFile(self, hostpath: str, containerpath: str) -> Node:
        """!
        @brief Import a file from the host to the container.

        @param hostpath path of the file on the host. (should be absolute to
        prevent issues)
        @param containerpath path of the file in the container.

        @returns self, for chaining API calls.
        """
        self.__imported_files[containerpath] = hostpath

        return self

    def addSoftware(self, name: str) -> Node:
        """!
        @brief Add new software to node.

        @param name software package name.

        Use this to add software to the node. For example, if using the "docker"
        compiler, this will be added as an "apt-get install" line in Dockerfile.

        @returns self, for chaining API calls.
        """
        if ' ' in name:
            for soft in name.split(' '):
                self.__softwares.add(soft)
        else:
            self.__softwares.add(name)

        return self

    def getSoftware(self) -> Set[str]:
        """!
        @brief Get set of software.

        @returns set of softwares.
        """
        return self.__softwares

    def addBuildCommand(self, cmd: str) -> Node:
        """!
        @brief Add new command to build step.

        Use this to add build steps to the node. For example, if using the
        "docker" compiler, this will be added as a "RUN" line in Dockerfile.

        @param cmd command to add.

        @returns self, for chaining API calls.
        """
        self.__build_commands.append(cmd)

        return self

    def getBuildCommands(self) -> List[str]:
        """!
        @brief Get build commands.

        @returns list of commands.
        """
        return self.__build_commands

    def insertStartCommand(self, index: int, cmd: str, fork: bool = False) -> Node:
        """!
        @brief Add new command to start script.

        The command should not be a blocking command. If you need to run a
        blocking command, set fork to true and fork it to the background so
        that it won't block the execution of other commands.

        Use this to add start steps to the node. For example, if using the
        "docker" compiler, this will be added to start.sh.

        @param index index to insert command in.
        @param cmd command to add.
        @param fork (optional) fork to command to background?

        @returns self, for chaining API calls.
        """
        self.__start_commands.insert(index, (cmd, fork))

        return self

    def appendStartCommand(self, cmd: str, fork: bool = False) -> Node:
        """!
        @brief Add new command to start script.

        The command should not be a blocking command. If you need to run a
        blocking command, set fork to true and fork it to the background so
        that it won't block the execution of other commands.

        @param cmd command to add.
        @param fork (optional) fork to command to background?

        Use this to add start steps to the node. For example, if using the
        "docker" compiler, this will be added to start.sh.

        @returns self, for chaining API calls.
        """
        self.__start_commands.append((cmd, fork))

        return self

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

    def addSharedFolder(self, nodePath: str, hostPath: str) -> Node:
        """!
        @@brief Add a new shared folder between the node and host.

        @param nodePath path to the folder inside the container.
        @param hostPath path to the folder on the emulator host node.

        @returns self, for chaining API calls.
        """
        self.__shared_folders[nodePath] = hostPath

        return self

    def getSharedFolders(self) -> Dict[str, str]:
        """!
        @brief Get shared folders between the node and host.

        @returns dict, where key is the path in container and value is path on
        host.
        """
        return self.__shared_folders

    def addPersistentStorage(self, path: str) -> Node:
        """!
        @brief Add persistent storage to node.

        Nodes usually start fresh when you re-start them. This allow setting a
        directory where data will be persistent.

        @param path path to put the persistent storage folder in the container.

        @returns self, for chaining API calls.
        """
        self.__persistent_storages.append(path)

        return self

    def getPersistentStorages(self) -> List[str]:
        """!
        @brief Get persistent storage folders on the node.

        @returns list of persistent storage folder.
        """
        return self.__persistent_storages

    def copySettings(self, node: Node):
        """!
        @brief copy settings from another node.

        @param node node to copy from.
        """
        if node.getDisplayName() != None: self.setDisplayName(node.getDisplayName())
        if node.getDescription() != None: self.setDescription(node.getDescription())
        if node.getClasses()     != None: self.setClasses(node.getClasses())

        # TODO:
        # It is called in Emulator::render
        # Render steps are (1) Render Base, (2) Get pending targets(vnode name) from Service layers,
        # (3) Resolve bindings for all vnodes, (4) Applying changes made to virtual physical nodes to real physical nodes,
        # (5) Render Services.
        # copySettings is called in the step (4) and the base system is replaced when in the step (5)
        # if node.getBaseSystem() != None : self.setBaseSystem(node.getClasses())

        for (h, n, p) in node.getPorts(): self.addPort(h, n, p)
        for p in node.getPersistentStorages(): self.addPersistentStorage(p)
        for (c, f) in node.getStartCommands(): self.appendStartCommand(c, f)
        for c in node.getBuildCommands(): self.addBuildCommand(c)
        for s in node.getSoftware(): self.addSoftware(s)

        for file in node.getFiles():
            (path, content) = file.get()
            self.setFile(path, content)


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

RouterFileTemplates: Dict[str, str] = {}

RouterFileTemplates["protocol"] = """\
protocol {protocol} {name} {{{body}}}
"""

RouterFileTemplates["pipe"] = """\
protocol pipe {{
    table {src};
    peer table {dst};
    import {importFilter};
    export {exportFilter};
}}
"""

RouterFileTemplates['rw_configure_script'] = '''\
#!/bin/bash
gw="`ip rou show default | cut -d' ' -f3`"
sed -i 's/!__default_gw__!/'"$gw"'/g' /etc/bird/bird.conf
'''

class Router(Node):
    """!
    @brief Node extension class.

    Nodes with routing install will be replaced with this to get the extension
    methods.
    """

    __loopback_address: str

    def setLoopbackAddress(self, address: str):
        """!
        @brief Set loopback address.

        @param address address.
        """
        self.__loopback_address = address

    def getLoopbackAddress(self) -> str:
        """!
        @brief Get loopback address.

        @returns address.
        """
        return self.__loopback_address

    def addProtocol(self, protocol: str, name: str, body: str) -> Router:
        """!
        @brief Add a new protocol to BIRD on the given node.

        @param protocol protocol type. (e.g., bgp, ospf)
        @param name protocol name.
        @param body protocol body.

        @returns self, for chaining API calls.
        """
        self.appendFile("/etc/bird/bird.conf", RouterFileTemplates["protocol"].format(
            protocol = protocol,
            name = name,
            body = body
        ))

        return self

    def addTablePipe(self, src: str, dst: str = 'master4', importFilter: str = 'none', exportFilter: str = 'all', ignoreExist: bool = True) -> Router:
        """!
        @brief add a new routing table pipe.

        @param src src table.
        @param dst (optional) dst table (default: master4)
        @param importFilter (optional) filter for importing from dst table to src table (default: none)
        @param exportFilter (optional) filter for exporting from src table to dst table (default: all)
        @param ignoreExist (optional) assert check if table exists. If true, error is silently discarded.

        @throws AssertionError if pipe between two tables already exist and ignoreExist is False.

        @returns self, for chaining API calls.
        """
        meta = self.getAttribute('__routing_layer_metadata', {})
        if 'pipes' not in meta: meta['pipes'] = {}
        pipes = meta['pipes']
        if src not in pipes: pipes[src] = []
        if dst in pipes[src]:
            assert ignoreExist, 'pipe from {} to {} already exist'.format(src, dst)
            return
        pipes[src].append(dst)
        self.appendFile('/etc/bird/bird.conf', RouterFileTemplates["pipe"].format(
            src = src,
            dst = dst,
            importFilter = importFilter,
            exportFilter = exportFilter
        ))

        return self

    def addTable(self, tableName: str) -> Router:
        """!
        @brief Add a new routing table to BIRD on the given node.

        @param tableName name of the new table.

        @returns self, for chaining API calls.
        """
        meta = self.getAttribute('__routing_layer_metadata', {})
        if 'tables' not in meta: meta['tables'] = []
        tables = meta['tables']
        if tableName not in tables: self.appendFile('/etc/bird/bird.conf', 'ipv4 table {};\n'.format(tableName))
        tables.append(tableName)

        return self

class RealWorldRouter(Router):
    """!
    @brief RealWorldRouter class.

    This class extends the router node to supporting routing prefix to real
    world.

    @todo real world access.
    """

    __realworld_routes: List[str]
    __sealed: bool
    __hide_hops: bool

    def initRealWorld(self, hideHops: bool):
        """!
        @brief init RealWorldRouter.
        """
        if hasattr(self, '__sealed'): return
        self.__realworld_routes = []
        self.__sealed = False
        self.__hide_hops = hideHops
        self.addSoftware('iptables')

    def addRealWorldRoute(self, prefix: str) -> RealWorldRouter:
        """!
        @brief Add real world route.

        @param prefix prefix.

        @throws AssertionError if sealed.

        @returns self, for chaining API calls.
        """
        assert not self.__sealed, 'Node sealed.'
        self.__realworld_routes.append(prefix)

        return self

    def getRealWorldRoutes(self) -> List[str]:
        """!
        @brief Get list of real world prefixes.

        @returns list of prefixes.
        """
        return self.__realworld_routes

    def seal(self):
        """!
        @brief seal the realworld router.

        Use this method to "seal" the router (add static protocol.) No new real
        world routes can be added once the node is sealed.
        """
        if self.__sealed: return
        self.__sealed = True
        if len(self.__realworld_routes) == 0: return
        self.setFile('/rw_configure_script', RouterFileTemplates['rw_configure_script'])
        self.insertStartCommand(0, '/rw_configure_script')
        self.insertStartCommand(0, 'chmod +x /rw_configure_script')
        self.addTable('t_rw')
        statics = '\n    ipv4 { table t_rw; import all; };\n    route ' + ' via !__default_gw__!;\n    route '.join(self.__realworld_routes)
        statics += ' via !__default_gw__!;\n'
        for prefix in self.__realworld_routes:
            # nat matched only
            self.appendFile('/rw_configure_script', 'iptables -t nat -A POSTROUTING -d {} -j MASQUERADE\n'.format(prefix))

            if self.__hide_hops:
                # remove realworld hops
                self.appendFile('/rw_configure_script', 'iptables -t mangle -A POSTROUTING -d {} -j TTL --ttl-set 64\n'.format(prefix))

        self.addProtocol('static', 'real_world', statics)
        self.addTablePipe('t_rw', 't_bgp', exportFilter = 'filter { bgp_large_community.add(LOCAL_COMM); bgp_local_pref = 40; accept; }')
        # self.addTablePipe('t_rw', 't_ospf') # TODO


    def print(self, indent: int) -> str:
        out = super(RealWorldRouter, self).print(indent)
        indent += 4

        out += ' ' * indent
        out += 'Real-world prefixes:\n'

        indent += 4
        for prefix in self.__realworld_routes:
            out += ' ' * indent
            out += '{}\n'.format(prefix)


        return out


class ScionRouter(Router):
    """!
    @brief Extends Router nodes for SCION routing.

    SCION border router nodes will be replaced with this class during ScionRouting
    layer configuration.
    """

    __interfaces: Dict[int, Dict]  # IFID to interface
    __next_port: int               # Next free UDP port

    def __init__(self):
        super().__init__()
        self.initScionRouter()

    def initScionRouter(self):
        self.__interfaces = {}
        self.__next_port = 50000

    def addScionInterface(self, ifid: int, iface: Dict) -> None:
        """!
        @brief Add a SCION interface to the border router.

        @param ifid Interface ID of the new interface.
        @param iface Interface definition.
        """
        assert ifid not in self.__interfaces, f"interface {ifid} already exists"
        self.__interfaces[ifid] = iface

    def getScionInterface(self, ifid: int) -> Dict:
        """!
        @brief Retrieve an existing interface.

        @param ifid Interface ID to look up.
        @throws AssertionError if the interface does not exist.
        """
        assert ifid in self.__interfaces, f"interface {ifid} does not exist"
        return self.__interfaces[ifid]

    def getScionInterfaces(self) -> Dict[int, Dict]:
        """!
        @brief Get all border router interfaces.
        @returns IFIDs and interface declarations for border router.
        """
        return self.__interfaces

    def getNextPort(self) -> int:
        """!
        @brief Get the next free UDP port. Called during configuration.
        """
        port = self.__next_port
        self.__next_port += 1
        return port
