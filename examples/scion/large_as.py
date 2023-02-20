#!/usr/bin/env python3

from seedemu.compiler import Docker, Graphviz
from seedemu.core import Emulator
from seedemu.layers import ScionBase, ScionRouting, Ospf, ScionIsd, Scion
from seedemu.layers.Scion import LinkType as ScLinkType

# Initialize
emu = Emulator()
base = ScionBase()
routing = ScionRouting()
ospf = Ospf()
scion_isd = ScionIsd()
scion = Scion()

# SCION ISDs
base.createIsolationDomain(1)

# Internet Exchanges
base.createInternetExchange(100)
base.createInternetExchange(101)
base.createInternetExchange(102)
base.createInternetExchange(103)

# Core AS
as150 = base.createAutonomousSystem(150)
scion_isd.addIsdAs(1, 150, is_core=True)
as150.createNetwork('net0')
as150.createNetwork('net1')
as150.createNetwork('net2')
as150.createNetwork('net3')
# XXX(lschulz) Doesn't work. BFD fails because intra-AS routing does not work as required.
# (Not all BR interface can see each other)
as150.createControlService('cs1').joinNetwork('net0').joinNetwork('net1').joinNetwork('net2').joinNetwork('net3')
as150_br0 = as150.createRouter('br0')
as150_br1 = as150.createRouter('br1')
as150_br2 = as150.createRouter('br2')
as150_br3 = as150.createRouter('br3')
as150_br0.joinNetwork('net0').joinNetwork('net1').joinNetwork('ix100')
as150_br1.joinNetwork('net1').joinNetwork('net2').joinNetwork('ix101')
as150_br2.joinNetwork('net2').joinNetwork('net3').joinNetwork('ix102')
as150_br3.joinNetwork('net3').joinNetwork('net0').joinNetwork('ix103')

# Non-core ASes
asn_ix = {
    151: 100,
    152: 101,
    153: 101,
    154: 102,
    155: 103,
    156: 103,
}
for asn, ix in asn_ix.items():
    asys = base.createAutonomousSystem(asn)
    scion_isd.addIsdAs(1, asn, is_core=False)
    scion_isd.setCertIssuer(1, asn, issuer=150)
    asys.createNetwork('net0')
    asys.createControlService('cs1').joinNetwork('net0')
    asys.createRouter('br0').joinNetwork('net0').joinNetwork(f'ix{ix}')
    scion.addIxLink(ix, (1, 150), (1, asn), ScLinkType.Transit)

# Rendering
emu.addLayer(base)
emu.addLayer(routing)
emu.addLayer(ospf)
emu.addLayer(scion_isd)
emu.addLayer(scion)

emu.render()

# Compilation
emu.compile(Docker(), './output')
emu.compile(Graphviz(), "./output/graphs")
