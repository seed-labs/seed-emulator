from seedemu.core import Emulator, Binding, Filter
from seedemu.layers import Base, Routing, Ebgp, PeerRelationship
from seedemu.services import WebService
from seedemu.compiler import Docker



###############################################################################
# Load the component

emu = Emulator()
emu.load('component-dump.bin')

###############################################################################
# Demonstrating how to get the layers of the component.
# To build on top of this component, we need to get its layers. 

base: Base = emu.getLayer('Base')
web:  WebService = emu.getLayer('WebService')
routing: Routing = emu.getLayer('Routing')
ebgp: Ebgp = emu.getLayer('Ebgp')


###############################################################################
# Add a new autonomous system (AS-153)
# This requires making changes to the base, routing, and ebgp layers.

as153 = base.createAutonomousSystem(153)
as153.createNetwork('net0')


as153_router = as153.createRouter('router0')
as153_router.joinNetwork('net0')
as153_router.joinNetwork('ix100')

as153.createHost('web').joinNetwork('net0')
web.install('web153')
emu.addBinding(Binding('web153', filter = Filter(nodeName = 'web', asn = 153)))

# Peer with AS-150 and AS-151 at IX-100
ebgp.addPrivatePeering(100, 150, 153, abRelationship = PeerRelationship.Provider)
ebgp.addPrivatePeering(100, 151, 153, abRelationship = PeerRelationship.Peer)


###############################################################################
# Add a new web host to AS-151, which is from the component

as151 = base.getAutonomousSystem(151)
as151.createHost('web-2').joinNetwork('net0')
web.install('web151-2')
emu.addBinding(Binding('web151-2', filter = Filter(nodeName = 'web-2', asn = 151)))


###############################################################################
# Render and compile

emu.render()
emu.compile(Docker(), './output')
