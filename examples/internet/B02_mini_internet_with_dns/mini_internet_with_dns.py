#!/usr/bin/env python3
# encoding: utf-8

from seedemu.core import Emulator, Binding, Filter, Action
from seedemu.mergers import DEFAULT_MERGERS
from seedemu.hooks import ResolvConfHook
from seedemu.compiler import Docker
from seedemu.services import DomainNameService, DomainNameCachingService
from seedemu.layers import Base
from examples.internet.B00_mini_internet import mini_internet
from examples.internet.B01_dns_component import dns_component


def run(dumpfile=None):

    emuA = Emulator()
    emuB = Emulator()

    # Run the pre-built components
    mini_internet.run(dumpfile='./base-internet.bin')
    dns_component.run(dumpfile='./dns-component.bin')
    
    # Load and merge the pre-built components 
    emuA.load('./base-internet.bin')
    emuB.load('./dns-component.bin')
    emu = emuA.merge(emuB, DEFAULT_MERGERS)
    
    
    #####################################################################################
    # Bind the virtual nodes in the DNS infrastructure layer to physical nodes.
    # Action.FIRST will look for the first acceptable node that satisfies the filter rule.
    # There are several other filters types that are not shown in this example.
    
    emu.addBinding(Binding('a-root-server', filter=Filter(asn=171), action=Action.FIRST))
    emu.addBinding(Binding('b-root-server', filter=Filter(asn=150), action=Action.FIRST))
    emu.addBinding(Binding('a-com-server', filter=Filter(asn=151), action=Action.FIRST))
    emu.addBinding(Binding('b-com-server', filter=Filter(asn=152), action=Action.FIRST))
    emu.addBinding(Binding('a-net-server', filter=Filter(asn=152), action=Action.FIRST))
    emu.addBinding(Binding('a-edu-server', filter=Filter(asn=153), action=Action.FIRST))
    emu.addBinding(Binding('ns-twitter-com', filter=Filter(asn=161), action=Action.FIRST))
    emu.addBinding(Binding('ns-google-com', filter=Filter(asn=162), action=Action.FIRST))
    emu.addBinding(Binding('ns-example-net', filter=Filter(asn=163), action=Action.FIRST))
    emu.addBinding(Binding('ns-syr-edu', filter=Filter(asn=164), action=Action.FIRST))
    
    #####################################################################################
    # Create two local DNS servers (virtual nodes).
    ldns = DomainNameCachingService()
    ldns.install('global-dns-1')
    ldns.install('global-dns-2')
    
    # Customize the display name (for visualization purpose)
    emu.getVirtualNode('global-dns-1').setDisplayName('Global DNS-1')
    emu.getVirtualNode('global-dns-2').setDisplayName('Global DNS-2')
    
    # Create two new host in AS-152 and AS-153, use them to host the local DNS server.
    # We can also host it on an existing node.
    base: Base = emu.getLayer('Base')
    as152 = base.getAutonomousSystem(152)
    as152.createHost('local-dns-1').joinNetwork('net0', address = '10.152.0.53')
    as153 = base.getAutonomousSystem(153)
    as153.createHost('local-dns-2').joinNetwork('net0', address = '10.153.0.53')
    
    # Bind the Local DNS virtual nodes to physical nodes
    emu.addBinding(Binding('global-dns-1', filter = Filter(asn=152, nodeName="local-dns-1")))
    emu.addBinding(Binding('global-dns-2', filter = Filter(asn=153, nodeName="local-dns-2")))
    
    # Add 10.152.0.53 as the local DNS server for AS-160 and AS-170
    # Add 10.153.0.53 as the local DNS server for all the other nodes
    # We can also set this for individual nodes
    base.getAutonomousSystem(160).setNameServers(['10.152.0.53'])
    base.getAutonomousSystem(170).setNameServers(['10.152.0.53'])
    base.setNameServers(['10.153.0.53'])
    
    # Add the ldns layer
    emu.addLayer(ldns)
    
    if dumpfile is not None:
       # Save it to a file, so it can be used by other emulators
       emu.dump(dumpfile)
    else:
       # Rendering compilation 
       emu.render()
       emu.compile(Docker(), './output', override=True)

if __name__ == "__main__":
    run()

