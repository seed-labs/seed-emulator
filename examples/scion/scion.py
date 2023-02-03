#!/usr/bin/env python3

from seedemu.compiler import Docker, Graphviz
from seedemu.core import Emulator
from seedemu.layers import Base, Ebgp, Routing, Scion, PeerRelationship
from seedemu.layers.Scion import LinkType as ScLinkType

# Initialize
emu = Emulator()
base = Base()
routing = Routing()
ebgp = Ebgp()
scion = Scion()

# SCION ISDs
scion.addIsd(1)

# Internet Exchange
base.createInternetExchange(100)

# AS-150
as150 = base.createAutonomousSystem(150)
as150.createNetwork('net0')
as150_router = as150.createRouter('br0')
as150_router.joinNetwork('net0').joinNetwork('ix100')
as150_router.crossConnect(153, 'br0', '10.50.0.2/29')
scion.setAsIsd(150, 1)
scion.setCoreAs(150, True)

# AS-151
as151 = base.createAutonomousSystem(151)
as151.createNetwork('net0')
as151.createRouter('br0').joinNetwork('net0').joinNetwork('ix100')
scion.setAsIsd(151, 1)
scion.setCoreAs(151, True)

# AS-152
as152 = base.createAutonomousSystem(152)
as152.createNetwork('net0')
as152.createRouter('br0').joinNetwork('net0').joinNetwork('ix100')
scion.setAsIsd(152, 1)
scion.setCoreAs(152, True)

# AS-153
as153 = base.createAutonomousSystem(153)
as153.createNetwork('net0')
as153_router = as153.createRouter('br0')
as153_router.joinNetwork('net0')
as153_router.crossConnect(150, 'br0', '10.50.0.3/29')
scion.setAsIsd(153, 1)
scion.setCertIssuer(153, 150)

# BGP Peering
ebgp.addPrivatePeering(100, 150, 151)
ebgp.addPrivatePeering(100, 151, 152)
ebgp.addPrivatePeering(100, 152, 150)
ebgp.addCrossConnectPeering(150, 153, PeerRelationship.Provider)

# SCION Peering
scion.addIxLink(100, 150, 151, ScLinkType.Core)
scion.addIxLink(100, 151, 152, ScLinkType.Core)
scion.addIxLink(100, 152, 150, ScLinkType.Core)
scion.addXcLink(150, 153, ScLinkType.Transit)

# Rendering
emu.addLayer(base)
emu.addLayer(routing)
emu.addLayer(ebgp)
emu.addLayer(scion)

emu.render()

# Compilation
emu.compile(Docker(), './output')
# FIXME: Graphing currently doesn't work when cross-connects are involved
# emu.compile(Graphviz(), "./output/graphs")
