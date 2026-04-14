#!/usr/bin/env python3
# encoding: utf-8

from seedemu.layers import Base, Routing, Ebgp, PeerRelationship
from seedemu.services import ExaBgpService
from seedemu.core import Emulator, Binding, Filter
from seedemu.compiler import Docker, Platform
import sys, os


script_name = os.path.basename(__file__)
output_dir = os.path.join(os.path.dirname(__file__), "output")
exabgp_dashboard_port = int(os.environ.get("SEED_A13_EXABGP_PORT", "5001"))

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
exabgp = ExaBgpService()

base.createInternetExchange(100)

as2 = base.createAutonomousSystem(2)
as2.createNetwork("net0")
as2.createRouter("router0").joinNetwork("net0").joinNetwork("ix100")

as151 = base.createAutonomousSystem(151)
as151.createNetwork("net0")
as151.createRouter("router0").joinNetwork("net0").joinNetwork("ix100")
as151.createHost("control-plane-tool").joinNetwork("net0").addPortForwarding(exabgp_dashboard_port, 5000)

ebgp.addPrivatePeering(100, 2, 151, abRelationship=PeerRelationship.Provider)

exabgp.install("exabgp_tool") \
    .attachToRouter("router0") \
    .setLocalAsn(65010) \
    .addAnnouncement("198.51.100.0/24") \
    .enableDashboard(5000)

emu.addBinding(Binding("exabgp_tool", filter=Filter(nodeName="control-plane-tool", asn=151)))

emu.addLayer(base)
emu.addLayer(routing)
emu.addLayer(ebgp)
emu.addLayer(exabgp)

emu.render()
emu.compile(Docker(platform=platform), output_dir, override=True)
