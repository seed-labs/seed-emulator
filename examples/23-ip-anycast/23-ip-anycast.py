#!/usr/bin/env python3
# encoding: utf-8

from seedemu.core import Emulator, Binding, Filter, Action
from seedemu.compiler import Docker
from seedemu.layers import Base, Ebgp, PeerRelationship

emu = Emulator()

# Load the pre-built components and merge them
emu.load('../20-mini-internet/base-component.bin')

# Create a new AS, AS-180, but 
base: Base = emu.getLayer('Base')
as180 = base.createAutonomousSystem(180)

as180.createNetwork('net0', '10.180.0.0/24')
as180.createHost('host-0').joinNetwork('net0', address = '10.180.0.100')
as180.createRouter('router0').joinNetwork('net0').joinNetwork('ix100')

as180.createNetwork('net1', '10.180.0.0/24')
as180.createHost('host-1').joinNetwork('net1', address = '10.180.0.100')
as180.createRouter('router1').joinNetwork('net1').joinNetwork('ix105')

# Peer with others
ebgp: Ebgp = emu.getLayer('Ebgp')
ebgp.addPrivatePeerings(100, [4],  [180], PeerRelationship.Provider)
ebgp.addPrivatePeerings(105, [3],  [180], PeerRelationship.Provider)


###############################################

emu.render()
emu.compile(Docker(selfManagedNetwork=True), './output')

