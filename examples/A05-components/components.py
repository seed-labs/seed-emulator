#!/usr/bin/env python3
# encoding: utf-8

from seedemu.core import Emulator, Binding, Filter
from seedemu.layers import Base, Routing, Ebgp, PeerRelationship
from seedemu.services import WebService
from seedemu.compiler import Docker


###############################################################################
# Load the pre-built component from example 01-transit-as
# Need to go to 01-transit-as and generate the component first

emu = Emulator()
emu.load('../A01-transit-as/base-component.bin')


###############################################################################
# Demonstrating how to get the layers of the component.
# To make changes to any existing layer, we need to get the layer reference 

base: Base       = emu.getLayer('Base')
ebgp: Ebgp       = emu.getLayer('Ebgp')

web:  WebService = WebService()



###############################################################################
# Add a new host to AS-151, which is from the pre-built component

as151 = base.getAutonomousSystem(151)
as151.createHost('web-2').joinNetwork('net0')
web.install('web151-2')
emu.addBinding(Binding('web151-2', filter = Filter(nodeName = 'web-2', asn = 151)))


###############################################################################
# Add a new autonomous system (AS-154)
# This requires making changes to the base and ebgp layers.

as154 = base.createAutonomousSystem(154)
as154.createNetwork('net0')

as154.createRouter('router0').joinNetwork('net0').joinNetwork('ix100')
as154.createRouter('router1').joinNetwork('net0').joinNetwork('ix101')

as154.createHost('web').joinNetwork('net0')
web.install('web154')
emu.addBinding(Binding('web154', filter = Filter(nodeName = 'web', asn = 154)))

# Peer with AS-151 and AS-152 
ebgp.addPrivatePeering(100, 151, 154, abRelationship = PeerRelationship.Provider)
ebgp.addPrivatePeering(101, 152, 154, abRelationship = PeerRelationship.Peer)



###############################################################################
# Add a new internet exchange (IX-102) and peer AS-153 and AS-152 there.

# Create an internet exchange
base.createInternetExchange(102)

# Add a BGP router to AS-152 and connect it to IX-102
as152 = base.getAutonomousSystem(152)
as152.createRouter('router1').joinNetwork('net0').joinNetwork('ix102')

# Add a BGP router to AS-153 and connect it to IX-102
as154.createRouter('router2').joinNetwork('net0').joinNetwork('ix102')

# Peer them
ebgp.addPrivatePeering(102, 152, 154, abRelationship = PeerRelationship.Peer)



###############################################################################
# Render and compile

emu.render()
emu.compile(Docker(), './output')
