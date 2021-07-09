from seedemu.layers import Base, Routing, Ebgp, PeerRelationship, Ibgp, Ospf, Reality
from seedemu.services import WebService
from seedemu.core import Emulator, Binding, Filter
from seedemu.compiler import Docker

emu = Emulator()

base = Base()
routing = Routing()
ebgp = Ebgp()
ibgp = Ibgp()
ospf = Ospf()
web = WebService()
real = Reality()

###############################################################################

base.createInternetExchange(100)
base.createInternetExchange(101)

###############################################################################

as150 = base.createAutonomousSystem(150)

as150.createNetwork('net0')
as150.createNetwork('net1')
as150.createNetwork('net2')

r1 = as150.createRouter('r1')
r2 = as150.createRouter('r2')
r3 = as150.createRouter('r3')
r4 = as150.createRouter('r4')

r1.joinNetwork('ix100')
r1.joinNetwork('net0')

r2.joinNetwork('net0')
r2.joinNetwork('net1')

r3.joinNetwork('net1')
r3.joinNetwork('net2')

r4.joinNetwork('net2')
r4.joinNetwork('ix101')

###############################################################################
# Create AS151

as151 = base.createAutonomousSystem(151)
as151.createNetwork('net0')


as151.createHost('web').joinNetwork('net0')

as151_router = as151.createRouter('router0')
as151_router.joinNetwork('net0')
as151_router.joinNetwork('ix100')

# Enable the access from machines outside of the emulator
real.enableRealWorldAccess(as151, 'net0')

###############################################################################
# Create AS152

as152 = base.createAutonomousSystem(152)
as152.createNetwork('net0')


as152.createHost('web').joinNetwork('net0')

as152_router = as152.createRouter('router0')
as152_router.joinNetwork('net0')
as152_router.joinNetwork('ix101')

# Enable the access from machines outside of the emulator
real.enableRealWorldAccess(as152, 'net0')


###############################################################################
# Create a real-world AS

as11872 = base.createAutonomousSystem(11872)
as11872_router = real.createRealWorldRouter(as11872)
as11872_router.joinNetwork('ix101', '10.101.0.118')

###############################################################################
# BGP peering 

ebgp.addPrivatePeering(100, 150, 151, abRelationship = PeerRelationship.Provider)
ebgp.addPrivatePeering(101, 150, 152, abRelationship = PeerRelationship.Provider)
ebgp.addPrivatePeering(101, 150, 11872, abRelationship = PeerRelationship.Unfiltered)

###############################################################################
# Create two virtual nodes and bind them to physical nodes

web.install('web1')
web.install('web2')

emu.addBinding(Binding('web1', filter = Filter(asn = 151, nodeName = 'web')))
emu.addBinding(Binding('web2', filter = Filter(asn = 152, nodeName = 'web')))

###############################################################################
# Rendering

emu.addLayer(base)
emu.addLayer(routing)
emu.addLayer(ebgp)
emu.addLayer(ibgp)
emu.addLayer(ospf)
emu.addLayer(web)
emu.addLayer(real)

emu.render()

###############################################################################
# Compilation 

emu.compile(Docker(), './output')
