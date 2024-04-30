#!/usr/bin/env python3
# encoding: utf-8

from seedemu.core import Emulator, Binding, Filter, Action
from seedemu.compiler import Docker
from seedemu.layers import Base, Ebgp, PeerRelationship
from examples.internet.B00_mini_internet import mini_internet

mini_internet.run(dumpfile='./base-internet.bin')

emu = Emulator()

# Load the pre-built component
emu.load('./base-internet.bin')
base: Base = emu.getLayer('Base')
ebgp: Ebgp = emu.getLayer('Ebgp')

# Create a new AS as the BGP attacker 
as199 = base.createAutonomousSystem(199)
as199.createNetwork('net0')
as199.createHost('host-0').joinNetwork('net0')

# Attach it to ix-105 and peer with AS-2
as199.createRouter('router0').joinNetwork('net0').joinNetwork('ix105')
ebgp.addPrivatePeerings(105, [2],  [199], PeerRelationship.Provider)


###############################################
emu.render()
emu.compile(Docker(), './output')
