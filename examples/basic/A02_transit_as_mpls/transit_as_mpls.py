#!/usr/bin/env python3
# encoding: utf-8

from seedemu.layers import Base, Routing, Ebgp, PeerRelationship, Mpls
from seedemu.services import WebService
from seedemu.core import Emulator, Binding, Filter
from seedemu.compiler import Docker, Platform
import sys, os

###############################################################################
# Set the platform information
script_name = os.path.basename(__file__)

if len(sys.argv) == 1:
    platform = Platform.AMD64
elif len(sys.argv) == 2:
    if sys.argv[1].lower() == 'amd':
        platform = Platform.AMD64
    elif sys.argv[1].lower() == 'arm':
        platform = Platform.ARM64
    else:
        print(f"Usage:  {script_name} amd|arm")
        sys.exit(1)
else:
    print(f"Usage:  {script_name} amd|arm")
    sys.exit(1)

emu = Emulator()

base = Base()
routing = Routing()
ebgp = Ebgp()
mpls = Mpls()
web = WebService()

###############################################################################

base.createInternetExchange(100)
base.createInternetExchange(101)

###############################################################################
# Create and set up the transit AS (AS-150)

as150 = base.createAutonomousSystem(150)

# Create 3 internal networks
as150.createNetwork('net0')
as150.createNetwork('net1')
as150.createNetwork('net2')

# Create four routers and link them in a linear structure:
# ix100 <--> r1 <--> r2 <--> r3 <--> r4 <--> ix101
# r1 and r2 are BGP routers because they are connected to internet exchanges
as150.createRouter('r1').joinNetwork('net0').joinNetwork('ix100')
as150.createRouter('r2').joinNetwork('net0').joinNetwork('net1')
as150.createRouter('r3').joinNetwork('net1').joinNetwork('net2')
as150.createRouter('r4').joinNetwork('net2').joinNetwork('ix101')

# Enable MPLS 
mpls.enableOn(150)

###############################################################################
# Create and set up the stub AS (AS-151)

as151 = base.createAutonomousSystem(151)

# Create an internal network and a router
as151.createNetwork('net0')
as151.createRouter('router0').joinNetwork('net0').joinNetwork('ix100')

# Create a web-service node 
as151.createHost('web').joinNetwork('net0')
web.install('web151')
emu.addBinding(Binding('web151', filter = Filter(nodeName = 'web', asn = 151)))


###############################################################################
# Create and set up the stub AS (AS-152)

as152 = base.createAutonomousSystem(152)
as152.createNetwork('net0')
as152.createRouter('router0').joinNetwork('net0').joinNetwork('ix101')

as152_web = as152.createHost('web').joinNetwork('net0')
web.install('web152')
emu.addBinding(Binding('web152', filter = Filter(nodeName = 'web', asn = 152)))


###############################################################################
# Make AS-150 the internet service provider for AS-151 and AS-152
ebgp.addPrivatePeering(100, 150, 151, abRelationship = PeerRelationship.Provider)
ebgp.addPrivatePeering(101, 150, 152, abRelationship = PeerRelationship.Provider)

###############################################################################

emu.addLayer(base)
emu.addLayer(routing)
emu.addLayer(ebgp)
emu.addLayer(mpls)
emu.addLayer(web)

emu.render()

###############################################################################

emu.compile(Docker(platform=platform), './output', override=True)
