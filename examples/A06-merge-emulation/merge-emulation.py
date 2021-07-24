#!/usr/bin/env python3
# encoding: utf-8

from seedemu.core import Emulator
from seedemu.mergers import DEFAULT_MERGERS
from seedemu.layers import Base, Routing, Ebgp
from seedemu.compiler import Docker


###############################################################################
# Create Emulation A
# We can also load this emulation for a pre-built component

emuA     = Emulator()
baseA    = Base()
ebgpA    = Ebgp()
routingA = Routing()

# Create an internet exchange ix100
baseA.createInternetExchange(100)

# Create an autonomous system AS-150
as150 = baseA.createAutonomousSystem(150)
as150.createNetwork('net0')
as150.createHost('host0').joinNetwork('net0')
as150.createRouter('router0').joinNetwork('net0').joinNetwork('ix100')

# Peer with others at ix100
ebgpA.addRsPeer(100, 150)

# Add these layers to the emulation A
emuA.addLayer(baseA)
emuA.addLayer(routingA)
emuA.addLayer(ebgpA)

###############################################################################
# Create Emulation B
# We can also load this emulation for a pre-built component

baseB = Base()
ebgpB = Ebgp()
routingB = Routing()

# Create an autonomous system AS-150
as151 = baseB.createAutonomousSystem(151)
as151.createNetwork('net0')
as151.createHost('host0').joinNetwork('net0')
as151.createRouter('router0').joinNetwork('net0').joinNetwork('ix100')

# Peer with others at ix100
ebgpB.addRsPeer(100, 151)

# Add these layers to the emulation B
emuB = Emulator()
emuB.addLayer(baseB)
emuB.addLayer(routingB)
emuB.addLayer(ebgpB)


###############################################################################
# Merge these two emulations

emu_merged = emuA.merge(emuB, DEFAULT_MERGERS)


###############################################################################
# Generate the final emulation files

emu_merged.render()
emu_merged.compile(Docker(), './output')

