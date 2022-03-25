#!/usr/bin/env python3
# encoding: utf-8

from ipaddress import ip_address
from seedemu import *

emu = Emulator()

# Load the pre-built component

# (1) mini-internet-with-dns
emu.load('../../B02-mini-internet-with-dns/base_with_dns.bin')

# (2) nano-internet without dns
#emu.load('../../A20-nano-internet/base-component.bin')

base:Base = emu.getLayer('Base')

# Create a DHCP server (virtual node).
dhcp = DHCPService()

# Default DhcpIpRange : x.x.x.101 ~ x.x.x.120
# Set DhcpIpRange : x.x.x.125 ~ x.x.x.140
dhcp.install('dhcp-01')

# Customize the display name (for visualization purpose)
emu.getVirtualNode('dhcp-01').setDisplayName('DHCP Server')

# Create new host in AS-151, use it to host the DHCP server.
# We can also host it on an existing node.
as151 = base.getAutonomousSystem(151)
as151.createHost('dhcp-server').joinNetwork('net0')

# Create new host in AS-151, use it to host the Host which use dhcp instead of static ip
as151.createHost('dhcp-client').joinNetwork('net0', address = "dhcp")

# Defulat HostIpRange : x.x.x.71 - x.x.x.99
# Set HostIpRange : x.x.x.90 - x.x.x.99
# We can also change DhcpIpRange and RouterIpRange with the same way.
as151.getNetwork('net0').setHostIpRange(90, 99, 1)

# Bind the DHCP virtual node to the physical node.
emu.addBinding(Binding('dhcp-01', filter = Filter(asn=151, nodeName='dhcp-server')))

# Add the dhcp layer
emu.addLayer(dhcp)

# Render the emulation
emu.render()

# Compil the emulation
emu.compile(Docker(), './output', override=True)