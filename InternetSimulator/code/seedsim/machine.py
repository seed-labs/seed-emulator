import os
import csv

from .constants import *


####################################
# The Machine class: base class
####################################
class Machine:
   def __init__(self, name):
       self.name = name

   def getName(self):
       return self.name


####################################
# The Host class
####################################
class Host(Machine):
   def __init__(self, name, network, ip, simulator): 
       self.name = name
       self.network =  network
       self.ip = ip

       # remember the simulator it belongs to 
       self.simulator = simulator

   def printDetails(self):
       print(self.name)
       print("   ", self.network, self.ip)

   def createStartScript(self):
       network = self.simulator.getNetwork(self.network)
       router  = network.getDefaultRT() 
       content = FileTemplate.hostStartScript.format(router)
       return content

   def createDockerComposeEntry(self):
       entry = FileTemplate.docker_compose_host_entry
       result = entry.format(self.name, "./" + self.name, 
                             self.network, self.ip) 

       return result


####################################
# The Router class
####################################
class Router(Machine): 
   def __init__(self, name, sim): 
       self.name = name
       self.interfaces = []

       # remember the simulator it belongs to 
       self.simulator = sim


   def printDetails(self):
       print(self.name)
       self.listInterfaces()

   def listInterfaces(self):
       print("  Interfaces:")
       for (name, ip) in self.interfaces:
           print("     ", name, ip)

   def addInterface(self, name, ip):
       self.interfaces.append((name, ip))
        

   def createBirdConf_OSPF(self):
       # generate the OSPF entry for each interface  
       area_0_entries = ""
       for i in range(len(self.interfaces)):
          ifn = 'eth' + str(i)
          area_0_entries += ' '*8 + "interface \"{}\" {{}};\n".format(ifn)

       return FileTemplate.birdConf_OSPF.format(area_0_entries)

   def createDockerComposeEntry(self):
       net_entries =''
       for f in self.interfaces:
           template = FileTemplate.docker_compose_interface_entry
           net_entries += template.format(f[0], f[1]) +"\n"

       entry = FileTemplate.docker_compose_router_entry
       result = entry.format(self.name, "./" + self.name, 
                             net_entries)

       return result


 
# For route server
class RouteServer(Router): 
   def __init__(self, name, ixp, sim): 
       self.name = name
       self.ixp  = ixp
       self.type = 'rs'
       self.simulator  = sim
       self.peers = set()    # Set of peers (names)
       self.interfaces = []  # Suppose to have only one interace


   def getIP_on_IXP_Network(self):
       (network, ip) = self.interfaces[0]
       return ip

   def getASN(self):
       return self.ixp

   def getType(self):
       return self.type

   def addPeer(self, peername):
       self.peers.add(peername)

   def initializeNetwork(self):
       net_name = SimConstants.IXNETNAME.format(self.ixp)
       net = self.simulator.getNetwork(net_name)
       if net:
          ip = net.getIPByASN(self.ixp)
          self.addInterface(net_name, ip)

   def listPeers(self):
       print("  Peers:")
       for peer in self.peers:
           print("     ", peer)

   def printDetails(self):
       print(self.name)
       self.listInterfaces()
       self.listPeers()


   def createBirdConf_BGP(self):
       # generate the BGP entry for each interface  
       entries = FileTemplate.birdConf_common
       (net_name, my_ip) = self.interfaces[0]
       for peer_name in self.peers:
           peer = self.simulator.getRouter(peer_name)
           if peer:
               peer_ip = peer.getIP_on_IXP_Network()
               peer_as = peer.getASN()
           entries += FileTemplate.birdConf_BGP_RS.format(my_ip, self.ixp, peer_ip, peer_as)
           entries += '\n'

       return entries


# For BGP router
class BGPRouter(Router): 
   def __init__(self, name, asn, ixp, sim): 
       self.name = name
       self.asn  = asn
       self.ixp  = ixp
       self.simulator = sim
       self.type = 'as'

       self.interfaces = [] # 0: for internal network, 1: for IXP network
       self.peers = set()   # Set of peers (names)

   def getIP_on_IXP_Network(self):
       (network, ip) = self.interfaces[1]
       return ip

   def getIP_on_Internal_Network(self):
       (network, ip) = self.interfaces[0]
       return ip

   def getASN(self):
       return self.asn

   def getType(self):
       return self.type

   def initializeNetwork(self):
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
       self.peers.add(peername)

   def listPeers(self):
       print("  Peers:")
       for peer in self.peers:
           print("      ", peer)

   def printDetails(self):
       print(self.name)
       self.listInterfaces()
       self.listPeers()

   def createBirdConf_BGP(self):
       # generate the BGP entry for each interface  
       entries = FileTemplate.birdConf_common
       my_ip = self.getIP_on_IXP_Network()
       for peer_name in self.peers:
           peer = self.simulator.getRouter(peer_name)
           if peer:
               peer_ip = peer.getIP_on_IXP_Network()
               peer_as = peer.getASN()
           entries += FileTemplate.birdConf_BGP.format(my_ip, self.asn, peer_ip, peer_as)
           entries += '\n'

       return entries

   # From the AS object, get the list of BGP routers (names) for this AS
   # Add each of them (except itself) as a IBGP peer
   def createBirdConf_IBGP(self):
       entries = ""
       my_ip  = self.getIP_on_Internal_Network()
       as_obj = self.simulator.getASByName(SimConstants.ASNAME.format(self.asn))

       routers = as_obj.getBGPRouters() # Return a list of router names
       if len(routers) < 2: 
           return entries  # This AS has only one BGP router, no need to add IBGP 

       entries += FileTemplate.birdConf_OSPF

       for router in routers:  # Add each router (except itself) as IBGP peer (full mesh)
           if router == self.name: 
               continue    # Skip itself 

           router_obj = self.simulator.getRouter(router)
           peer_ip = router_obj.getIP_on_Internal_Network()
           entries += FileTemplate.birdConf_IBGP.format(my_ip, self.asn, peer_ip, self.asn)  
           entries += "\n"

       return entries

