#!/usr/bin/env python3
# encoding: utf-8

from seedemu.core import Emulator, Binding, Filter, Action
from seedemu.mergers import DEFAULT_MERGERS
from seedemu.hooks import ResolvConfHook
from seedemu.compiler import Docker
from seedemu.services import DomainNameService, DomainNameCachingService, DomainNameCachingServer
from seedemu.layers import Base

emuA = Emulator()
emuB = Emulator()

# Load the pre-built components and merge them
emuA.load('../C00-hybrid-internet/base-component.bin')
emuB.load('../C01-hybrid-dns-component/hybrid-dns-component.bin')
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

# Dump to a file
emu.dump('hybrid_base_with_dns.bin')


###############################################
# Render the emulation and further customization
emu.render()

###############################################
# Render the emulation

emu.compile(Docker(), './output', override=True)

