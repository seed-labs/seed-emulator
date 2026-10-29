#!/usr/bin/env python3

from seedemu.compiler import Docker, Graphviz
from seedemu.core import Emulator
from seedemu.layers import ScionBase, ScionRouting, ScionIsd, Scion
from seedemu.layers.Scion import LinkType as ScLinkType

# Initialize
emu = Emulator()
base = ScionBase()
routing = ScionRouting()
scion_isd = ScionIsd()
scion = Scion()

# SCION ISDs
base.createIsolationDomain(1)

# Internet Exchanges
base.createInternetExchange(100, prefix = "192.100.0.0/16")

# Core AS with large ASN
as150 = base.createAutonomousSystem(0x100001101)
scion_isd.addIsdAs(1, 0x100001101, is_core=True)
as150.createNetwork('net0', "10.150.1.0/24")
as150.createControlService('cs1').joinNetwork('net0')
as150_router = as150.createRouter('br0')
as150_router.joinNetwork('net0').joinNetwork('ix100', address="192.100.0.150")

# Non-core AS
as153 = base.createAutonomousSystem(151)
scion_isd.addIsdAs(1, 151, is_core=False)
scion_isd.setCertIssuer((1, 151), issuer=0x100001101)
as153.createNetwork('net0')
as153.createControlService('cs1').joinNetwork('net0')
as153_router = as153.createRouter('br0')
as153_router.joinNetwork('net0').joinNetwork('ix100', address="192.100.0.151")

# SCION links
scion.addIxLink(100, (1, 0x100001101), (1, 151), ScLinkType.Transit)

# Rendering
emu.addLayer(base)
emu.addLayer(routing)
emu.addLayer(scion_isd)
emu.addLayer(scion)

emu.render()

# Compilation
emu.compile(Docker(), './output')
emu.compile(Graphviz(), "./output/graphs")
