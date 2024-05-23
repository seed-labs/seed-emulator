#!/usr/bin/env python3
# encoding: utf-8

from seedemu.compiler import Docker
from seedemu.layers import Base, EtcHosts
from seedemu.core import Emulator

emu = Emulator()
etc_hosts = EtcHosts()

# Load the pre-built mini-internet component
emu.load('../../mini_internet/emulator-code/base-component.bin')

# Create a new host in AS-152 with custom host name
base: Base = emu.getLayer('Base')
as152 = base.getAutonomousSystem(152)
as152.createHost('database').joinNetwork('net0', address = '10.152.0.4').addHostName('database.com')

# Add the etc_hosts layer
emu.addLayer(etc_hosts)

# Render the emulation and further customization
emu.render()
emu.compile(Docker(), './output')
