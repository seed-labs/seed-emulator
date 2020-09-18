"""Internet Simulator Network."""

import os
import csv

from .constants import *


class Network:
    """!Network class
    
    This class represents a network in the simulation."""

    HOST_IP_START = 71
    HOST_IP_END = 99
    RT_IP_START = 41
    RT_IP_END = 69
    RT_BGP_START = 254
    RT_BGP_END = 200

    def __init__(self, name: str, prefix: str, netmask: str, type: str, simulator):
        """!Network constructor

        @param self The object pointer.
        @param prefix The prefix of this Network.
        @param netmask The mask (CIDR) of this Network.
        @param type The type of this Network.
        @param simulator Reference to the parent simulator object.
        """

        self.name = name
        self.prefix = prefix
        self.netmask = str(netmask)
        self.type = type
        self.next_hostip = self.HOST_IP_START
        self.next_routerip = self.RT_IP_START
        self.next_bgpip = self.RT_BGP_START

        # remember the simulator it belongs to
        self.simulator = simulator

        # Set the default router on this network (use the 1st one)
        rt = prefix.split('.')
        rt[3] = str(self.RT_BGP_START)
        self.default_router = '.'.join(rt)

    # Assign IP addresses based on ASN. This one is used to
    # assign IP addresses to BGP routers on the IXP network
    def getIPByASN(self, asn: int):
        """!Assign IP addresses based on ASN.
        
        This one is used to assign IP addresses to BGP routers on the IXP
        network.

        @param self The object pointer.
        @param asn ASN.
        @returns str IP address.
        """
        #assert asn < 255
        ip_in_list = self.prefix.split('.')
        ip_in_list[3] = asn
        return '.'.join(ip_in_list)

    def getIP(self, router=False, bgp=False):
        """!Get IP address by type

        @param self The object pointer.
        @param router Is this IP for internal router?
        @param bgp Is this IP for BGP router?
        @returns str IP address.
        """
        ip_in_list = self.prefix.split('.')
        if bgp:  # For BGP routers
            ip_addr = self.next_bgpip
            ip_in_list[3] = str(ip_addr)
            assert ip_addr >= self.RT_BGP_END
            self.next_bgpip -= 1
            return '.'.join(ip_in_list)
        elif router:  # For internal Routers
            ip_addr = self.next_routerip
            ip_in_list[3] = str(ip_addr)
            assert ip_addr <= self.RT_IP_END
            self.next_routerip += 1
            return '.'.join(ip_in_list)
        else:  # For hosts
            ip_addr = self.next_hostip
            ip_in_list[3] = str(ip_addr)
            assert ip_addr <= self.HOST_IP_END
            self.next_hostip += 1
            return '.'.join(ip_in_list)

    def getDefaultRT(self):
        """!Get the router in this network.

        @param self The object pointer.
        @returns str IP address.
        """
        return self.default_router

    def createDockerComposeEntry(self):
        """!Get the docker compose file as string

        @param self The object pointer.
        @returns str Part of docker-compose.yml
        """
        template = FileTemplate.docker_compose_network_entry
        result = template.format(self.name, self.prefix, self.netmask)
        return result

    def printDetails(self):
        """!Print the details to stdout.

        @param self The object pointer."""
        print("Name: {} -- Network: {} -- Netmask: {}".format(self.name,
                                                              self.prefix, self.netmask))
