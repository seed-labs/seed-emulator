#!/usr/bin/env python3
# encoding: utf-8

from seedemu.core import Emulator, Binding, Filter, Action
from seedemu.mergers import DEFAULT_MERGERS
from seedemu.hooks import ResolvConfHook
from seedemu.compiler import Docker
from seedemu.services import DomainNameService, DomainNameCachingService
from seedemu.layers import Base

emuA = Emulator()
emuB = Emulator()

# Load the pre-built components and merge them
emuA.load('../base-component.bin')
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
emu.addBinding(Binding('a-cn-server', filter=Filter(asn=154), action=Action.FIRST))
emu.addBinding(Binding('b-cn-server', filter=Filter(asn=160), action=Action.FIRST))
emu.addBinding(Binding('ns-twitter-com', filter=Filter(asn=161), action=Action.FIRST))
emu.addBinding(Binding('ns-google-com', filter=Filter(asn=162), action=Action.FIRST))
emu.addBinding(Binding('ns-example-net', filter=Filter(asn=163), action=Action.FIRST))
emu.addBinding(Binding('ns-syr-edu', filter=Filter(asn=164), action=Action.FIRST))
emu.addBinding(Binding('ns-weibo-cn', filter=Filter(asn=170), action=Action.FIRST))

#####################################################################################
# Create a local DNS server (virtual node). We will use this server
# as the local DNS server for all the nodes in the emulator.
ldns = DomainNameCachingService()
ldns.install('global-dns')

# Create a new host in AS-153, use it to host the local DNS server.
# We can also host it on an existing node.
base: Base = emu.getLayer('Base')
as153 = base.getAutonomousSystem(153)
as153.createHost('local-dns').joinNetwork('net0', address = '10.153.0.53')
emu.addBinding(Binding('global-dns', filter = Filter(asn=153, nodeName="local-dns")))

# Add 10.153.0.53 as the local DNS server for all the nodes in the emulation
# We need to use the hook approach, because this setting is added to a container
# as the container boots up, so we cannot add it when building the container.
# Using the hook approach, we can run commands on a container after it starts.
emu.addHook(ResolvConfHook(['10.153.0.53']))

# Add the ldns layer
emu.addLayer(ldns)

# Dump to a file
emu.dump('base_with_dns.bin')


###############################################
# Render the emulation and further customization
emu.render()

# After the rendering, we can now find the physical node for 
# a given virtual node, and further customize the physical node.
emu.getBindingFor('a-root-server').setDisplayName('A-Root')
emu.getBindingFor('b-root-server').setDisplayName('B-Root')
emu.getBindingFor('a-com-server').setDisplayName('A-COM')
emu.getBindingFor('b-com-server').setDisplayName('B-COM')
emu.getBindingFor('a-net-server').setDisplayName('NET')
emu.getBindingFor('a-edu-server').setDisplayName('EDU')
emu.getBindingFor('a-cn-server').setDisplayName('A-CN')
emu.getBindingFor('b-cn-server').setDisplayName('B-CN')
emu.getBindingFor('ns-twitter-com').setDisplayName('Twitter')
emu.getBindingFor('ns-google-com').setDisplayName('Google')
emu.getBindingFor('ns-example-net').setDisplayName('Example')
emu.getBindingFor('ns-syr-edu').setDisplayName('Syracuse')
emu.getBindingFor('ns-weibo-cn').setDisplayName('微博')

emu.getBindingFor('global-dns').setDisplayName('Global DNS')


###############################################
# Render the emulation

emu.compile(Docker(), './output')

