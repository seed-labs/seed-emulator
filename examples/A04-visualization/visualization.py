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

base: Base = emu.getLayer('Base')


###############################################################################
# Add meta data to elements. This is for visualization.

as151 = base.getAutonomousSystem(151)
as151.getRouter('router0').setDisplayName('AS151 Core Router')
as151.getHost('web').setDisplayName('example.com')

ix100_lan = base.getInternetExchange(100).getPeeringLan()
ix100_lan.setDisplayName('Seattle').setDescription('The Seattle Internet Exchange')

ix101_lan = base.getInternetExchange(101).getPeeringLan()
ix101_lan.setDisplayName('New York')


###############################################################################
# Render and compile

emu.render()
emu.compile(Docker(), './output')
