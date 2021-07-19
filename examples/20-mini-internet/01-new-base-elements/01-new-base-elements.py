from seedemu.layers import Base, Routing, Ebgp, Ibgp, Ospf, PeerRelationship, Dnssec
from seedemu.services import WebService, DomainNameService, DomainNameCachingService
from seedemu.services import CymruIpOriginService, ReverseDomainNameService, BgpLookingGlassService
from seedemu.compiler import Docker, Graphviz
from seedemu.hooks import ResolvConfHook
from seedemu.core import Emulator, Service, Binding, Filter
from seedemu.layers import Router
from typing import List, Tuple, Dict

from utility import *

###############################################################################
# Load the base component, retrieve the layer objects

emu = Emulator()
emu.load('../base-component.bin')

base: Base = emu.getLayer('Base')
web:  WebService = emu.getLayer('WebService')
routing: Routing = emu.getLayer('Routing')
ebgp: Ebgp = emu.getLayer('Ebgp')


###############################################################################
# Add a new internet exchange 

base.createInternetExchange(120)


###############################################################################
# Create three stub ASes and add the peering

make_stub_AS(emu, base, 180, 100, [web, None])
make_stub_AS(emu, base, 181, 101, [None, None])
make_stub_AS(emu, base, 182, 120, [None, None])

# Peer AS-180 publicly with others at IX-100 
ebgp.addRsPeer(100, 180)


# Peer AS-181 privately with AS-4 at IX-104 
# To be added later


# Create a new PoP for AS-2 at IX-120 and peer with AS-182

#ebgp.addRsPeers(120, [2, 181])


###############################################################################

emu.render()
emu.compile(Docker(), './output')

