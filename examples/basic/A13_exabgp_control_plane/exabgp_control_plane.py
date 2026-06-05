#!/usr/bin/env python3
# encoding: utf-8

from seedemu.layers import Base, Routing
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
exabgp = ExaBgpService()

base.createInternetExchange(100)

as2 = base.createAutonomousSystem(2)
as2.createNetwork("net0")
as2.createRouter("router0").joinNetwork("net0").joinNetwork("ix100")

as180 = base.createAutonomousSystem(180)
as180.createHost("exabgp").joinNetwork("ix100", address="10.100.0.180").addPort(exabgp_dashboard_port, 5000)

exabgp.install("as180_exabgp") \
    .setLocalAsn(180) \
    .addPeer("router0", router_asn=2, router_relationship="customer") \
    .addAnnouncement("198.51.100.0/24")
emu.addBinding(Binding("as180_exabgp", filter=Filter(asn=180, nodeName="exabgp")))

emu.addLayer(base)
emu.addLayer(routing)
emu.addLayer(exabgp)

emu.render()
emu.compile(Docker(platform=platform), output_dir, override=True)
