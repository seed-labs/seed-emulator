#!/usr/bin/env python3
# encoding: utf-8

from seedemu.layers import Base, Routing, Ebgp, PeerRelationship, Mpls
from seedemu.compiler import Docker, DistributedDocker, GcpDistributedDocker, Graphviz
from seedemu.services import WebService
from seedemu.core import Emulator, Binding, Filter
from os import mkdir

###############################################################################
# Load the pre-built component from example 01-transit-as
# Need to go to 01-transit-as and generate the component first

emu = Emulator()
emu.load('../A01-transit-as/base-component.bin')

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

mkdir('./output')
emu.compile(Docker(), './output/regular-docker')
emu.compile(Graphviz(), './output/graphs')
emu.compile(DistributedDocker(), './output/distributed-docker')
emu.compile(GcpDistributedDocker(), './output/gcp-distributed-docker')
