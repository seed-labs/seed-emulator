#!/usr/bin/env python3

from seedemu.compiler import Docker, Graphviz
from seedemu.core import Emulator
from seedemu.layers import Base, Ebgp, Routing, Scion
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
as150.createRouter('br0').joinNetwork('net0').joinNetwork('ix100')
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

# BGP Peering
ebgp.addPrivatePeering(100, 150, 151)
ebgp.addPrivatePeering(100, 151, 152)
ebgp.addPrivatePeering(100, 152, 150)

# SCION Peering
scion.addIxLink(100, 150, 151, ScLinkType.Peer)
scion.addIxLink(100, 151, 152, ScLinkType.Peer)
scion.addIxLink(100, 152, 150, ScLinkType.Peer)

# Rendering
emu.addLayer(base)
emu.addLayer(routing)
emu.addLayer(ebgp)
emu.addLayer(scion)

emu.render()

# Compilation
emu.compile(Docker(), './output')
emu.compile(Graphviz(), "./output/graphs")
