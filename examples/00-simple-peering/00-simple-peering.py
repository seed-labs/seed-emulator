from seedsim.layers import Base, Routing, Ebgp, WebService
from seedsim.compiler import Docker
from seedsim.core import Simulator

sim = Simulator()

base = Base(sim)
routing = Routing(sim)
ebgp = Ebgp(sim)
web = WebService(sim)

###############################################################################

base.createInternetExchange(100)

###############################################################################

as150 = base.createAutonomousSystem(150)

as150_web = as150.createHost('web')
web.installOn(as150_web)

as150_router = as150.createRouter('router0')

as150_net = as150.createNetwork('net0')

routing.addDirect(as150_net)

as150_web.joinNetwork(as150_net)
as150_router.joinNetwork(as150_net)

as150_router.joinNetworkByName('ix100')

###############################################################################

as151 = base.createAutonomousSystem(151)

as151_web = as151.createHost('web')
web.installOn(as151_web)

as151_router = as151.createRouter('router0')

as151_net = as151.createNetwork('net0')

routing.addDirect(as151_net)

as151_web.joinNetwork(as151_net)
as151_router.joinNetwork(as151_net)

as151_router.joinNetworkByName('ix100')

###############################################################################

as152 = base.createAutonomousSystem(152)

as152_web = as152.createHost('web')
web.installOn(as152_web)

as152_router = as152.createRouter('router0')

as152_net = as152.createNetwork('net0')

routing.addDirect(as152_net)

as152_web.joinNetwork(as152_net)
as152_router.joinNetwork(as152_net)

as152_router.joinNetworkByName('ix100')

###############################################################################

ebgp.addRsPeer(100, 150)
ebgp.addRsPeer(100, 151)
ebgp.addRsPeer(100, 152)

###############################################################################

sim.addLayer(base)
sim.addLayer(routing)
sim.addLayer(ebgp)
sim.addLayer(web)

sim.render()

###############################################################################

sim.compile(Docker(), './simple-peering')