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
emu     = Emulator()
base    = Base()
routing = Routing()
ebgp    = Ebgp()
ibgp    = Ibgp()
ospf    = Ospf()
web     = WebService()

###############################################################################

base.createInternetExchange(100)
base.createInternetExchange(101)
base.createInternetExchange(102)
base.createInternetExchange(103)
base.createInternetExchange(104)
base.createInternetExchange(105)

###############################################################################
# Create Transit Autonomous Systems 

## Tier 1 ASes
make_transit_AS(base, routing, 2, [100, 101, 102], 
       [(100, 101), (101, 102)] 
)

make_transit_AS(base, routing, 3, [100, 103, 105], 
       [(100, 103), (103, 105), (105, 100)]
)

make_transit_AS(base, routing, 4, [100, 104], 
       [(100, 104)]
)

## Tier 2 ASes
make_transit_AS(base, routing, 11, [102, 105], [(102, 105)])
make_transit_AS(base, routing, 12, [101, 104], [(101, 104)])


###############################################################################
# Create Stub ASes. "None" means create a host only 

make_stub_AS(emu, base, routing, 151, 100, [web])
make_stub_AS(emu, base, routing, 150, 101, [web, None])
make_stub_AS(emu, base, routing, 170, 101, [None, None])
make_stub_AS(emu, base, routing, 152, 102, [web])
make_stub_AS(emu, base, routing, 153, 102, [web])
make_stub_AS(emu, base, routing, 160, 103, [web, web])
make_stub_AS(emu, base, routing, 161, 103, [web])
make_stub_AS(emu, base, routing, 162, 103, [web])
make_stub_AS(emu, base, routing, 154, 104, [web])
make_stub_AS(emu, base, routing, 155, 105, [web])
make_stub_AS(emu, base, routing, 171, 105, [])

# Add a host with customized IP address to AS154 
as154 = base.getAutonomousSystem(154)
as154.createHost('host_0').joinNetwork('net0', address = '10.154.0.129')



###############################################################################
# Peering: using router server 
# I made changes to the Ebgp.py code, changing the default peering relationship to "Unfiltered"
# (a_export, b_export) = self.__getExportFilters(reg, ix, peer, PeerRelationship.Unfiltered)

ebgp.addRsPeers(100, [2, 3, 4, 151])
ebgp.addRsPeers(101, [2, 12, 150, 170])
ebgp.addRsPeers(102, [2, 11, 152, 153])
ebgp.addRsPeers(103, [3, 160, 161, 162])
ebgp.addRsPeers(104, [4, 12, 154])
ebgp.addRsPeers(105, [3, 11, 155, 171])


###############################################################################
# Add layers to the emulator, render and compile

emu.addLayer(base)
emu.addLayer(routing)
emu.addLayer(ebgp)
emu.addLayer(ibgp)
emu.addLayer(ospf)
emu.addLayer(web)

emu.render()

emu.compile(Docker(), './output')
#emu.compile(Graphviz(), './output/_graphs')
