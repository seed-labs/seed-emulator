#!/usr/bin/env python3
# encoding: utf-8

from seedemu import *
from examples.internet.B00_mini_internet import mini_internet
import os, sys

###############################################################################
# Set the platform information
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

mini_internet.run(dumpfile='./base_internet.bin')

emu = Emulator()

# Load the pre-built component
emu.load('./base_internet.bin')

base:Base = emu.getLayer('Base')

# Create a DHCP server (virtual node).
dhcp = DHCPService()

# Default DhcpIpRange : x.x.x.101 ~ x.x.x.120
# Set DhcpIpRange : x.x.x.125 ~ x.x.x.140
dhcp.install('dhcp-01').setIpRange(125, 140)
dhcp.install('dhcp-02')


# Customize the display name (for visualization purpose)
emu.getVirtualNode('dhcp-01').setDisplayName('DHCP Server 1')
emu.getVirtualNode('dhcp-02').setDisplayName('DHCP Server 2')


# Create new hosts in AS-151 and AS-161, use them to host the DHCP servers.
# We can also host it on an existing node.
as151 = base.getAutonomousSystem(151)
as151.createHost('dhcp-server-01').joinNetwork('net0')

as161 = base.getAutonomousSystem(161)
as161.createHost('dhcp-server-02').joinNetwork('net0')

# Bind the DHCP virtual node to the physical node.
emu.addBinding(Binding('dhcp-01', filter = Filter(asn=151, nodeName='dhcp-server-01')))
emu.addBinding(Binding('dhcp-02', filter = Filter(asn=161, nodeName='dhcp-server-02')))


# Create new hosts in AS-151 and AS-161
# Make them to use dhcp instead of static ip
as151.createHost('dhcp-client-01').joinNetwork('net0', address = "dhcp")
as151.createHost('dhcp-client-02').joinNetwork('net0', address = "dhcp")

as161.createHost('dhcp-client-03').joinNetwork('net0', address = "dhcp")
as161.createHost('dhcp-client-04').joinNetwork('net0', address = "dhcp")

# Add the dhcp layer
emu.addLayer(dhcp)

# Render the emulation
emu.render()

# Compil the emulation
emu.compile(Docker(platform=platform), './output', override=True)