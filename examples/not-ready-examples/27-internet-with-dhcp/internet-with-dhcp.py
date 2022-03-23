#!/usr/bin/env python3
# encoding: utf-8

from ipaddress import ip_address
from seedemu import *

emu = Emulator()

# Load the pre-built component

# (1) mini-internet-with-dns
#emu.load('../../B02-mini-internet-with-dns/base_with_dns.bin')

# (2) nano-internet without dns
emu.load('../../A20-nano-internet/base-component.bin')

base:Base = emu.getLayer('Base')

# Create a DHCP server (virtual node).
dhcp = DHCPService()

# default ip range : x.x.x.20 ~ x.x.x.60
# set ip range to : x.x.x.30 ~ x.x.x.70
dhcp.install('dhcp-01').setIpRange(30, 70)

# Customize the display name (for visualization purpose)
emu.getVirtualNode('dhcp-01').setDisplayName('DHCP Server')

# Create new host in AS-151, use it to host the DHCP server.
# We can also host it on an existing node.
as151 = base.getAutonomousSystem(151)
as151.createHost('dhcp-server').joinNetwork('net0')

# Bind the DHCP virtual node to the physical node.
emu.addBinding(Binding('dhcp-01', filter = Filter(asn=151, nodeName='dhcp-server')))

# Add the dhcp layer
emu.addLayer(dhcp)

# Render the emulation
emu.render()

# Compil the emulation
emu.compile(Docker(), './output', override=True)