"""Internet Simulator Nodes."""

import os
import csv

from .constants import *


class Machine:
    """!Machine class

    The base Machine class. This class represents an generic machine in the simulation."""
    
    def __init__(self, name: str):
        """!Machine constructor

        @param self The object pointer.
        @param name The name of this Machine."""
        self.name = name

    def getName(self):
        """!Get name of the Machine.

        @param self The object pointer.
        @returns str Name of this router."""
        return self.name


class Host(Machine):
    """!Host class
    
    This class represents an host node in the simulation."""

    def __init__(self, name: str, network: str, ip: str, simulator):
        """!Host constructor

        @param self The object pointer.
        @param name The name of this host.
        @param network The name of network to connect to.
        @param ip The ip address of this host.
        @param simulator Reference to the parent simulator object.
        """
        self.name = name
        self.network = network
        self.ip = ip

        # remember the simulator it belongs to
        self.simulator = simulator

    def printDetails(self):
        """!Print the details to stdout.

        @param self The object pointer."""
        print(self.name)
        print("   ", self.network, self.ip)

    def createStartScript(self):
        """!Get the start script as string.

        @param self The object pointer.
        @returns str Content of start.sh."""
        network = self.simulator.getNetwork(self.network)
        router = network.getDefaultRT()
        content = FileTemplate.hostStartScript.format(router)
        return content

    def createDockerComposeEntry(self):
        """!Get the docker compose file as string

        @param self The object pointer.
        @returns str Part of docker-compose.yml"""
        entry = FileTemplate.docker_compose_host_entry
        result = entry.format(self.name, "./" + self.name,
                              self.network, self.ip)

        return result


class Router(Machine):
    """!Router class
    
    This class represents a router node in the simulation."""
    def __init__(self, name: str, sim):
        """!Router constructor

        @param self The object pointer.
        @param name The name of this router.
        @param sim Reference to the parent simulator object.
        """
        self.name = name
        self.interfaces = []

        # remember the simulator it belongs to
        self.simulator = sim

    def printDetails(self):
        """!Print the details to stdout.

        @param self The object pointer."""
        print(self.name)
        self.listInterfaces()

    def listInterfaces(self):
        """!Print the interfaces details to stdout.

        @param self The object pointer."""
        print("  Interfaces:")
        for (name, ip) in self.interfaces:
            print("     ", name, ip)

    def addInterface(self, name: str, ip: str):
        """!Add an interface to router.

        @param self The object pointer.
        @param name Name of the interface.
        @param ip IP address on the interface."""
        self.interfaces.append((name, ip))

    def createBirdConf_OSPF(self):
        """!Get Bird's OSPF config.

        @param self The object pointer.
        @returns str Part of bird.conf."""
        area_0_entries = ""
        for i in range(len(self.interfaces)):
            ifn = 'eth' + str(i)
            area_0_entries += ' '*8 + "interface \"{}\" {{}};\n".format(ifn)

        return FileTemplate.birdConf_OSPF.format(area_0_entries)

    def createDockerComposeEntry(self):
        """!Get the docker compose file as string

        @param self The object pointer.
        @returns str Part of docker-compose.yml"""
        net_entries = ''
        for f in self.interfaces:
            template = FileTemplate.docker_compose_interface_entry
            net_entries += template.format(f[0], f[1]) + "\n"

        entry = FileTemplate.docker_compose_router_entry
        result = entry.format(self.name, "./" + self.name,
                              net_entries)

        return result


# For route server
class RouteServer(Router):
    """!RouteServer class

    This class represents a route server node in the simulation."""

    def __init__(self, name: str, ixp: int, sim):
        """!RouteServer constructor

        @param self The object pointer.
        @param name The name of this RouteServer.
        @param ixp The ASN of IXP this RouteServer belongs to.
        @param sim Reference to the parent simulator object.
        """
        self.name = name
        self.ixp = ixp
        self.type = 'rs'
        self.simulator = sim
        self.peers = set()    # Set of peers (names)
        self.interfaces = []  # Suppose to have only one interace

    def getIP_on_IXP_Network(self):
        """!Get IP address on the IX peering LAN.

        @param self The object pointer.
        @returns str IP address.
        """
        (network, ip) = self.interfaces[0]
        return ip

    def getASN(self):
        """!Get ASN of the RouteServer.

        @param self The object pointer.
        @returns int ASN.
        """
        return self.ixp

    def getType(self):
        """!Get type of the RouteServer.

        @param self The object pointer.
        @returns str type.
        """
        return self.type

    def addPeer(self, peername: str):
        """!Add a peer.

        @param self The object pointer.
        @param peername The name of the peer AS.
        """

        self.peers.add(peername)

    def initializeNetwork(self):
        """!Create the IX peering LAN.

        @param self The object pointer.
        """
        net_name = SimConstants.IXNETNAME.format(self.ixp)
        net = self.simulator.getNetwork(net_name)
        if net:
            ip = net.getIPByASN(self.ixp)
            self.addInterface(net_name, ip)

    def listPeers(self):
        """!Print the list of peers to stdout.

        @param self The object pointer."""
        print("  Peers:")
        for peer in self.peers:
            print("     ", peer)

    def printDetails(self):
        """!Print the details to stdout.

        @param self The object pointer."""
        print(self.name)
        self.listInterfaces()
        self.listPeers()

    def createBirdConf_BGP(self):
        """!Get Bird's BGP config.

        @param self The object pointer.
        @returns str Part of bird.conf."""
        area_0_entries = ""
        # generate the BGP entry for each interface
        entries = FileTemplate.birdConf_common
        (net_name, my_ip) = self.interfaces[0]
        for peer_name in self.peers:
            peer = self.simulator.getRouter(peer_name)
            if peer:
                peer_ip = peer.getIP_on_IXP_Network()
                peer_as = peer.getASN()
            entries += FileTemplate.birdConf_BGP_RS.format(
                my_ip, self.ixp, peer_ip, peer_as)
            entries += '\n'

        return entries


# For BGP router
class BGPRouter(Router):
    """!BGPRouter class

    This class represents a BGP router node in the simulation."""
    def __init__(self, name: str, asn: int, ixp: int, sim):
        """!BGPRouter constructor

        @param self The object pointer.
        @param name The name of this BGPRouter.
        @param asn The ASN of this BGPRouter.
        @param ixp The ASN of IXP this BGPRouter belongs to.
        @param sim Reference to the parent simulator object.
        """
        self.name = name
        self.asn = asn
        self.ixp = ixp
        self.simulator = sim
        self.type = 'as'

        self.interfaces = []  # 0: for internal network, 1: for IXP network
        self.peers = set()   # Set of peers (names)

    def getIP_on_IXP_Network(self):
        """!Get IP address on the IX peering LAN.

        @param self The object pointer.
        @returns str IP address.
        """
        (network, ip) = self.interfaces[1]
        return ip

    def getIP_on_Internal_Network(self):
        """!Get IP address on the internal LAN.

        @param self The object pointer.
        @returns str IP address.
        """
        (network, ip) = self.interfaces[0]
        return ip

    def getASN(self):
        """!Get ASN.

        @param self The object pointer.
        @returns int ASN.
        """
        return self.asn

    def getType(self):
        """!Get type of the BGPRouter.

        @param self The object pointer.
        @returns str type.
        """
        return self.type

    def initializeNetwork(self):
        """!Create the internal LAN.

        @param self The object pointer.
        """
        # Initialize the interface
        net_name = SimConstants.ASNETNAME.format(self.asn)
        net = self.simulator.getNetwork(net_name)
        if net:
            ip = net.getIP(router=True, bgp=True)
            self.addInterface(net_name, ip)

        net_name = SimConstants.IXNETNAME.format(self.ixp)
        net = self.simulator.getNetwork(net_name)
        if net:
            ip = net.getIPByASN(self.asn)
            self.addInterface(net_name, ip)

    # Add peer name
    def addPeer(self, peername):
        """!Add a peer.

        @param self The object pointer.
        @param peername The name of the peer AS.
        """

        self.peers.add(peername)

    def listPeers(self):
        """!Print the list of peers to stdout.

        @param self The object pointer."""
        print("  Peers:")
        for peer in self.peers:
            print("      ", peer)

    def printDetails(self):
        """!Print the details to stdout.

        @param self The object pointer."""
        print(self.name)
        self.listInterfaces()
        self.listPeers()

    def createBirdConf_BGP(self):
        """!Get Bird's BGP config.

        @param self The object pointer.
        @returns str Part of bird.conf."""
        # generate the BGP entry for each interface
        entries = FileTemplate.birdConf_common
        my_ip = self.getIP_on_IXP_Network()
        for peer_name in self.peers:
            peer = self.simulator.getRouter(peer_name)
            if peer:
                peer_ip = peer.getIP_on_IXP_Network()
                peer_as = peer.getASN()
            entries += FileTemplate.birdConf_BGP.format(
                my_ip, self.asn, peer_ip, peer_as)
            entries += '\n'

        return entries

    # From the AS object, get the list of BGP routers (names) for this AS
    # Add each of them (except itself) as a IBGP peer
    def createBirdConf_IBGP(self):
        """!Get Bird's IBGP config.

        @param self The object pointer.
        @returns str Part of bird.conf."""
        entries = ""
        my_ip = self.getIP_on_Internal_Network()
        as_obj = self.simulator.getASByName(
            SimConstants.ASNAME.format(self.asn))

        routers = as_obj.getBGPRouters()  # Return a list of router names
        if len(routers) < 2:
            return entries  # This AS has only one BGP router, no need to add IBGP

        entries += FileTemplate.birdConf_OSPF

        # Add each router (except itself) as IBGP peer (full mesh)
        for router in routers:
            if router == self.name:
                continue    # Skip itself

            router_obj = self.simulator.getRouter(router)
            peer_ip = router_obj.getIP_on_Internal_Network()
            entries += FileTemplate.birdConf_IBGP.format(
                my_ip, self.asn, peer_ip, self.asn)
            entries += "\n"

        return entries
