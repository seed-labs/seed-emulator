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

ix100 = base.createInternetExchange(100)
ix101 = base.createInternetExchange(101)
ix102 = base.createInternetExchange(102)
ix103 = base.createInternetExchange(103)
ix104 = base.createInternetExchange(104)
ix105 = base.createInternetExchange(105)

# Customize names for a demo in a keynote speech in China
#ix100.getPeeringLan().setDisplayName('北京')
#ix101.getPeeringLan().setDisplayName('上海')
#ix102.getPeeringLan().setDisplayName('广州')
#ix103.getPeeringLan().setDisplayName('常州')
#ix104.getPeeringLan().setDisplayName('武汉')
#ix105.getPeeringLan().setDisplayName('成都')


###############################################################################
# Create Transit Autonomous Systems 

## Tier 1 ASes
make_transit_AS(base, 2, [100, 101, 102], 
       [(100, 101), (101, 102)] 
)

make_transit_AS(base, 3, [100, 103, 105], 
       [(100, 103), (103, 105), (105, 100)]
)

make_transit_AS(base, 4, [100, 104], 
       [(100, 104)]
)

## Tier 2 ASes
make_transit_AS(base, 11, [102, 105], [(102, 105)])
make_transit_AS(base, 12, [101, 104], [(101, 104)])


###############################################################################
# Create single-homed stub ASes. "None" means create a host only 

make_stub_AS(emu, base, 150, 100, [web, None])
make_stub_AS(emu, base, 151, 100, [web, None])

make_stub_AS(emu, base, 152, 101, [None, None])
make_stub_AS(emu, base, 153, 101, [web, None, None])

make_stub_AS(emu, base, 154, 102, [None, web])

make_stub_AS(emu, base, 160, 103, [web, None])
make_stub_AS(emu, base, 161, 103, [web, None])
make_stub_AS(emu, base, 162, 103, [web, None])

make_stub_AS(emu, base, 163, 104, [web, None])
make_stub_AS(emu, base, 164, 104, [None, None])

make_stub_AS(emu, base, 170, 105, [web, None])
make_stub_AS(emu, base, 171, 105, [None])


# Add a host with customized IP address to AS-154 
as154 = base.getAutonomousSystem(154)
as154.createHost('host_2').joinNetwork('net0', address = '10.154.0.129')


###############################################################################
# Peering via RS (route server). The default peering mode for RS is PeerRelationship.Peer, 
# which means each AS will only export its customers and their own prefixes. 
# We will use this peering relationship to peer all the ASes in an IX.
# None of them will provide transit service for others. 

ebgp.addRsPeers(100, [2, 3, 4])
#ebgp.addRsPeers(101, [2, 12, 152, 153])
#ebgp.addRsPeers(102, [2, 11, 154])
#ebgp.addRsPeers(103, [3, 160, 161, 162])
#ebgp.addRsPeers(104, [4, 12, 163, 164])
#ebgp.addRsPeers(105, [3, 11, 170, 171])

# To buy transit services from another autonomous system, we will use 
# private peering.  

private_peering_with_isp(ebgp, 100, 2,  [150, 151])
private_peering_with_isp(ebgp, 100, 3,  [150, 151])
private_peering_with_isp(ebgp, 100, 4,  [150, 151])

private_peering_with_isp(ebgp, 101, 2,  [12])
private_peering_with_isp(ebgp, 101, 12, [152, 153])

private_peering_with_isp(ebgp, 102, 2,  [11, 154])
private_peering_with_isp(ebgp, 102, 11, [154])

private_peering_with_isp(ebgp, 103, 3,  [160, 161, 162])

private_peering_with_isp(ebgp, 104, 4,  [12])
private_peering_with_isp(ebgp, 104, 12, [164])
# We use AS-163 the BGP attacker, it needs to use the "unfiltered" peering
private_peering_with_isp_unfiltered(ebgp, 104, 4, [163])

private_peering_with_isp(ebgp, 105, 3,  [11, 170])
private_peering_with_isp(ebgp, 105, 11, [171])


###############################################################################
# Add layers to the emulator, render and compile

emu.addLayer(base)
emu.addLayer(routing)
emu.addLayer(ebgp)
emu.addLayer(ibgp)
emu.addLayer(ospf)
emu.addLayer(web)

# Save it to a component file
emu.dump('base-component.bin')

# Generate the docker files
#emu.render()
#emu.compile(Docker(), './output')

