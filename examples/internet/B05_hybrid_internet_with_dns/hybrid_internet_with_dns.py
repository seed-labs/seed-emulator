#!/usr/bin/env python3
# encoding: utf-8

from seedemu.core import Emulator, Binding, Filter, Action
from seedemu.mergers import DEFAULT_MERGERS
from seedemu.compiler import Docker, Platform
from seedemu.services import DomainNameCachingService
from seedemu.layers import Base
from examples.internet.B03_hybrid_internet import hybrid_internet
from examples.internet.B04_hybrid_dns_component import hybrid_dns_component
import os, sys

def run(dumpfile = None):
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

    emuA = Emulator()
    emuB = Emulator()

    # Run, load, and merge the pre-built components
    hybrid_internet.run(dumpfile='./base_hybrid_component.bin')
    hybrid_dns_component.run(dumpfile='./hybrid_dns_component.bin')
    emuA.load('./base_hybrid_component.bin')
    emuB.load('./hybrid_dns_component.bin')
    emu = emuA.merge(emuB, DEFAULT_MERGERS)

    #####################################################################################
    # Bind the virtual nodes in the DNS infrastructure layer to physical nodes.
    # Action.FIRST will look for the first acceptable node that satisfies the filter rule.
    # There are several other filters types that are not shown in this example.

    emu.addBinding(Binding('a-root-server', filter=Filter(asn=171), action=Action.FIRST))
    emu.addBinding(Binding('ns-google-com', filter=Filter(asn=153), action=Action.FIRST))
    emu.addBinding(Binding('ns-twitter-com', filter=Filter(asn=161), action=Action.FIRST))
    #####################################################################################

    #####################################################################################
    # Create a local DNS servers (virtual nodes).
    # Add forward zone so that the DNS queries from emulator can be forwarded to the emulator's Nameserver not the real ones.
    ldns = DomainNameCachingService()
    ldns.install('global-dns-1').addForwardZone('google.com.', 'ns-google-com').addForwardZone('twitter.com.', 'ns-twitter-com')

    # Customize the display name (for visualization purpose)
    emu.getVirtualNode('global-dns-1').setDisplayName('Global DNS-1')

    # Create a new host in AS-153, use it to host the local DNS server.
    # We can also host it on an existing node.
    base: Base = emu.getLayer('Base')
    as153 = base.getAutonomousSystem(153)
    as153.createHost('local-dns-1').joinNetwork('net0', address = '10.153.0.53')

    # Bind the Local DNS virtual nodes to physical nodes
    emu.addBinding(Binding('global-dns-1', filter = Filter(asn=153, nodeName="local-dns-1")))

    # Add 10.153.0.53 as the local DNS server for all the other nodes
    base.setNameServers(['10.153.0.53'])

    # Add the ldns layer
    emu.addLayer(ldns)

    if dumpfile is not None:
        emu.dump(dumpfile)
    else:
        emu.render()
        emu.compile(Docker(platform=platform), './output', override=True)

if __name__ == "__main__":
    run()
