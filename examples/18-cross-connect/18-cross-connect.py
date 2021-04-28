from seedsim.layers import Base, Routing, Ebgp, PeerRelationship
from seedsim.services import WebService
from seedsim.compiler import Docker
from seedsim.core import Simulator, Binding, Filter

sim = Simulator()

base = Base()
routing = Routing()
ebgp = Ebgp()
web = WebService()

###############################################################################

base.createInternetExchange(100)

###############################################################################

as150 = base.createAutonomousSystem(150)

as150_web = as150.createHost('web')

web.install('web150')
sim.addBinding(Binding('web150', filter = Filter(asn = 150, nodeName = 'web')))

as150_router = as150.createRouter('router0')
as150_net = as150.createNetwork('net0')

routing.addDirect(150, 'net0')

as150_web.joinNetwork('net0')
as150_router.joinNetwork('net0')

as150_router.joinNetwork('ix100')

as150_router.crossConnect(152, 'router0', '10.50.0.1/30')

###############################################################################

as151 = base.createAutonomousSystem(151)

as151_web = as151.createHost('web')

web.install('web151')
sim.addBinding(Binding('web151', filter = Filter(asn = 151, nodeName = 'web')))

as151_router = as151.createRouter('router0')

as151_net = as151.createNetwork('net0')

routing.addDirect(151, 'net0')

as151_web.joinNetwork('net0')
as151_router.joinNetwork('net0')

as151_router.joinNetwork('ix100')

###############################################################################

as152 = base.createAutonomousSystem(152)

as152_web = as152.createHost('web')

web.install('web152')
sim.addBinding(Binding('web152', filter = Filter(asn = 152, nodeName = 'web')))

as152_router = as152.createRouter('router0')

as152_net = as152.createNetwork('net0')

routing.addDirect(152, 'net0')

as152_web.joinNetwork('net0')
as152_router.joinNetwork('net0')

as152_router.crossConnect(150, 'router0', '10.50.0.2/30')

###############################################################################

ebgp.addRsPeer(100, 150)
ebgp.addRsPeer(100, 151)

ebgp.addCrossConnectPeering(150, 152, PeerRelationship.Provider)

###############################################################################

sim.addLayer(base)
sim.addLayer(routing)
sim.addLayer(ebgp)
sim.addLayer(web)

sim.render()

###############################################################################

sim.compile(Docker(selfManagedNetwork = True), './cross-connect')