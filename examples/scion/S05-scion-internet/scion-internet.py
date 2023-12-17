#!/usr/bin/env python3

from ipaddress import IPv4Network
from seedemu.compiler import Docker
from seedemu.core import Emulator
from seedemu.layers import ScionBase, ScionRouting, ScionIsd, Scion
from seedemu.layers.Scion import LinkType as ScLinkType


def create_as(isd, asn, is_core=False, issuer=None):
    as_ = base.createAutonomousSystem(asn)
    scion_isd.addIsdAs(isd, asn, is_core)
    if not is_core:
        scion_isd.setCertIssuer((isd, asn), issuer)
    as_.createNetwork('net0')
    as_.createControlService('cs1').joinNetwork('net0')
    as_.setBeaconingIntervals('30s', '30s', '30s')
    if is_core:
        policy = {
            'Filter': {
                'MaxHopsLength': 4,
                'AllowIsdLoop': False
            }
        }
        as_.setBeaconPolicy('propagation', policy).setBeaconPolicy('core_registration', policy)
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

# SCION ISDs
base.createIsolationDomain(1)

# Internet Exchanges
# We use "Internet Exchanges" as internal networks of the subdivided ASes in
# order to reduce the number of networks Docker has to create.
base.createInternetExchange(5)  # Tier-1 ISP
base.createInternetExchange(7)  # Tier-1 ISP
base.createInternetExchange(10) # Large IXP
base.createInternetExchange(11) # Large IXP
base.createInternetExchange(12) # Small IXP
base.createInternetExchange(17) # Small access network
base.createInternetExchange(18) # Large access network
base.createInternetExchange(20) # Large content provider

# Tier-1 ISP as50-53
br = create_as(1, 50, is_core=True)[1].joinNetwork('ix5')
br.crossConnect(60, 'br0', xc_nets.next_addr('50-60'))
br.crossConnect(70, 'br0', xc_nets.next_addr('50-70'))
br.crossConnect(201, 'br0', xc_nets.next_addr('50-201'))
br = create_as(1, 51, issuer=50)[1].joinNetwork('ix5')
br.crossConnect(150, 'br0', xc_nets.next_addr('51-150'))
br.crossConnect(151, 'br0', xc_nets.next_addr('51-151'))
br.crossConnect(181, 'br0', xc_nets.next_addr('51-181'))
create_as(1, 52, issuer=50)[1].joinNetwork('ix5')
br = create_as(1, 53, issuer=50)[1].joinNetwork('ix5')
br.crossConnect(152, 'br0', xc_nets.next_addr('53-152'))
scion.addIxLink(5, (1, 50), (1, 51), ScLinkType.Transit)
scion.addIxLink(5, (1, 50), (1, 52), ScLinkType.Transit)
scion.addIxLink(5, (1, 50), (1, 53), ScLinkType.Transit)
scion.addIxLink(5, (1, 52), (1, 51), ScLinkType.Transit, count=2)
scion.addIxLink(5, (1, 52), (1, 53), ScLinkType.Transit, count=2)

# Tier-1 ISP as60
_, br = create_as(1, 60, is_core=True)
br.crossConnect(50, 'br0', xc_nets.next_addr('50-60'))
br.crossConnect(70, 'br0', xc_nets.next_addr('60-70'))
br.crossConnect(103, 'br0', xc_nets.next_addr('60-103'))
br.crossConnect(152, 'br0', xc_nets.next_addr('60-152'))
br.crossConnect(180, 'br0', xc_nets.next_addr('60-180'))

# Tier-1 ISP as70-73
br = create_as(1, 70, is_core=True)[1].joinNetwork('ix7')
br.crossConnect(50, 'br0', xc_nets.next_addr('50-70'))
br.crossConnect(60, 'br0', xc_nets.next_addr('60-70'))
br.crossConnect(110, 'br0', xc_nets.next_addr('70-110'))
br.crossConnect(170, 'br0', xc_nets.next_addr('70-170'))
br.crossConnect(200, 'br0', xc_nets.next_addr('70-200'))
br = create_as(1, 71, issuer=70)[1].joinNetwork('ix7')
br.crossConnect(120, 'br0', xc_nets.next_addr('71-120'))
br.crossConnect(160, 'br0', xc_nets.next_addr('71-160'))
br.crossConnect(161, 'br0', xc_nets.next_addr('71-161'))
create_as(1, 72, issuer=70)[1].joinNetwork('ix7')
br = create_as(1, 73, issuer=70)[1].joinNetwork('ix7')
br.crossConnect(162, 'br0', xc_nets.next_addr('73-162'))
br.crossConnect(163, 'br0', xc_nets.next_addr('73-163'))
scion.addIxLink(7, (1, 70), (1, 71), ScLinkType.Transit)
scion.addIxLink(7, (1, 70), (1, 72), ScLinkType.Transit)
scion.addIxLink(7, (1, 70), (1, 73), ScLinkType.Transit)
scion.addIxLink(7, (1, 72), (1, 71), ScLinkType.Transit, count=2)
scion.addIxLink(7, (1, 72), (1, 73), ScLinkType.Transit, count=2)

# Large IXP as100-113
br = create_as(1, 100, is_core=True)[1].joinNetwork('ix10')
br.crossConnect(111, 'br0', xc_nets.next_addr('100-111'))
create_as(1, 101, is_core=True)[1].joinNetwork('ix10')
create_as(1, 102, is_core=True)[1].joinNetwork('ix10')
br = create_as(1, 103, is_core=True)[1].joinNetwork('ix10')
br.crossConnect(60, 'br0', xc_nets.next_addr('60-103'))
create_as(1, 104, issuer=100)[1].joinNetwork('ix10')
create_as(1, 105, issuer=100)[1].joinNetwork('ix10')
create_as(1, 106, issuer=100)[1].joinNetwork('ix10')
create_as(1, 107, issuer=100)[1].joinNetwork('ix10')
create_as(1, 108, issuer=100)[1].joinNetwork('ix10')
create_as(1, 109, issuer=100)[1].joinNetwork('ix10')
scion.addIxLink(10, (1, 100), (1, 101), ScLinkType.Core)
scion.addIxLink(10, (1, 101), (1, 102), ScLinkType.Core)
scion.addIxLink(10, (1, 102), (1, 103), ScLinkType.Core)
scion.addIxLink(10, (1, 100), (1, 102), ScLinkType.Core)
scion.addIxLink(10, (1, 101), (1, 103), ScLinkType.Core)
scion.addIxLink(10, (1, 100), (1, 104), ScLinkType.Transit, count=2)
scion.addIxLink(10, (1, 100), (1, 105), ScLinkType.Transit, count=2)
scion.addIxLink(10, (1, 100), (1, 106), ScLinkType.Transit, count=2)
scion.addIxLink(10, (1, 100), (1, 107), ScLinkType.Transit, count=2)
scion.addIxLink(10, (1, 101), (1, 104), ScLinkType.Transit, count=2)
scion.addIxLink(10, (1, 101), (1, 105), ScLinkType.Transit, count=2)
scion.addIxLink(10, (1, 101), (1, 106), ScLinkType.Transit, count=2)
scion.addIxLink(10, (1, 101), (1, 107), ScLinkType.Transit, count=2)
scion.addIxLink(10, (1, 102), (1, 104), ScLinkType.Transit, count=2)
scion.addIxLink(10, (1, 102), (1, 105), ScLinkType.Transit, count=2)
scion.addIxLink(10, (1, 102), (1, 106), ScLinkType.Transit, count=2)
scion.addIxLink(10, (1, 102), (1, 107), ScLinkType.Transit, count=2)
scion.addIxLink(10, (1, 103), (1, 104), ScLinkType.Transit, count=2)
scion.addIxLink(10, (1, 103), (1, 105), ScLinkType.Transit, count=2)
scion.addIxLink(10, (1, 103), (1, 106), ScLinkType.Transit, count=2)
scion.addIxLink(10, (1, 103), (1, 107), ScLinkType.Transit, count=2)
scion.addIxLink(10, (1, 105), (1, 108), ScLinkType.Transit, count=2)
scion.addIxLink(10, (1, 106), (1, 109), ScLinkType.Transit, count=2)
br = create_as(1, 110, is_core=True)[1].joinNetwork('ix11')
br.crossConnect(70, 'br0', xc_nets.next_addr('70-110'))
br = create_as(1, 111, is_core=True)[1].joinNetwork('ix11')
br.crossConnect(100, 'br0', xc_nets.next_addr('100-111'))
create_as(1, 112, issuer=110)[1].joinNetwork('ix11')
create_as(1, 113, issuer=110)[1].joinNetwork('ix11')
scion.addIxLink(11, (1, 110), (1, 111), ScLinkType.Core)
scion.addIxLink(11, (1, 110), (1, 112), ScLinkType.Transit, count=2)
scion.addIxLink(11, (1, 110), (1, 113), ScLinkType.Transit, count=2)
scion.addIxLink(11, (1, 111), (1, 112), ScLinkType.Transit, count=2)
scion.addIxLink(11, (1, 111), (1, 113), ScLinkType.Transit, count=2)

# Small IXP as120-122
br = create_as(1, 120, is_core=True)[1].joinNetwork('ix12')
br.crossConnect(71, 'br0', xc_nets.next_addr('71-120'))
create_as(1, 121, issuer=120)[1].joinNetwork('ix12')
create_as(1, 122, issuer=120)[1].joinNetwork('ix12')
scion.addIxLink(12, (1, 120), (1, 121), ScLinkType.Transit, count=2)
scion.addIxLink(12, (1, 120), (1, 122), ScLinkType.Transit, count=2)

# Large content provider as200-205
br = create_as(1, 200, is_core=True)[1].joinNetwork('ix20')
br.crossConnect(70, 'br0', xc_nets.next_addr('70-200'))
br = create_as(1, 201, is_core=True)[1].joinNetwork('ix20')
br.crossConnect(50, 'br0', xc_nets.next_addr('50-201'))
create_as(1, 202, issuer=200)[1].joinNetwork('ix20').joinNetwork('ix11').joinNetwork('ix12')
create_as(1, 203, issuer=200)[1].joinNetwork('ix20').joinNetwork('ix10')
br = create_as(1, 204, issuer=200)[1].joinNetwork('ix20')
br.crossConnect(163, 'br0', xc_nets.next_addr('163-204'))
br = create_as(1, 205, issuer=200)[1].joinNetwork('ix20')
br.crossConnect(150, 'br0', xc_nets.next_addr('150-205'))
scion.addIxLink(20, (1, 200), (1, 201), ScLinkType.Core, count=2)
scion.addIxLink(20, (1, 200), (1, 202), ScLinkType.Transit)
scion.addIxLink(20, (1, 202), (1, 204), ScLinkType.Transit)
scion.addIxLink(20, (1, 201), (1, 203), ScLinkType.Transit)
scion.addIxLink(20, (1, 203), (1, 205), ScLinkType.Transit)
scion.addIxLink(11, (1, 113), (1, 202), ScLinkType.Transit, count=2)
scion.addIxLink(10, (1, 104), (1, 203), ScLinkType.Transit, count=2)
scion.addIxLink(12, (1, 122), (1, 202), ScLinkType.Transit)

# Small access network as170-171
br = create_as(1, 170, is_core=True)[1].joinNetwork('ix17')
br.crossConnect(70, 'br0', xc_nets.next_addr('70-170'))
create_as(1, 171, issuer=170)[1].joinNetwork('ix17').joinNetwork('ix11').joinNetwork('ix12')
scion.addIxLink(17, (1, 170), (1, 171), ScLinkType.Transit)
scion.addIxLink(11, (1, 112), (1, 171), ScLinkType.Transit, count=2)
scion.addIxLink(12, (1, 121), (1, 171), ScLinkType.Transit)

# Core links
scion.addXcLink((1, 50), (1, 60), ScLinkType.Core)
scion.addXcLink((1, 50), (1, 70), ScLinkType.Core, count=2)
scion.addXcLink((1, 60), (1, 70), ScLinkType.Core)
scion.addXcLink((1, 50), (1, 201), ScLinkType.Core)
scion.addXcLink((1, 60), (1, 103), ScLinkType.Core)
scion.addXcLink((1, 70), (1, 200), ScLinkType.Core)
scion.addXcLink((1, 70), (1, 110), ScLinkType.Core)
scion.addXcLink((1, 70), (1, 170), ScLinkType.Core)
scion.addXcLink((1, 100), (1, 111), ScLinkType.Core)

# Large access network as180-191
br = create_as(1, 180, is_core=True)[1].joinNetwork('ix18')
br.crossConnect(60, 'br0', xc_nets.next_addr('60-180'))
br = create_as(1, 181, issuer=180)[1].joinNetwork('ix18').joinNetwork('ix10')
br.crossConnect(51, 'br0', xc_nets.next_addr('51-181'))
br = create_as(1, 182, issuer=180)[1].joinNetwork('ix18').joinNetwork('ix10')
br = create_as(1, 183, issuer=180)[1].joinNetwork('ix18').joinNetwork('ix10')
for asn in range(184, 192):
    create_as(1, asn, issuer=180)[1].joinNetwork('ix18')
scion.addIxLink(18, (1, 180), (1, 181), ScLinkType.Transit)
scion.addIxLink(18, (1, 180), (1, 182), ScLinkType.Transit)
scion.addIxLink(18, (1, 180), (1, 183), ScLinkType.Transit)
scion.addIxLink(18, (1, 181), (1, 184), ScLinkType.Transit)
scion.addIxLink(18, (1, 181), (1, 185), ScLinkType.Transit)
scion.addIxLink(18, (1, 182), (1, 184), ScLinkType.Transit)
scion.addIxLink(18, (1, 182), (1, 185), ScLinkType.Transit)
scion.addIxLink(18, (1, 182), (1, 186), ScLinkType.Transit)
scion.addIxLink(18, (1, 183), (1, 185), ScLinkType.Transit)
scion.addIxLink(18, (1, 183), (1, 186), ScLinkType.Transit)
scion.addIxLink(18, (1, 184), (1, 187), ScLinkType.Transit)
scion.addIxLink(18, (1, 184), (1, 188), ScLinkType.Transit)
scion.addIxLink(18, (1, 184), (1, 189), ScLinkType.Transit)
scion.addIxLink(18, (1, 185), (1, 187), ScLinkType.Transit)
scion.addIxLink(18, (1, 185), (1, 188), ScLinkType.Transit)
scion.addIxLink(18, (1, 185), (1, 190), ScLinkType.Transit)
scion.addIxLink(18, (1, 185), (1, 191), ScLinkType.Transit)
scion.addIxLink(18, (1, 186), (1, 189), ScLinkType.Transit)
scion.addIxLink(18, (1, 186), (1, 190), ScLinkType.Transit)
scion.addIxLink(18, (1, 186), (1, 191), ScLinkType.Transit)
scion.addXcLink((1, 60), (1, 180), ScLinkType.Core)
scion.addXcLink((1, 51), (1, 181), ScLinkType.Transit)
scion.addIxLink(10, (1, 108), (1, 181), ScLinkType.Transit)
scion.addIxLink(10, (1, 109), (1, 182), ScLinkType.Transit)
scion.addIxLink(10, (1, 107), (1, 183), ScLinkType.Transit)

# Leaf ASes
br = create_as(1, 150, issuer=50)[1].joinNetwork('ix10')
br.crossConnect(51, 'br0', xc_nets.next_addr('51-150'))
br.crossConnect(205, 'br0', xc_nets.next_addr('150-205'))
scion.addXcLink((1, 51), (1, 150), ScLinkType.Transit)
scion.addIxLink(10, (1, 104), (1, 150), ScLinkType.Transit)
scion.addXcLink((1, 205), (1, 150), ScLinkType.Transit)

br = create_as(1, 151, issuer=50)[1].joinNetwork('ix10')
br.crossConnect(51, 'br0', xc_nets.next_addr('51-151'))
scion.addXcLink((1, 51), (1, 151), ScLinkType.Transit)
scion.addIxLink(10, (1, 104), (1, 151), ScLinkType.Transit)
scion.addIxLink(10, (1, 105), (1, 151), ScLinkType.Transit)

br = create_as(1, 152, issuer=50)[1].joinNetwork('ix10')
br.crossConnect(53, 'br0', xc_nets.next_addr('53-152'))
br.crossConnect(60, 'br0', xc_nets.next_addr('60-152'))
scion.addXcLink((1, 53), (1, 152), ScLinkType.Transit)
scion.addXcLink((1, 60), (1, 152), ScLinkType.Transit)
scion.addIxLink(10, (1, 107), (1, 152), ScLinkType.Transit)

br = create_as(1, 160, issuer=70)[1].joinNetwork('ix11').joinNetwork('ix12')
br.crossConnect(71, 'br0', xc_nets.next_addr('71-160'))
scion.addXcLink((1, 71), (1, 160), ScLinkType.Transit)
scion.addIxLink(11, (1, 112), (1, 160), ScLinkType.Transit)
scion.addIxLink(12, (1, 121), (1, 160), ScLinkType.Transit)

br = create_as(1, 161, issuer=70)[1].joinNetwork('ix12')
br.crossConnect(71, 'br0', xc_nets.next_addr('71-161'))
scion.addXcLink((1, 71), (1, 161), ScLinkType.Transit)
scion.addIxLink(12, (1, 121), (1, 161), ScLinkType.Transit)

br = create_as(1, 162, issuer=70)[1].joinNetwork('ix12')
br.crossConnect(73, 'br0', xc_nets.next_addr('73-162'))
scion.addXcLink((1, 73), (1, 162), ScLinkType.Transit)
scion.addIxLink(12, (1, 122), (1, 162), ScLinkType.Transit)

br = create_as(1, 163, issuer=70)[1].joinNetwork('ix11').joinNetwork('ix12')
br.crossConnect(73, 'br0', xc_nets.next_addr('73-163'))
br.crossConnect(204, 'br0', xc_nets.next_addr('163-204'))
scion.addXcLink((1, 73), (1, 163), ScLinkType.Transit)
scion.addXcLink((1, 204), (1, 163), ScLinkType.Transit)
scion.addIxLink(11, (1, 113), (1, 163), ScLinkType.Transit)
scion.addIxLink(12, (1, 122), (1, 163), ScLinkType.Transit)

# Rendering
emu.addLayer(base)
emu.addLayer(routing)
emu.addLayer(scion_isd)
emu.addLayer(scion)

emu.render()

# Compilation
emu.compile(Docker(), './scion')
