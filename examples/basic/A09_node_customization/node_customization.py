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
# Demonstrating how to customize a node

base  = emu.getLayer('Base')

# Get the instances of the AS and node objects
as152 = base.getAutonomousSystem(152)
node  = as152.getHost('host0')

# Dockerfile: RUN apt-get update && apt-get install -y 
#                     --no-install-recommends python3
node.addSoftware("python3")

# Dockerfile: RUN curl http://example.com
node.addBuildCommand("curl http://example.com")

# Create a file on the node; file content come from hostpath
# Dockerfile: COPY 0a1fa965b6af40555d9b54e6693b2af1 /myprog.py
node.importFile(hostpath="/tmp/myprog.py",
                containerpath="/myprog.py")

# Create a file on the node; file content is the provided string
# Dockerfile: COPY 0ca69acb643ae682dd700b7c190b2564 /file.txt
node.setFile(path="/file.txt", content="hello world")

# Add "ping 1.2.3.4" to start.sh
node.insertStartCommand(0, "ping 1.2.3.4")

# Add "python3 /myprog.py &" to start.sh
node.appendStartCommand("python3 /myprog.py", fork=True)

###############################################################################
# Render and compile

emu.render()
emu.compile(Docker(platform=platform), './output', override=True)
