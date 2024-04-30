#!/usr/bin/env python3
# encoding: utf-8

from seedemu.core import Emulator, Binding, Filter, Action
from seedemu.compiler import Docker
from seedemu.layers import Base, Ebgp, PeerRelationship

emu = Emulator()

# Load the pre-built component
emu.load('../B00-mini-internet/base-component.bin')
base: Base = emu.getLayer('Base')
ebgp: Ebgp = emu.getLayer('Ebgp')

# Create a new AS with two disjoint networks, but the
# IP prefix of these two networks are the same.
as180 = base.createAutonomousSystem(180)
as180.createNetwork('net0', '10.180.0.0/24')
as180.createNetwork('net1', '10.180.0.0/24')

# Create a host on each network, but assign them the same IP address
as180.createHost('host-0').joinNetwork('net0', address = '10.180.0.100')
as180.createHost('host-1').joinNetwork('net1', address = '10.180.0.100')

# Attach one network to IX-100 (via BGP router)
# Peer AS-180 with AS-3 and AS-4
as180.createRouter('router0').joinNetwork('net0').joinNetwork('ix100')
ebgp.addPrivatePeerings(100, [3, 4],  [180], PeerRelationship.Provider)

# Attach the other network to IX-105 (via a different BGP router)
# Peer AS-180 with AS-2 and AS-3
as180.createRouter('router1').joinNetwork('net1').joinNetwork('ix105')
ebgp.addPrivatePeerings(105, [2, 3],  [180], PeerRelationship.Provider)


###############################################
emu.render()

# We need to set the selfManagedNetwork option to True (see README)
emu.compile(Docker(selfManagedNetwork=True), './output')

