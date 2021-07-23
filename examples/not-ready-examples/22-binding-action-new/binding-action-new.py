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
# Create and set up AS150 to AS155

for asn in range(150, 155):
    asObject = base.createAutonomousSystem(asn)
    asObject.createNetwork('net0')
    asObject.createRouter('router0').joinNetwork('net0').joinNetwork('ix100')
    ebgp.addRsPeer(100, asn)

###############################################################################
# Create some virtual nodes for web services

for asn in range(150, 155):
    web.install('w{}'.format(asn))

###############################################################################
# Creating bindings with NEW action (creates physical node automatically,
# instead of looking for physical node matching the filter)

# create physical node in AS150, with name 'web'
emu.addBinding(Binding('w150', filter = Filter(nodeName = 'web', asn = 150), action = Action.NEW))

# create physical node in AS150, with random name
emu.addBinding(Binding('w151', filter = Filter(asn = 151), action = Action.NEW))

# create physical node with address 10.152.0.71. (since 10.152.0.71 is in AS152, the node will be in AS152)
emu.addBinding(Binding('w152', filter = Filter(ip = '10.152.0.81'), action = Action.NEW))

# create physical node for the rest of nodes in randomly picked AS, with random nodeName/IP/net.
emu.addBinding(Binding('w.*', action = Action.NEW))

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
