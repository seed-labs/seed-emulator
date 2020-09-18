import os
import csv

from .constants import *


class AS:
    """!Autonomous System

    This class represents an AS in the simulation."""

    def __init__(self, name: str, asn: int, as_type: str, net_name: str, simulator):
        """!Autonomous System constructor

        @param self The object pointer.
        @param name The name of this AS.
        @param as_type The type of this AS.
        @param net_name The name of the AS internal network.
        @param simulator Reference to the parent simulator object."""

        self.__name = name
        self.__asn = asn
        self.__network = net_name   # Use network name
        self.__type = as_type
        self.__simulator = simulator
        # Set of AS peers, each peer is a pair (peer name, location: ixp name)
        self.__peers = set()
        self.__bgprouters = set()  # Set of BGP routers (name) in this AS

    # Add (AS IX) to the peer list: self peers with AS at IX
    def addPeer(self, as_name: str, ix_name: str):
        """!Add a peer.

        @param self The object pointer.
        @param as_name The name of the perr AS.
        @param ix_name The name of the IX to establish this peering."""

        self.__peers.add((as_name, ix_name))

    def printDetails(self):
        """!Print the details to stdout.

        @param self The object pointer."""
        print("Name: {} -- Network: {} -- Type: {}".format(self.__name,
                                                           self.__network, self.__type))

    def getBGPRouters(self):
        """!Get the set of BGP routers.

        @param self The object pointer."""
        return self.__bgprouters

    def addBGPRouter(self, router_name: str):
        """!Add a new BGP router.

        @param self The object pointer.
        @router_name The name of the new router."""
        self.__bgprouters.add(router_name)

    # Future work: we can generate dot files using self.__peers
    def generateDotFile(self):
        """!Generate Graphviz dot file for this AS.

        @todo not yet implemented.

        @param self The object pointer."""
        pass


class IXP:
    """!Internet Exchange Point

    This class represents an IXP in the simulation."""

    def __init__(self, name: str, asn: int, net_name: str, simulator):
        """!Internet Exchange Point constructor

        @param self The object pointer.
        @param name The name of this IXP.
        @param net_name The name of the IXP network.
        @param simulator Reference to the parent simulator object."""

        self.__name = name
        self.__asn = asn
        self.__net_name = net_name    # Use network name
        self.__simulator = simulator
        self.__bgp_routers = set()    # Routers (names) in this IXP
        self.__type = 'IX'

    # Add Router to the list using router name
    def addBGPRouter(self, router_name: str):
        """!Add a BGP router to this IX.

        @param self The object pointer.
        @param name The name of the router."""
        self.__bgp_routers.add(router_name)

    def printDetails(self):
        """!Print the details to stdout.

        @param self The object pointer."""
        print("Name: {} -- Network: {} -- Type: {}".format(self.__name,
                                                           self.__net_name, self.__type))
