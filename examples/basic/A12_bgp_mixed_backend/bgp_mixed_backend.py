#!/usr/bin/env python3
# encoding: utf-8

from seedemu.layers import Base, Routing, Ebgp, PeerRelationship, Ospf, Ibgp
from seedemu.services import WebService
from seedemu.core import Emulator, Binding, Filter
from seedemu.compiler import Docker, Platform
import sys, os


script_name = os.path.basename(__file__)
output_dir = os.path.join(os.path.dirname(__file__), "output")

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
ospf = Ospf()
ibgp = Ibgp()
ebgp = Ebgp()
web = WebService()

base.createInternetExchange(100)
base.createInternetExchange(101)

# Transit provider with two internal routers.
as2 = base.createAutonomousSystem(2)
as2.createNetwork("net0")
as2.createRouter("r1").joinNetwork("net0").joinNetwork("ix100")
as2.createRouter("r2", routingBackend="frr").joinNetwork("net0").joinNetwork("ix101")

# Stub customers on both edges.
as151 = base.createAutonomousSystem(151)
as151.createNetwork("net0")
as151.createRouter("router0", routingBackend="frr").joinNetwork("net0").joinNetwork("ix100")
as151.createHost("web").joinNetwork("net0")

as152 = base.createAutonomousSystem(152)
as152.createNetwork("net0")
as152.createRouter("router0").joinNetwork("net0").joinNetwork("ix101")
as152.createHost("web").joinNetwork("net0")

web.install("web151")
emu.addBinding(Binding("web151", filter=Filter(nodeName="web", asn=151)))
web.install("web152")
emu.addBinding(Binding("web152", filter=Filter(nodeName="web", asn=152)))

ebgp.addPrivatePeering(100, 2, 151, abRelationship=PeerRelationship.Provider)
ebgp.addPrivatePeering(101, 2, 152, abRelationship=PeerRelationship.Provider)

emu.addLayer(base)
emu.addLayer(routing)
emu.addLayer(ospf)
emu.addLayer(ibgp)
emu.addLayer(ebgp)
emu.addLayer(web)

emu.render()
emu.compile(Docker(platform=platform), output_dir, override=True)
