import os
import csv

from .constants import *

class Network:
   HOST_IP_START = 71
   HOST_IP_END   = 99  
   RT_IP_START   = 41
   RT_IP_END     = 69
   RT_BGP_START   = 254
   RT_BGP_END     = 200
   
   def __init__(self, name, prefix, netmask, type, simulator):
       self.name    = name
       self.prefix  = prefix
       self.netmask = str(netmask)
       self.type = type
       self.next_hostip   = self.HOST_IP_START
       self.next_routerip = self.RT_IP_START
       self.next_bgpip    = self.RT_BGP_START

       # remember the simulator it belongs to 
       self.simulator = simulator

       # Set the default router on this network (use the 1st one)
       rt = prefix.split('.')
       rt[3] = str(self.RT_BGP_START)
       self.default_router = '.'.join(rt) 

   # Assign IP addresses based on ASN. This one is used to
   # assign IP addresses to BGP routers on the IXP network
   def getIPByASN(self, asn):
       #assert asn < 255
       ip_in_list = self.prefix.split('.')
       ip_in_list[3] = asn
       return '.'.join(ip_in_list)



   def getIP(self, router=False, bgp=False):
       ip_in_list = self.prefix.split('.')
       if bgp:  # For BGP routers
           ip_addr = self.next_bgpip
           ip_in_list[3] = str(ip_addr)
           assert ip_addr >= self.RT_BGP_END
           self.next_bgpip -= 1
           return '.'.join(ip_in_list)
       elif router: # For internal Routers
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
       return self.default_router

   def createDockerComposeEntry(self):
       template = FileTemplate.docker_compose_network_entry
       result = template.format(self.name, self.prefix, self.netmask)
       return result

   def printDetails(self):
       print("Name: {} -- Network: {} -- Netmask: {}".format(self.name,\
               self.prefix, self.netmask))


