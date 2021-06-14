from seedemu.core import Emulator
from seedemu.mergers import DEFAULT_MERGERS
from seedemu.layers import Base, Routing, Ebgp
from seedemu.compiler import Docker

###############################################################################

baseA = Base()
ebgpA = Ebgp()
routingA = Routing()

baseA.createInternetExchange(100)

as150 = baseA.createAutonomousSystem(150)

h150 = as150.createHost('host0')
r150 = as150.createRouter('router0')
as150.createNetwork('net0')

routingA.addDirect(150, 'net0')

h150.joinNetwork('net0')
r150.joinNetwork('net0')
r150.joinNetwork('ix100')

ebgpA.addRsPeer(100, 150)

simA = Emulator()
simA.addLayer(baseA)
simA.addLayer(routingA)
simA.addLayer(ebgpA)

###############################################################################

baseB = Base()
ebgpB = Ebgp()
routingB = Routing()

as151 = baseB.createAutonomousSystem(151)

h151 = as151.createHost('host0')
r151 = as151.createRouter('router0')
as151.createNetwork('net0')

routingB.addDirect(151, 'net0')

h151.joinNetwork('net0')
r151.joinNetwork('net0')
r151.joinNetwork('ix100')

ebgpB.addRsPeer(100, 151)

simB = Emulator()
simB.addLayer(baseB)
simB.addLayer(routingB)
simB.addLayer(ebgpB)

###############################################################################

merged = simA.merge(simB, DEFAULT_MERGERS)

print('A ==========')
print(simA.getRegistry())

print('B ==========')
print(simB.getRegistry())

print('Merged =====')
print(merged.getRegistry())

###############################################################################

merged.render()

###############################################################################

merged.compile(Docker(), './merge')
