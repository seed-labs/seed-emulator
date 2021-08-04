#!/usr/bin/env python3
# encoding: utf-8

from seedemu.layers import Base, Routing, Ebgp
from seedemu.services import WebService
from seedemu.compiler import Docker
from seedemu.core import Emulator, Binding, Filter


# Initialize the emulator and layers
emu     = Emulator()
base    = Base()
routing = Routing()
ebgp    = Ebgp()
web     = WebService()

###############################################################################
# Create an Internet Exchange
base.createInternetExchange(100)

###############################################################################
# Create and set up AS-150

# Create an autonomous system 
as150 = base.createAutonomousSystem(150)

# Create a network 
as150.createNetwork('net0')

# Create a router and connect it to two networks
as150.createRouter('router0').joinNetwork('net0').joinNetwork('ix100')

# Create a host called web and connect it to a network
as150.createHost('web').joinNetwork('net0')

# Create a web service on virtual node, give it a name
# This will install the web service on this virtual node
web.install('web150')

# Bind the virtual node to a physical node 
emu.addBinding(Binding('web150', filter = Filter(nodeName = 'web', asn = 150)))


###############################################################################
# Create and set up AS-151
# It is similar to what is done to AS-150

as151 = base.createAutonomousSystem(151)
as151.createNetwork('net0')
as151.createRouter('router0').joinNetwork('net0').joinNetwork('ix100')

as151.createHost('web').joinNetwork('net0')
web.install('web151')
emu.addBinding(Binding('web151', filter = Filter(nodeName = 'web', asn = 151)))

###############################################################################
# Create and set up AS-152
# It is similar to what is done to AS-150

as152 = base.createAutonomousSystem(152)
as152.createNetwork('net0')
as152.createRouter('router0').joinNetwork('net0').joinNetwork('ix100')

as152.createHost('web').joinNetwork('net0')
web.install('web152')
emu.addBinding(Binding('web152', filter = Filter(nodeName = 'web', asn = 152)))


###############################################################################
# Peering these ASes at Internet Exchange IX-100

ebgp.addRsPeer(100, 150)
ebgp.addRsPeer(100, 151)
ebgp.addRsPeer(100, 152)

###############################################################################
# the above are from A00-simple-peering

emu.getVirtualNode('web152').setDisplayName('Web server in AS152')
emu.getVirtualNode('web151').setFile('/var/www/html/hello.txt', 'hello from web151')

emu.getVirtualNode('web150').addSoftware('cowsay')
emu.getVirtualNode('web150').appendStartCommand('export PATH=$PATH:/usr/games')
emu.getVirtualNode('web150').appendStartCommand('echo "Adding start command and installing new software is also possible." | cowsay')

# the below are from A00-simple-peering
###############################################################################


###############################################################################
# Rendering 

emu.addLayer(base)
emu.addLayer(routing)
emu.addLayer(ebgp)
emu.addLayer(web)

emu.render()

###############################################################################
# Compilation

emu.compile(Docker(), './output')
