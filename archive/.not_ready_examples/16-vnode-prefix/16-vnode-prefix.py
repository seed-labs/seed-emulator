from seedemu import mergers
from seedemu.layers import Base, Routing, Ebgp, PeerRelationship, Ibgp, Ospf
from seedemu.services import WebService
from seedemu.core import Emulator, Binding, Filter
from seedemu.compiler import Docker
from seedemu.mergers import DEFAULT_MERGERS

###############################################################################

sim_base = Emulator()

base = Base()
routing = Routing()
ebgp = Ebgp()
ibgp = Ibgp()
ospf = Ospf()

###

base.createInternetExchange(100)
base.createInternetExchange(101)

###

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

###

as151 = base.createAutonomousSystem(151)

as151_web = as151.createHost('web')

as151_router = as151.createRouter('router0')

as151_net = as151.createNetwork('net0')



as151_web.joinNetwork('net0')
as151_router.joinNetwork('net0')

as151_router.joinNetwork('ix100')

###

as152 = base.createAutonomousSystem(152)

as152_web = as152.createHost('web')

as152_router = as152.createRouter('router0')

as152_net = as152.createNetwork('net0')



as152_web.joinNetwork('net0')
as152_router.joinNetwork('net0')

as152_router.joinNetwork('ix101')

###


ebgp.addPrivatePeering(100, 150, 151, abRelationship = PeerRelationship.Provider)
ebgp.addPrivatePeering(101, 150, 152, abRelationship = PeerRelationship.Provider)

###

sim_base.addLayer(base)
sim_base.addLayer(routing)
sim_base.addLayer(ebgp)
sim_base.addLayer(ibgp)
sim_base.addLayer(ospf)

###############################################################################

sim_web1 = Emulator()

web1 = WebService()
web1.install('host0')

sim_web1.addLayer(web1)

###############################################################################

sim_web2 = Emulator()

web2 = WebService()
web2.install('host0')

sim_web2.addLayer(web2)

###############################################################################

sim_base = sim_base.merge(sim_web1, vnodePrefix = 'web1_', mergers = DEFAULT_MERGERS)
sim_base = sim_base.merge(sim_web2, vnodePrefix = 'web2_', mergers = DEFAULT_MERGERS)

sim_base.addBinding(Binding('web1_host0', filter = Filter()))
sim_base.addBinding(Binding('web2_host0', filter = Filter()))

sim_base.render()

sim_base.compile(Docker(), './vnode-prefix')