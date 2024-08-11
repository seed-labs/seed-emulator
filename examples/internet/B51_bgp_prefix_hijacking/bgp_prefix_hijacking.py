#!/usr/bin/env python3
# encoding: utf-8

from seedemu.core import Emulator
from seedemu.compiler import Docker, Platform
from seedemu.layers import Base, Ebgp, PeerRelationship
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

emu = Emulator()

# Run and load the pre-built component
mini_internet.run(dumpfile='./base_internet.bin')
emu.load('./base_internet.bin')

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
emu.compile(Docker(platform=platform), './output', override=True)
