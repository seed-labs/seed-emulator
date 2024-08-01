#!/usr/bin/env python3
# encoding: utf-8

from seedemu import *
import random
from examples.internet.B00_mini_internet import mini_internet
import os, sys

###############################################################################
script_name = os.path.basename(__file__)

if len(sys.argv) == 1:
   platform = Platform.AMD64
elif len(sys.argv) == 2:
   if sys.argv[1].lower() == 'amd':
         platform = Platform.AMD64
   elif sys.argv[1].lower() == 'arm':
         platform = Platform.ARM64
   else:
         print(f"Usage:  {script_name} amd|arm")
         sys.exit(1)
else:
   print(f"Usage:  {script_name} amd|arm")
   sys.exit(1)

mini_internet.run(dumpfile='./base_internet.bin')

emu = Emulator()

# Load the base layer from the mini Internet example
emu.load('./base_internet.bin')


#################################################################
# Create a secret web server. We will use Tor to protect its location

# The following content will be put inside the protected web server
html = """
<html><body>
<h1>This is the secret web server!</h1>
</body></html>
"""

# Create a web server: we will use Tor to protect this server
web = WebService()
web.install("webserver")
emu.getVirtualNode('webserver').setDisplayName('Tor-webserver') \
        .setFile(content=html, path="/var/www/html/hello.html")

#################################################################
# Create a Tor component

# Create the Tor service layer
tor = TorService()

# Different types of Tor nodes (virtual nodes)
vnodes = {
   "da-1":     TorNodeType.DA,
   "da-2":     TorNodeType.DA,
   "da-3":     TorNodeType.DA,
   "da-4":     TorNodeType.DA,
   "da-5":     TorNodeType.DA,
   "client-1": TorNodeType.CLIENT,
   "client-2": TorNodeType.CLIENT,
   "relay-1":  TorNodeType.RELAY,
   "relay-2":  TorNodeType.RELAY,
   "relay-3":  TorNodeType.RELAY,
   "relay-4":  TorNodeType.RELAY,
   "exit-1":   TorNodeType.EXIT,
   "exit-2":   TorNodeType.EXIT,
   "hidden-service": TorNodeType.HS
}

# Create the virtual nodes
for i, (name, nodeType) in enumerate(vnodes.items()):
   if nodeType == TorNodeType.HS: 
      tor.install(name).setRole(nodeType).linkByVnode("webserver", 80)
   else:
      tor.install(name).setRole(nodeType)

   # Customize the display names.
   emu.getVirtualNode(name).setDisplayName("Tor-{}".format(name))
    


#################################################################
# Bind virtual nodes to physical nodes

as_list = [150, 151, 152, 153, 154, 160, 161, 162, 163, 164, 170, 171]
for i, (name, nodeType) in enumerate(vnodes.items()):
    # Pick an autonomous system randomly from the list,
    # and create a new host for each Tor node
    asn = random.choice(as_list)
    emu.addBinding(Binding(name, filter=Filter(asn=asn), action=Action.NEW))

# Bind the web server node to a physical node
emu.addBinding(Binding("webserver", filter=Filter(asn=170), action=Action.NEW))


#################################################################
emu.addLayer(web)
emu.addLayer(tor)
emu.render()
emu.compile(Docker(platform=platform), './output', override=True)
