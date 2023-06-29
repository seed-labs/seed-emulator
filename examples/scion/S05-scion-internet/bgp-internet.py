#!/usr/bin/env python3

from ipaddress import IPv4Network
from seedemu.compiler import Docker
from seedemu.core import Emulator
from seedemu.layers import ScionBase, ScionRouting, ScionIsd, Scion, Ebgp
from seedemu.layers import PeerRelationship as PeerRel
from seedemu.layers.Scion import LinkType as ScLinkType


def create_as(isd, asn, is_core=False, issuer=None):
    as_ = base.createAutonomousSystem(asn)
    scion_isd.addIsdAs(isd, asn, is_core)
    if not is_core:
        scion_isd.setCertIssuer((isd, asn), issuer)
    as_.createNetwork('net0')
    as_.createControlService('cs1').joinNetwork('net0')
    br = as_.createRouter('br0')
    br.joinNetwork('net0')
    return as_, br


class CrossConnectNetAssigner:
    def __init__(self):
        self.subnet_iter = IPv4Network("10.3.0.0/16").subnets(new_prefix=29)
        self.xc_nets = {}

    def next_addr(self, net):
        if net not in self.xc_nets:
            hosts = next(self.subnet_iter).hosts()
            next(hosts) # Skip first IP (reserved for Docker)
            self.xc_nets[net] = hosts
        return "{}/29".format(next(self.xc_nets[net]))

xc_nets = CrossConnectNetAssigner()


# Initialize
emu = Emulator()
base = ScionBase()
routing = ScionRouting()
scion_isd = ScionIsd()
scion = Scion()
ebgp = Ebgp()

# SCION ISDs
base.createIsolationDomain(1)

# IXes
base.createInternetExchange(10) # Large IXP (east)
base.createInternetExchange(11) # Large IXP (west)
base.createInternetExchange(12) # Small IXP

# ASes
_, br = create_as(1, 50, is_core=True) # Tier-1 ISP
br.crossConnect(60, 'br0', xc_nets.next_addr('50-60'))
br.crossConnect(70, 'br0', xc_nets.next_addr('50-70'))
br.crossConnect(150, 'br0', xc_nets.next_addr('50-150'))
br.crossConnect(151, 'br0', xc_nets.next_addr('50-151'))
br.crossConnect(180, 'br0', xc_nets.next_addr('50-180'))
br.crossConnect(200, 'br0', xc_nets.next_addr('50-200'))
_, br = create_as(1, 60, is_core=True) # Tier-1 ISP
br.crossConnect(50, 'br0', xc_nets.next_addr('50-60'))
br.crossConnect(70, 'br0', xc_nets.next_addr('60-70'))
br.crossConnect(152, 'br0', xc_nets.next_addr('60-152'))
br.crossConnect(180, 'br0', xc_nets.next_addr('60-180'))
_, br = create_as(1, 70, is_core=True) # Tier-1 ISP
br.crossConnect(50, 'br0', xc_nets.next_addr('50-70'))
br.crossConnect(60, 'br0', xc_nets.next_addr('60-70'))
br.crossConnect(160, 'br0', xc_nets.next_addr('70-160'))
br.crossConnect(161, 'br0', xc_nets.next_addr('70-161'))
br.crossConnect(162, 'br0', xc_nets.next_addr('70-162'))
br.crossConnect(163, 'br0', xc_nets.next_addr('70-163'))
br.crossConnect(170, 'br0', xc_nets.next_addr('70-170'))
br.crossConnect(200, 'br0', xc_nets.next_addr('70-200'))
_, br = create_as(1, 170, issuer=70) # Access Network
br.joinNetwork('ix11').joinNetwork('ix12')
br.crossConnect(70, 'br0', xc_nets.next_addr('70-170'))
_, br = create_as(1, 180, issuer=50) # Large Access Network
br.joinNetwork('ix10')
br.crossConnect(50, 'br0', xc_nets.next_addr('50-180'))
br.crossConnect(60, 'br0', xc_nets.next_addr('60-180'))
_, br = create_as(1, 200, issuer=50) # Content Provider
br.joinNetwork('ix10').joinNetwork('ix11').joinNetwork('ix12')
br.crossConnect(50, 'br0', xc_nets.next_addr('50-200'))
br.crossConnect(70, 'br0', xc_nets.next_addr('70-200'))
br.crossConnect(150, 'br0', xc_nets.next_addr('150-200'))
br.crossConnect(163, 'br0', xc_nets.next_addr('163-200'))
_, br = create_as(1, 150, issuer=50)
br.joinNetwork('ix10')
br.crossConnect(50, 'br0', xc_nets.next_addr('50-150'))
br.crossConnect(200, 'br0', xc_nets.next_addr('150-200'))
_, br = create_as(1, 151, issuer=50)
br.joinNetwork('ix10')
br.crossConnect(50, 'br0', xc_nets.next_addr('50-151'))
_, br = create_as(1, 152, issuer=60)
br.joinNetwork('ix10')
br.crossConnect(60, 'br0', xc_nets.next_addr('60-152'))
_, br = create_as(1, 160, issuer=70)
br.joinNetwork('ix11').joinNetwork('ix12')
br.crossConnect(70, 'br0', xc_nets.next_addr('70-160'))
_, br = create_as(1, 161, issuer=70)
br.joinNetwork('ix12')
br.crossConnect(70, 'br0', xc_nets.next_addr('70-161'))
_, br = create_as(1, 162, issuer=70)
br.joinNetwork('ix12')
br.crossConnect(70, 'br0', xc_nets.next_addr('70-162'))
_, br = create_as(1, 163, issuer=70)
br.joinNetwork('ix11').joinNetwork('ix12')
br.crossConnect(70, 'br0', xc_nets.next_addr('70-163'))
br.crossConnect(200, 'br0', xc_nets.next_addr('163-200'))

# BGP
ebgp.addCrossConnectPeering(70, 50, PeerRel.Peer)
ebgp.addCrossConnectPeering(50, 60, PeerRel.Peer)
ebgp.addCrossConnectPeering(60, 70, PeerRel.Peer)
ebgp.addCrossConnectPeering(70, 170, PeerRel.Provider)
ebgp.addCrossConnectPeering(70, 160, PeerRel.Provider)
ebgp.addCrossConnectPeering(70, 161, PeerRel.Provider)
ebgp.addCrossConnectPeering(70, 162, PeerRel.Provider)
ebgp.addCrossConnectPeering(70, 163, PeerRel.Provider)
ebgp.addCrossConnectPeering(70, 200, PeerRel.Provider)
ebgp.addCrossConnectPeering(50, 200, PeerRel.Provider)
ebgp.addCrossConnectPeering(50, 150, PeerRel.Provider)
ebgp.addCrossConnectPeering(50, 151, PeerRel.Provider)
ebgp.addCrossConnectPeering(50, 180, PeerRel.Provider)
ebgp.addCrossConnectPeering(60, 180, PeerRel.Provider)
ebgp.addCrossConnectPeering(60, 152, PeerRel.Provider)
ebgp.addCrossConnectPeering(200, 163, PeerRel.Peer)
ebgp.addCrossConnectPeering(200, 150, PeerRel.Peer)
peers_ix12 = [160, 161, 162, 163, 170, 200]
for peer in peers_ix12:
    ebgp.addRsPeer(12, peer)
peers_ix11 = [160, 163, 170, 200]
for peer in peers_ix11:
    ebgp.addRsPeer(11, peer)
peers_ix10 = [150, 151, 152, 180, 200]
for peer in peers_ix10:
    ebgp.addRsPeer(10, peer)

# SCION links
scion.addXcLink((1, 70), (1, 50), ScLinkType.Core)
scion.addXcLink((1, 50), (1, 60), ScLinkType.Core)
scion.addXcLink((1, 60), (1, 70), ScLinkType.Core)
scion.addXcLink((1, 70), (1, 170), ScLinkType.Transit)
scion.addXcLink((1, 70), (1, 160), ScLinkType.Transit)
scion.addXcLink((1, 70), (1, 161), ScLinkType.Transit)
scion.addXcLink((1, 70), (1, 162), ScLinkType.Transit)
scion.addXcLink((1, 70), (1, 163), ScLinkType.Transit)
scion.addXcLink((1, 70), (1, 200), ScLinkType.Transit)
scion.addXcLink((1, 50), (1, 200), ScLinkType.Transit)
scion.addXcLink((1, 50), (1, 150), ScLinkType.Transit)
scion.addXcLink((1, 50), (1, 151), ScLinkType.Transit)
scion.addXcLink((1, 50), (1, 180), ScLinkType.Transit)
scion.addXcLink((1, 60), (1, 180), ScLinkType.Transit)
scion.addXcLink((1, 60), (1, 152), ScLinkType.Transit)
scion.addXcLink((1, 200), (1, 163), ScLinkType.Peer)
scion.addXcLink((1, 200), (1, 150), ScLinkType.Peer)
for a, b in [(a, b) for a in peers_ix12 for b in peers_ix12 if a < b]:
    scion.addIxLink(12, (1, a), (1, b), ScLinkType.Peer)
for a, b in [(a, b) for a in peers_ix11 for b in peers_ix11 if a < b]:
    scion.addIxLink(11, (1, a), (1, b), ScLinkType.Peer)
for a, b in [(a, b) for a in peers_ix10 for b in peers_ix10 if a < b]:
    scion.addIxLink(10, (1, a), (1, b), ScLinkType.Peer)

# Rendering
emu.addLayer(base)
emu.addLayer(routing)
emu.addLayer(scion_isd)
emu.addLayer(scion)
emu.addLayer(ebgp)

emu.render()

# Compilation
emu.compile(Docker(), './bgp')
