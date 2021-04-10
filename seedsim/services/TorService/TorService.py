#!/usr/bin/env python
# encoding: utf-8
# __author__ = 'Demon'

from seedsim.core import Node, Printable, Simulator, Service, Server
from seedsim.core.enums import NetworkType
from typing import List, Dict, Tuple, Set
import pkgutil
from enum import Enum

TorServerFileTemplates: Dict[str, str] = {}

TorServerFileTemplates["torrc"] = pkgutil.get_data(__name__, 'config/torrc').decode("utf-8")
TorServerFileTemplates["torrc.da"] = pkgutil.get_data(__name__, 'config/torrc.da').decode("utf-8")
TorServerFileTemplates["da_fingerprint"] = pkgutil.get_data(__name__, 'config/da_fingerprint').decode("utf-8")
TorServerFileTemplates["tor-entrypoint"] = pkgutil.get_data(__name__, 'config/tor-entrypoint').decode("utf-8")
TorServerFileTemplates["downloader"] = """
    until $(curl --output /dev/null --silent --head --fail http://{da_addr}:8888); do
        echo "DA server not ready"
        sleep 3
    done
    sleep 3
    FINGERPRINT=$(curl -s {da_addr}:8888/torrc.da)

    while ! echo $FINGERPRINT | grep DirAuthority
    do
        echo " fingerprint not ready"
        sleep 2
    done
    echo "fingerprint ready"
    echo $FINGERPRINT >> /etc/tor/torrc
"""

BUILD_COMMANDS = """build_temps="build-essential automake" && \
    build_deps="libssl-dev zlib1g-dev libevent-dev ca-certificates\
        dh-apparmor libseccomp-dev dh-systemd \
        git" && \
    DEBIAN_FRONTEND=noninteractive apt-get -y --no-install-recommends install $build_deps $build_temps \
        init-system-helpers \
        pwgen && \
    mkdir /src && \
    cd /src && \
    git clone https://git.torproject.org/tor.git && \
    cd tor && \
    git checkout ${TOR_VER} && \
    ./autogen.sh && \
    ./configure --disable-asciidoc && \
    make && \
    make install && \
    apt-get -y purge --auto-remove $build_temps && \
    apt-get clean && rm -r /var/lib/apt/lists/* && \
    rm -rf /src/*
"""


class TorNodeType(Enum):
    DA = "DA"
    RELAY = "RELAY"
    EXIT = "EXIT"
    CLIENT = "CLIENT"
    HS = "HS"


class TorServer(Server):
    """!
    @brief The Tor server.
    """

    __role: TorNodeType
    __hs_link: Set

    def __init__(self):
        """!
        @brief TorServer constructor.

        @param node node to install server on.
        """
        self.__role = TorNodeType.RELAY.value
        self.__hs_link = ()

    def setRole(self, role: Enum):
        self.__role = role.value

    def getRole(self) -> str:
        return self.__role

    def getLink(self) -> str:
        return self.__hs_link

    def setLink(self, addr, port: int):
        self.__hs_link = (addr, port)

    def linkByVnode(self, vname: str, port: int):
        assert self.getRole() == "HS", "linkByVnode(): only HS type node can bind a host."
        assert len(self.__hs_link) == 0, "linkByVnode(): TorServer already has linked a host."
        self.__hs_link = (vname, port)

    def configure(self, node: Node, tor):
        ifaces = node.getInterfaces()
        assert len(ifaces) > 0, 'TorNode configure(): node has not interfaces'
        addr = ifaces[0].getAddress()

        if self.getRole() == "DA":
            tor.addDirAuthority(addr)

        if self.getRole() == "HS" and len(self.getLink()) != 0:
            addr, port = self.getLink()
            node.appendStartCommand("export TOR_HS_ADDR={}".format(addr))
            node.appendStartCommand("export TOR_HS_PORT={}".format(port))

    def install(self, node: Node, tor):
        ifaces = node.getInterfaces()
        assert len(ifaces) > 0, 'node has not interfaces'
        addr = ifaces[0].getAddress()
        download_commands = ""
        for dir in tor.getDirAuthority():
            download_commands += TorServerFileTemplates["downloader"].format(da_addr=dir)

        node.addSoftware("git python3")
        node.addBuildCommand(BUILD_COMMANDS)
        node.setFile("/etc/tor/torrc", TorServerFileTemplates["torrc"])
        node.setFile("/etc/tor/torrc.da", TorServerFileTemplates["torrc.da"])
        node.setFile("/usr/local/bin/da_fingerprint", TorServerFileTemplates["da_fingerprint"])
        node.setFile("/usr/local/bin/tor-entrypoint", TorServerFileTemplates["tor-entrypoint"].format(TOR_IP=addr, downloader = download_commands))
        node.appendStartCommand("export TOR_ORPORT=7000")
        node.appendStartCommand("export TOR_DIRPORT=9030")
        node.appendStartCommand("export TOR_DIR=/tor")
        node.appendStartCommand("export ROLE={}".format(self.__role))
        node.appendStartCommand("chmod +x /usr/local/bin/tor-entrypoint /usr/local/bin/da_fingerprint")
        node.appendStartCommand("mkdir /tor")
        if self.getRole() == "DA":
            node.appendStartCommand("python3 -m http.server 8888 -d /tor &")
        node.appendStartCommand("tor-entrypoint")
        node.appendStartCommand("tor -f /etc/tor/torrc")

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'TorServer'

        return out

class TorService(Service):
    """!
    @brief The Tor network service.
    """

    def __init__(self):
        super().__init__()
        self.__da_nodes = []

    def getName(self):
        return 'TorService'

    def _doConfigure(self, node: Node, server: TorServer):
        server.configure(node, self)

    def addDirAuthority(self, addr: str):
        self.__da_nodes.append(addr)

    def getDirAuthority(self):
        return self.__da_nodes

    def __resolveHSLink(self, simulator: Simulator):
        for server in self.getPendingTargets().values():
            if server.getRole() == "HS" and len(server.getLink()) != 0:
                vname, port = server.getLink()
                pnode = simulator.resolvVnode(vname)
                ifaces = pnode.getInterfaces()
                assert len(ifaces) > 0, '__resolveHSLink(): node as{}/{} has no interfaces'.format(pnode.getAsn(), pnode.getName())
                addr = ifaces[0].getAddress()
                server.setLink(addr, port)

    def configure(self, simulator: Simulator):
        self.__resolveHSLink(simulator)
        return super().configure(simulator)

    def _doInstall(self, node: Node, server: TorServer):
        server.install(node, self)

    def _createServer(self) -> Server:
        return TorServer()