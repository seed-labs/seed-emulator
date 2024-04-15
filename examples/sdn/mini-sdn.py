#!/usr/bin/env python3
# encoding: utf-8

from seedemu.layers import Base, Routing, Ebgp, Ibgp, Ospf, PeerRelationship, Dnssec
from seedemu.services import WebService, DomainNameService, DomainNameCachingService
from seedemu.services import CymruIpOriginService, ReverseDomainNameService, BgpLookingGlassService
from seedemu.compiler import Docker, Graphviz
from seedemu.hooks import ResolvConfHook
from seedemu.core import Emulator, Service, Binding, Filter
from seedemu.layers import Router
from seedemu.raps import OpenVpnRemoteAccessProvider
from seedemu.utilities import Makers

from typing import List, Tuple, Dict


###############################################################################
emu     = Emulator()
base    = Base()


# ix100 = base.createInternetExchange(100)
# ix100.getPeeringLan().setDisplayName('NYC-100')

###############################################################################
# Create single-homed stub ASes. "None" means create a host only 
# Makers.makeStubAs(emu, base, 154, [None])
as154 = base.createAutonomousSystem(154)
#Create a SDN br here to support SDN for this specific autonomous system.

sdn_0 = as154.createSoftwareDefinedNetwork('sdn0', prefix= '10.154.0.0/24')

# Add a host with customized IP address to AS-154 
as154.createHost('host_a1').joinNetwork('sdn0', address='10.154.0.1')
as154.createHost('host-a2').joinNetwork('sdn0', address='10.154.0.2')

sdn_1 = as154.v('sdn1', prefix= '10.154.0.0/24')
as154.createHost('host_b1').joinNetwork('sdn1', address='10.154.1.1')
as154.createHost('host-b2').joinNetwork('sdn1', address='10.154.1.2')

sdn_2 = as154.createSoftwareDefinedNetwork('sdn2', prefix= '10.154.2.0/24')
as154.createHost('host_c1').joinNetwork('sdn2', address='10.154.2.1')
as154.createHost('host-c2').joinNetwork('sdn2', address='10.154.2.2')

#Adding bgp router on sdn3
router = as154.createRouter('router0')
router.joinNetwork('sdn2')
# router.joinNetwork('ix{}'.format(exchange))

#A regular network on the same autonomous system
as154.createNetwork('net0')
router.joinNetwork('net0')
as154.createHost('host_x1').joinNetwork('net0', address='10.154.128.1')
###############################################################################
# Another autonomous system with regular network
# stub_as = base.createAutonomousSystem(152)
# stub_as.createNetwork('net0')

# # Create a BGP router 
# # Attach the router to both the internal and external networks
# router = stub_as.createRouter('router0')
# router.joinNetwork('net0')
# router.joinNetwork('ix{}'.format(exchange))



###############################################################################

# Add layers to the emulator
emu.addLayer(base)

# Save it to a component file, so it can be used by other emulators
emu.dump('base-component.bin')

# Uncomment the following if you want to generate the final emulation files
emu.render()
emu.compile(Docker(sdnNetwork=True), './output', override=True)

