from seedsim.layers import Base, Routing, Ebgp, PeerRelationship, Ibgp, Ospf, WebService, Mpls
from seedsim.core import Simulator
from seedsim.compiler import Docker

sim = Simulator()

base = Base()
routing = Routing()
ebgp = Ebgp()
mpls = Mpls()
web = WebService()

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

mpls.enableOn(150)

###############################################################################

as151 = base.createAutonomousSystem(151)

as151_web = as151.createHost('web')
web.installByName(151, 'web')

as151_router = as151.createRouter('router0')

as151_net = as151.createNetwork('net0')

routing.addDirect(151, 'net0')

as151_web.joinNetwork('net0')
as151_router.joinNetwork('net0')

as151_router.joinNetwork('ix100')

###############################################################################

as152 = base.createAutonomousSystem(152)

as152_web = as152.createHost('web')
web.installByName(152, 'web')

as152_router = as152.createRouter('router0')

as152_net = as152.createNetwork('net0')

routing.addDirect(152, 'net0')

as152_web.joinNetwork('net0')
as152_router.joinNetwork('net0')

as152_router.joinNetwork('ix101')

###############################################################################

ebgp.addPrivatePeering(100, 150, 151, abRelationship = PeerRelationship.Provider)
ebgp.addPrivatePeering(101, 150, 152, abRelationship = PeerRelationship.Provider)

###############################################################################

sim.addLayer(base)
sim.addLayer(routing)
sim.addLayer(ebgp)
sim.addLayer(mpls)
sim.addLayer(web)

sim.render()

###############################################################################

sim.compile(Docker(), './transit-as-mpls')