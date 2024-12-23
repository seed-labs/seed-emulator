#!/usr/bin/env python3
# encoding: utf-8

from seedemu import *
from examples.basic.A01_transit_as import transit_as
import sys, os


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

###############################################################################
# Load the pre-built component from example A01_transit_as
transit_as.run(dumpfile='./base_component.bin')

emu = Emulator()
emu.load('./base_component.bin')



###############################################################################
# Render and compile

emu.render()
emu.compile(Docker(platform=platform), './output', override=True)

