#!/usr/bin/env python3

from seedemu.compiler import Docker, Graphviz
from seedemu.core import Emulator
from seedemu.layers import (
    ScionBase, ScionRouting, ScionIsd, Scion, Ospf, Ibgp, Ebgp, PeerRelationship)
from seedemu.layers.Scion import LinkType as ScLinkType

# Initialize
emu = Emulator()
base = ScionBase()
routing = ScionRouting()
ospf = Ospf()
scion_isd = ScionIsd()
scion = Scion()
ibgp = Ibgp()
ebgp = Ebgp()

# SCION ISDs
base.createIsolationDomain(1)
base.createIsolationDomain(2)

# Internet Exchanges
base.createInternetExchange(100)
base.createInternetExchange(101)
base.createInternetExchange(102)
base.createInternetExchange(103)
base.createInternetExchange(104)

# Core AS 1-150
as150 = base.createAutonomousSystem(150)
scion_isd.addIsdAs(1, 150, is_core=True)
as150.createNetwork('net0')
as150.createNetwork('net1')
as150.createNetwork('net2')
as150.createNetwork('net3')
as150.createControlService('cs1').joinNetwork('net0')
as150.createControlService('cs2').joinNetwork('net2')
as150_br0 = as150.createRouter('br0')
as150_br1 = as150.createRouter('br1')
as150_br2 = as150.createRouter('br2')
as150_br3 = as150.createRouter('br3')
as150_br0.joinNetwork('net0').joinNetwork('net1').joinNetwork('ix100')
as150_br1.joinNetwork('net1').joinNetwork('net2').joinNetwork('ix101')
as150_br2.joinNetwork('net2').joinNetwork('net3').joinNetwork('ix102')
as150_br3.joinNetwork('net3').joinNetwork('net0').joinNetwork('ix103')

# Non-core ASes in ISD 1
asn_ix = {
    151: 101,
    152: 102,
    153: 103,
}
for asn, ix in asn_ix.items():
    as_ = base.createAutonomousSystem(asn)
    scion_isd.addIsdAs(1, asn, is_core=False)
    scion_isd.setCertIssuer((1, asn), issuer=150)
    as_.createNetwork('net0')
    as_.createControlService('cs1').joinNetwork('net0')
    as_.createRouter('br0').joinNetwork('net0').joinNetwork(f'ix{ix}')

# Core AS 1-160
as160 = base.createAutonomousSystem(160)
scion_isd.addIsdAs(2, 160, is_core=True)
as160.createNetwork('net0')
as160.createControlService('cs1').joinNetwork('net0')
as160.createRouter('br0').joinNetwork('net0').joinNetwork('ix100')
as160.createRouter('br1').joinNetwork('net0').joinNetwork('ix104')

# Non-core AS in ISD 2
as161 = base.createAutonomousSystem(161)
scion_isd.addIsdAs(2, 161, is_core=False)
scion_isd.setCertIssuer((2, 161), issuer=160)
as161.createNetwork('net0')
as161.createControlService('cs1').joinNetwork('net0')
as161.createRouter('br0').joinNetwork('net0').joinNetwork('ix104')

# SCION links
scion.addIxLink(100, (1, 150), (2, 160), ScLinkType.Core)
scion.addIxLink(101, (1, 150), (1, 151), ScLinkType.Transit)
scion.addIxLink(102, (1, 150), (1, 152), ScLinkType.Transit)
scion.addIxLink(103, (1, 150), (1, 153), ScLinkType.Transit)
scion.addIxLink(104, (2, 160), (2, 161), ScLinkType.Transit)

# BGP peering
ebgp.addPrivatePeering(100, 150, 160, abRelationship=PeerRelationship.Peer)
ebgp.addPrivatePeering(101, 150, 151, abRelationship=PeerRelationship.Provider)
ebgp.addPrivatePeering(102, 150, 152, abRelationship=PeerRelationship.Provider)
ebgp.addPrivatePeering(103, 150, 153, abRelationship=PeerRelationship.Provider)
ebgp.addPrivatePeering(104, 160, 161, abRelationship=PeerRelationship.Provider)

# Rendering
emu.addLayer(base)
emu.addLayer(routing)
emu.addLayer(ospf)
emu.addLayer(scion_isd)
emu.addLayer(scion)
emu.addLayer(ibgp)
emu.addLayer(ebgp)

emu.render()

# Compilation
emu.compile(Docker(), './output')
emu.compile(Graphviz(), "./output/graphs")
