#!/usr/bin/env python3

from seedemu.compiler import Docker, Graphviz
from seedemu.core import Emulator
from seedemu.layers import Base, Routing, Scion, PeerRelationship
from seedemu.layers.Scion import LinkType as ScLinkType

# Initialize
emu = Emulator()
base = Base()
routing = Routing()
scion = Scion()

# SCION ISDs
scion.addIsd(1)

# ASes
as150 = base.createAutonomousSystem(150)
as151 = base.createAutonomousSystem(151)
as152 = base.createAutonomousSystem(152)

as150_router = as150.createRouter('br1')
as151_router = as151.createRouter('br1')
as152_router = as152.createRouter('br1')

as150.createNetwork('net150')
as151.createNetwork('net151')
as152.createNetwork('net152')

as150_router.joinNetwork('net150')
as151_router.joinNetwork('net151')
as152_router.joinNetwork('net152')


scion.setAsIsd(150, 1)
scion.setAsIsd(151, 1)
scion.setAsIsd(152, 1)

scion.setCoreAs(150, True)
scion.setCertIssuer(151, 150)
scion.setCertIssuer(152, 150)

as150_router.crossConnect(151, 'br1', '10.150.1.2/29')
as150_router.crossConnect(152, 'br1', '10.150.2.2/29')
as151_router.crossConnect(150, 'br1', '10.150.1.3/29')
as152_router.crossConnect(150, 'br1', '10.150.2.3/29')

# BGP Peering
#ebgp.addPrivatePeering(100, 150, 151)
#ebgp.addPrivatePeering(100, 151, 152)
#ebgp.addPrivatePeering(100, 152, 150)
#ebgp.addCrossConnectPeering(150, 153, PeerRelationship.Provider)

scion.setInternalNet(150, 'net150')
scion.setInternalNet(151, 'net151')
scion.setInternalNet(152, 'net152')

scion.addXcLink(150, 151, ScLinkType.Transit)
scion.addXcLink(150, 152, ScLinkType.Transit)

# SCION Peering
#scion.addIxLink(100, 150, 151, ScLinkType.Core)
#scion.addIxLink(100, 151, 152, ScLinkType.Core)
#scion.addIxLink(100, 152, 150, ScLinkType.Core)
#scion.addXcLink(150, 153, ScLinkType.Transit)

# Rendering
emu.addLayer(base)
emu.addLayer(routing)
#emu.addLayer(ebgp)
emu.addLayer(scion)

emu.render()

# Compilation
emu.compile(Docker(), './output')
# FIXME: Graphing currently doesn't work when cross-connects are involved
# emu.compile(Graphviz(), "./output/graphs")
