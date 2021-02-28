from seedsim import mergers
from seedsim.core import Simulator
from seedsim.mergers import DefaultBaseMerger
from seedsim.layers import Base

###############################################################################

baseA = Base()

baseA.createInternetExchange(100)

as150 = baseA.createAutonomousSystem(150)

h150 = as150.createHost('host0')
r150 = as150.createRouter('router0')
as150.createNetwork('net0')

h150.joinNetwork('net0')
r150.joinNetwork('net0')
r150.joinNetwork('ix100')

simA = Simulator()
simA.addLayer(baseA)

###############################################################################

baseB = Base()

as151 = baseB.createAutonomousSystem(151)

h151 = as151.createHost('host0')
r151 = as151.createRouter('router0')
as151.createNetwork('net0')

h151.joinNetwork('net0')
r151.joinNetwork('net0')
r151.joinNetwork('ix100')

simB = Simulator()
simB.addLayer(baseB)

###############################################################################

merged = simA.merge(simB, [DefaultBaseMerger()])

print('A ==========')
print(simA.getRegistry())

print('B ==========')
print(simB.getRegistry())

print('Merged =====')
print(merged.getRegistry())
