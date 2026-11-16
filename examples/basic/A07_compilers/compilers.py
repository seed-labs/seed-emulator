#!/usr/bin/env python3
# encoding: utf-8

from seedemu.compiler import Docker, DistributedDocker, GcpDistributedDocker, Graphviz, Platform
from seedemu.core import Emulator
import os, sys
from examples.basic.A01_transit_as import transit_as
from seedemu.containerBundle import InternetMap

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
# Load the pre-built component from example 01-transit-as
transit_as.run(dumpfile='./base_component.bin')

emu = Emulator()
emu.load('./base_component.bin')

###############################################################################
# Render the emulation

emu.render()


###############################################################################
# The Registry keeps track of every important objects created in the 
# emulation (nodes, layers, networks, files, etc.)
# We can print out these objects 

print(emu.getRegistry())

###############################################################################
# Compile the emulation
script_dir = os.path.dirname(os.path.abspath(__file__))
output_dir = os.path.join(script_dir, 'output')
os.makedirs(output_dir, exist_ok=True)
docker = Docker(platform=platform)
# Add Internet visualization services: topology, geographic map, and traffic observation.
# The second argument is a container name suffix that distinguishes bundle instances.
internet_map_bundle = InternetMap(emu, ".map.seed")
# Provide a host port pool (range excludes the stop value); InternetMap needs at least 3 ports.
internet_map_bundle.setPorts(list(range(8081, 8089)))
# Register the bundle with the Docker compiler to generate its containers during emu.compile().
docker.addContainerBundle(internet_map_bundle)
emu.compile(docker, './output/regular-docker', override=True)
emu.compile(Graphviz(), './output/graphs', override=True)
emu.compile(DistributedDocker(), './output/distributed-docker', override=True)
emu.compile(GcpDistributedDocker(), './output/gcp-distributed-docker', override=True)