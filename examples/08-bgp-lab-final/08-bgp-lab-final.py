from seedemu.layers import Base, Routing, Ebgp, PeerRelationship, Ibgp, Ospf
from seedemu.services import WebService
from seedemu.compiler import Docker
from seedemu.core import Emulator, Filter, Binding

emu = Emulator()

base = Base()
routing = Routing()
ebgp = Ebgp()
ibgp = Ibgp()
ospf = Ospf()
web = WebService()

###############################################################################

def make_stub_as(asn: int, exchange: str):
    stub_as = base.createAutonomousSystem(asn)

    web_server = stub_as.createHost('web')
    web.install('web{}'.format(asn))
    emu.addBinding(Binding('web{}'.format(asn), filter = Filter(asn = asn, nodeName = 'web')))

    router = stub_as.createRouter('router0')

    net = stub_as.createNetwork('net0')

    

    web_server.joinNetwork('net0')
    router.joinNetwork('net0')

    router.joinNetwork(exchange)

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

as2_100.joinNetwork('ix100')
as2_101.joinNetwork('ix101')
as2_102.joinNetwork('ix102')

as2_net_100_101 = as2.createNetwork('n01')
as2_net_101_102 = as2.createNetwork('n12')
as2_net_102_100 = as2.createNetwork('n20')





as2_100.joinNetwork('n01')
as2_101.joinNetwork('n01')

as2_101.joinNetwork('n12')
as2_102.joinNetwork('n12')

as2_102.joinNetwork('n20')
as2_100.joinNetwork('n20')

###############################################################################

as3 = base.createAutonomousSystem(3)

as3_101 = as3.createRouter('r1')
as3_102 = as3.createRouter('r2')

as3_101.joinNetwork('ix101')
as3_102.joinNetwork('ix102')

as3_net_101_102 = as3.createNetwork('n12')



as3_101.joinNetwork('n12')
as3_102.joinNetwork('n12')

###############################################################################

ebgp.addPrivatePeering(100, 2, 150, PeerRelationship.Provider)
ebgp.addPrivatePeering(100, 150, 151, PeerRelationship.Provider)

ebgp.addPrivatePeering(101, 2, 3, PeerRelationship.Provider)
ebgp.addPrivatePeering(101, 2, 152, PeerRelationship.Provider)
ebgp.addPrivatePeering(101, 3, 152, PeerRelationship.Provider)

ebgp.addPrivatePeering(102, 2, 160, PeerRelationship.Provider)
ebgp.addPrivatePeering(102, 3, 160, PeerRelationship.Provider)
ebgp.addPrivatePeering(102, 3, 161, PeerRelationship.Provider)

###############################################################################

emu.addLayer(base)
emu.addLayer(routing)
emu.addLayer(ebgp)
emu.addLayer(ibgp)
emu.addLayer(ospf)
emu.addLayer(web)

emu.render()

###############################################################################

emu.compile(Docker(), './output')
