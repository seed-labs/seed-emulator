from seedsim.layers import Base, Routing, Ebgp, PeerRelationship, Mpls, WebService
from seedsim.renderer import Renderer
from seedsim.compiler import Docker

base = Base()
routing = Routing()
ebgp = Ebgp()
mpls = Mpls()
web = WebService()

rendrer = Renderer()
docker_compiler = Docker()

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

r1.joinNetworkByName('ix100')
r1.joinNetworkByName('net0')

r2.joinNetworkByName('net0')
r2.joinNetworkByName('net1')

r3.joinNetworkByName('net1')
r3.joinNetworkByName('net2')

r4.joinNetworkByName('net2')
r4.joinNetworkByName('ix101')

mpls.enableOn(150)

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

as152_router.joinNetworkByName('ix101')

###############################################################################

ebgp.addPrivatePeering(100, 150, 151, abRelationship = PeerRelationship.Provider)
ebgp.addPrivatePeering(101, 150, 152, abRelationship = PeerRelationship.Provider)

###############################################################################

rendrer.addLayer(base)
rendrer.addLayer(routing)
rendrer.addLayer(ebgp)
rendrer.addLayer(mpls)
rendrer.addLayer(web)

rendrer.render()

###############################################################################

docker_compiler.compile('./transit-as-mpls')