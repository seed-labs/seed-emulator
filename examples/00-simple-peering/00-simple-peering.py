from seedsim.layers import Base, Routing, Ebgp, WebService
from seedsim.compiler import Docker
from seedsim.core import Simulator

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
web.installByName(150, 'web')

as150_router = as150.createRouter('router0')
as150_net = as150.createNetwork('net0')

routing.addDirect(150, 'net0')

as150_web.joinNetwork('net0')
as150_router.joinNetwork('net0')

as150_router.joinNetwork('ix100')

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

as152_router.joinNetwork('ix100')

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