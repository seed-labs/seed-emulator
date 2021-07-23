from seedemu.layers import Base, Routing, Ebgp
from seedemu.services import WebService
from seedemu.compiler import Docker
from seedemu.core import Emulator, Binding, Filter, Action

###############################################################################
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
# Create and set up AS150

as150 = base.createAutonomousSystem(150)
as150.createNetwork('net0')
as150.createRouter('router0').joinNetwork('net0').joinNetwork('ix100')

###############################################################################
# Create and set up AS151

as151 = base.createAutonomousSystem(151)
as151.createNetwork('net0')
as151.createRouter('router0').joinNetwork('net0').joinNetwork('ix100')

###############################################################################
# Create and set up AS-152

as152 = base.createAutonomousSystem(152)
as152.createNetwork('net0')
as152.createRouter('router0').joinNetwork('net0').joinNetwork('ix100')

###############################################################################
# Peering these ASes at Internet Exchange IX-100

ebgp.addRsPeer(100, 150)
ebgp.addRsPeer(100, 151)
ebgp.addRsPeer(100, 152)

###############################################################################
# Create some virtual nodes for web services

web.install('w150')
web.install('w151')
web.install('w152')

###############################################################################
# Creating bindings with NEW action (creates physical node automatically,
# instead of looking for physical node matching the filter)

# create physical node in AS150, with name 'web'
emu.addBinding(Binding('w150', filter = Filter(nodeName = 'web', asn = 150), action = Action.NEW))

# create physical node in AS150, with random name
emu.addBinding(Binding('w151', filter = Filter(asn = 151), action = Action.NEW))

# create physical node with address 10.152.0.71. (since 10.152.0.71 is in AS152, the node will be in AS152)
emu.addBinding(Binding('w152', filter = Filter(ip = '10.152.0.71'), action = Action.NEW))

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
