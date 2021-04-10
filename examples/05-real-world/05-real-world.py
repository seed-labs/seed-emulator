from seedsim.layers import Base, Routing, Ebgp, PeerRelationship, Ibgp, Ospf, Reality
from seedsim.services import WebService
from seedsim.core import Simulator, Binding, Filter
from seedsim.compiler import Docker

sim = Simulator()

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

as151 = base.createAutonomousSystem(151)

as151_web = as151.createHost('web')

as151_router = as151.createRouter('router0')

as151_net = as151.createNetwork('net0')

routing.addDirect(151, 'net0')
real.enableRealWorldAccess(as151, 'net0')

as151_web.joinNetwork('net0')
as151_router.joinNetwork('net0')

as151_router.joinNetwork('ix100')

###############################################################################

as152 = base.createAutonomousSystem(152)

as152_web = as152.createHost('web')

as152_router = as152.createRouter('router0')

as152_net = as152.createNetwork('net0')

routing.addDirect(152, 'net0')
real.enableRealWorldAccess(as152, 'net0')

as152_web.joinNetwork('net0')
as152_router.joinNetwork('net0')

as152_router.joinNetwork('ix101')

###############################################################################

as11872 = base.createAutonomousSystem(11872)
as11872_router = real.createRealWorldRouter(as11872)

as11872_router.joinNetwork('ix101', '10.101.0.118')

###############################################################################

ebgp.addPrivatePeering(100, 150, 151, abRelationship = PeerRelationship.Provider)
ebgp.addPrivatePeering(101, 150, 152, abRelationship = PeerRelationship.Provider)
ebgp.addPrivatePeering(101, 150, 11872, abRelationship = PeerRelationship.Unfiltered)

###############################################################################

web.install('web1')
web.install('web2')

###############################################################################

sim.addBinding(Binding('web1', filter = Filter(asn = 151, nodeName = 'web')))
sim.addBinding(Binding('web2', filter = Filter(asn = 152, nodeName = 'web')))

###############################################################################

sim.addLayer(base)
sim.addLayer(routing)
sim.addLayer(ebgp)
sim.addLayer(ibgp)
sim.addLayer(ospf)
sim.addLayer(web)
sim.addLayer(real)

sim.render()

###############################################################################

sim.compile(Docker(selfManagedNetwork = True), './real-world')