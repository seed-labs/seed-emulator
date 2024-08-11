#!/usr/bin/env python3
# encoding: utf-8

from seedemu.compiler import Docker, Platform
from seedemu.core import Emulator, Binding, Filter
from seedemu.services import TrafficService, TrafficServiceType
from seedemu.layers import EtcHosts
from examples.internet.B00_mini_internet import mini_internet
import os, sys

def run(dumpfile=None):
    ###############################################################################
    # Set the platform information
    if dumpfile is None:
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

    # Run the pre-built components
    mini_internet.run(dumpfile='./base_internet.bin')
    
    # Load and merge the pre-built components 
    emu.load('./base_internet.bin')
    
    base = emu.getLayer("Base")

    etc_hosts = EtcHosts()

    traffic_service = TrafficService()
    traffic_service.install("ditg-receiver-1", TrafficServiceType.DITG_RECEIVER)
    traffic_service.install("ditg-receiver-2", TrafficServiceType.DITG_RECEIVER)
    traffic_service.install(
        "ditg-generator",
        TrafficServiceType.DITG_GENERATOR,
        log_file="/root/ditg_generator.log",
        protocol="UDP",
        duration=120,
        rate=50,
    ).addReceivers(hosts=["ditg-receiver-1", "ditg-receiver-2"])

    # Add hosts to AS-150
    as150 = base.getAutonomousSystem(150)
    as150.createHost("ditg-generator").joinNetwork("net0")

    # Add hosts to AS-162
    as162 = base.getAutonomousSystem(162)
    as162.createHost("ditg-receiver-1").joinNetwork("net0")

    # Add hosts to AS-170
    as162 = base.getAutonomousSystem(170)
    as162.createHost("ditg-receiver-2").joinNetwork("net0")

    # Binding virtual nodes to physical nodes
    emu.addBinding(
        Binding("ditg-generator", filter=Filter(asn=150, nodeName="ditg-generator"))
    )
    emu.addBinding(
        Binding("ditg-receiver-1", filter=Filter(asn=162, nodeName="ditg-receiver-1"))
    )
    emu.addBinding(
        Binding("ditg-receiver-2", filter=Filter(asn=170, nodeName="ditg-receiver-2"))
    )

    # Add the layers
    emu.addLayer(traffic_service)
    emu.addLayer(etc_hosts)

    if dumpfile is not None:
       # Save it to a file, so it can be used by other emulators
       emu.dump(dumpfile)
    else:
       # Rendering compilation 
       emu.render()
       emu.compile(Docker(platform=platform), './output', override=True)

if __name__ == "__main__":
    run()
