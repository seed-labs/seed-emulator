from seedsim.layers import Base, Routing, Ebgp, Ibgp, Ospf, WebService, Router
from seedsim.renderer import Renderer
from seedsim.compiler import Docker
from seedsim.core import Registry

base = Base()
routing = Routing()
ebgp = Ebgp()
ibgp = Ibgp()
ospf = Ospf()
web = WebService()

rendrer = Renderer()
docker_compiler = Docker()

###############################################################################

def make_stub_as(asn: int, exchange: str):
    stub_as = base.createAutonomousSystem(asn)

    web_server = stub_as.createHost('web')
    web.installOn(web_server)

    router = stub_as.createRouter('router0')

    net = stub_as.createNetwork('net0')

    routing.addDirect(net)

    web_server.joinNetwork(net)
    router.joinNetwork(net)

    router.joinNetworkByName(exchange)

###############################################################################

base.createInternetExchange(100)
base.createInternetExchange(101)
base.createInternetExchange(102)

###############################################################################

make_stub_as(150, 'ix100')
make_stub_as(151, 'ix100')

make_stub_as(152, 'ix101')

make_stub_as(160, 'ix102')
make_stub_as(161, 'ix102')

###############################################################################

as2 = base.createAutonomousSystem(2)

as2_100 = as2.createRouter('r0')
as2_101 = as2.createRouter('r1')
as2_102 = as2.createRouter('r2')

as2_100.joinNetworkByName('ix100')
as2_101.joinNetworkByName('ix101')
as2_102.joinNetworkByName('ix102')

as2_net_100_101 = as2.createNetwork('n01')
as2_net_101_102 = as2.createNetwork('n12')
as2_net_102_100 = as2.createNetwork('n20')

routing.addDirect(as2_net_100_101)
routing.addDirect(as2_net_101_102)
routing.addDirect(as2_net_102_100)

as2_100.joinNetwork(as2_net_100_101)
as2_101.joinNetwork(as2_net_100_101)

as2_101.joinNetwork(as2_net_101_102)
as2_102.joinNetwork(as2_net_101_102)

as2_102.joinNetwork(as2_net_102_100)
as2_100.joinNetwork(as2_net_102_100)

###############################################################################

as3 = base.createAutonomousSystem(3)

as3_101 = as3.createRouter('r1')
as3_102 = as3.createRouter('r2')

as3_101.joinNetworkByName('ix101')
as3_102.joinNetworkByName('ix102')

as3_net_101_102 = as3.createNetwork('n12')

routing.addDirect(as3_net_101_102)

as3_101.joinNetwork(as3_net_101_102)
as3_102.joinNetwork(as3_net_101_102)

###############################################################################

ebgp.addPrivatePeering(100, 2, 150)
ebgp.addPrivatePeering(100, 150, 151)

ebgp.addPrivatePeering(101, 2, 3)
ebgp.addPrivatePeering(101, 2, 152)
ebgp.addPrivatePeering(101, 3, 152)

ebgp.addPrivatePeering(102, 2, 160)
ebgp.addPrivatePeering(102, 3, 160)
ebgp.addPrivatePeering(102, 3, 161)

###############################################################################

rendrer.addLayer(base)
rendrer.addLayer(routing)
rendrer.addLayer(ebgp)
rendrer.addLayer(ibgp)
rendrer.addLayer(ospf)
rendrer.addLayer(web)

rendrer.render()

###############################################################################

docker_compiler.compile('./bgp-lab-final')
