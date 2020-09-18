import os
import csv

from .constants import *

# AS class
class AS:
   def __init__(self, name, asn, as_type, net_name, simulator):
       self.name = name
       self.asn  = asn
       self.network  = net_name   # Use network name
       self.type = as_type
       self.simulator = simulator
       self.peers = set()       # Set of AS peers, each peer is a pair (peer name, location: ixp name)
       self.bgprouters = set()  # Set of BGP routers (name) in this AS
       

   # Add (AS IX) to the peer list: self peers with AS at IX 
   def addPeer(self, as_name, ix_name):
       self.peers.add((as_name, ix_name))

   def printDetails(self):
       print("Name: {} -- Network: {} -- Type: {}".format(self.name,\
               self.network, self.type))

   def getBGPRouters(self):
       return self.bgprouters

   def addBGPRouter(self, router_name):
       self.bgprouters.add(router_name)

   # Future work: we can generate dot files using self.peers 
   def generateDotFile(self):
       pass 

class IXP:
   def __init__(self, name, asn, network, simulator):
       self.name = name
       self.asn  = asn
       self.network  = network    # Use network name
       self.simulator = simulator
       self.bgp_routers = set()    # Routers (names) in this IXP
       self.type = 'IX'

   # Add Router to the list using router name
   def addBGPRouter(self, router_name):
        self.bgp_routers.add(router_name)

   def printDetails(self):
       print("Name: {} -- Network: {} -- Type: {}".format(self.name,\
               self.network, self.type))

