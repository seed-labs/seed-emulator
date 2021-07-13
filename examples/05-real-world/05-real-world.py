from seedemu.layers import Base, Routing, Ebgp, PeerRelationship, Ibgp, Ospf
from seedemu.services import WebService
from seedemu.core import Emulator, Binding, Filter
from seedemu.raps import OpenVpnRemoteAccessProvider
from seedemu.compiler import Docker

emu     = Emulator()
base    = Base()
routing = Routing()
ebgp    = Ebgp()
ibgp    = Ibgp()
ospf    = Ospf()
web     = WebService()
ovpn    = OpenVpnRemoteAccessProvider()

###############################################################################

base.createInternetExchange(100)
base.createInternetExchange(101)

###############################################################################
# Create AS-150 with 3 internet networks

as150 = base.createAutonomousSystem(150)

as150.createNetwork('net0')
as150.createNetwork('net1')
as150.createNetwork('net2')

# Create 4 routers: r1 and r4 are BGP routers (connected to internet exchange) 
as150.createRouter('r1').joinNetwork('ix100').joinNetwork('net0')
as150.createRouter('r2').joinNetwork('net0').joinNetwork('net1')
as150.createRouter('r3').joinNetwork('net1').joinNetwork('net2')
as150.createRouter('r4').joinNetwork('net2').joinNetwork('ix101')


###############################################################################
# Create AS-151

as151 = base.createAutonomousSystem(151)

# Create a network and enable the access from machines outside of the emulator
as151.createNetwork('net0').enableRemoteAccess(ovpn)

# Create a host and a router
as151.createHost('web').joinNetwork('net0')
as151.createRouter('router0').joinNetwork('net0').joinNetwork('ix100')


###############################################################################
# Create AS-152

as152 = base.createAutonomousSystem(152)
as152.createNetwork('net0').enableRemoteAccess(ovpn)
as152.createHost('web').joinNetwork('net0')
as152.createRouter('router0').joinNetwork('net0').joinNetwork('ix101')


###############################################################################
# Create a real-world AS

as11872 = base.createAutonomousSystem(11872)
as11872.createRealWorldRouter('rw').joinNetwork('ix101', '10.101.0.118')

###############################################################################
# BGP peering 

ebgp.addPrivatePeering(100, 150, 151, abRelationship = PeerRelationship.Provider)
ebgp.addPrivatePeering(101, 150, 152, abRelationship = PeerRelationship.Provider)
ebgp.addPrivatePeering(101, 150, 11872, abRelationship = PeerRelationship.Unfiltered)

###############################################################################
# Create two virtual nodes that run web services, bind them to physical nodes

web.install('web1')
web.install('web2')
emu.addBinding(Binding('web1', filter = Filter(asn = 151, nodeName = 'web')))
emu.addBinding(Binding('web2', filter = Filter(asn = 152, nodeName = 'web')))

###############################################################################
# Rendering

emu.addLayer(base)
emu.addLayer(routing)
emu.addLayer(ebgp)
emu.addLayer(ibgp)
emu.addLayer(ospf)
emu.addLayer(web)

emu.render()

###############################################################################
# Compilation 

emu.compile(Docker(), './output')
