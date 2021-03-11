from seedsim.core import Simulator
from seedsim.layers import Base, Routing, Ebgp, Ospf, Ibgp, PeerRelationship
from seedsim.components import BgpAttackerComponent
from seedsim.compiler import Docker
from seedsim.mergers import DEFAULT_MERGERS

###############################################################################
# topology:
#
# as150 --+
#          \__ ix100 -- as2 -- ix101 -- as151 
#          /
# as666 --+
# (hijacking as151)
###############################################################################

sim = Simulator()

base = Base()
routing = Routing()
ebgp = Ebgp()
ospf = Ospf()
ibgp = Ibgp()

bgp_attack = BgpAttackerComponent()

###############################################################################

base.createInternetExchange(100)
base.createInternetExchange(101)

###############################################################################

as150 = base.createAutonomousSystem(150)

as150_r0 = as150.createRouter('r0')

as150_n0 = as150.createNetwork('n0')

routing.addDirect(150, 'n0')

as150_r0.joinNetwork('n0')
as150_r0.joinNetwork('ix100')

###############################################################################

as2 = base.createAutonomousSystem(2)

as2_r0 = as2.createRouter('r0')
as2_r1 = as2.createRouter('r1')

as2_n0 = as2.createNetwork('n0')

as2_r0.joinNetwork('n0')
as2_r1.joinNetwork('n0')

as2_r0.joinNetwork('ix100')
as2_r1.joinNetwork('ix101')

###############################################################################

as151 = base.createAutonomousSystem(151)

as151_r0 = as151.createRouter('r0')

as151_n0 = as151.createNetwork('n0')

routing.addDirect(151, 'n0')

as151_r0.joinNetwork('n0')
as151_r0.joinNetwork('ix101')

###############################################################################

sim.addLayer(base)
sim.addLayer(routing)
sim.addLayer(ibgp)
sim.addLayer(ebgp)
sim.addLayer(ospf)

###############################################################################

bgp_attack.addHijackedPrefix(as151_n0.getPrefix())
bgp_attack.joinInternetExchange('ix100', '10.100.0.66')

hijack_component = bgp_attack.get()

sim_with_attack = sim.merge(bgp_attack.get(), DEFAULT_MERGERS)

###############################################################################

ebgp.addPrivatePeering(100, 2, 150, PeerRelationship.Provider)
ebgp.addPrivatePeering(101, 2, 151, PeerRelationship.Provider)

# hijacker's session
ebgp.addPrivatePeering(100, 2, 666, PeerRelationship.Unfiltered)

###############################################################################

sim_with_attack.render()
sim_with_attack.compile(Docker(), 'bgp-attacker-component')