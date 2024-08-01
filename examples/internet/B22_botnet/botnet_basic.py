#!/usr/bin/env python3
# encoding: utf-8

import random
from seedemu.core import Emulator, Binding, Filter, Action
from seedemu.services import BotnetService, BotnetClientService
from seedemu.compiler import Docker, Platform
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

mini_internet.run(dumpfile='./base_internet.bin')

emu = Emulator()

# Load the pre-built component
emu.load('./base_internet.bin')

###############################################################################
# Build a botnet

# Create two service layers
bot = BotnetService()
botClient = BotnetClientService()

# Create a virtual node for bot controller,
# and customize its display name 
bot.install('bot-controller')
emu.getVirtualNode('bot-controller').setDisplayName('Bot-Controller')

# Install a file to this node
f = open("./ddos.py", "r")
emu.getVirtualNode('bot-controller').setFile(content=f.read(), path="/tmp/ddos.py")

# Create 6 bot nodes
for counter in range(6):
    vname = 'bot-node-%.3d'%(counter)

    # Create a virtual node for each bot client,
    # tell them which node is the controller node,
    # and customize its display name.
    botClient.install(vname).setServer('bot-controller')
    emu.getVirtualNode(vname).setDisplayName('Bot-%.3d'%(counter))


###############################################################################
# Bind the virtual nodes to physical nodes

# Bind the controller node 
emu.addBinding(Binding('bot-controller', 
               filter = Filter(ip='10.150.0.66'), action=Action.NEW))

as_list = [150, 151, 152, 153, 154, 160, 161, 162, 163, 164, 170, 171]
for counter in range(6):
    vname = 'bot-node-%.3d'%(counter)

    # Pick an autonomous system randomly from the list,
    # and create a new host for each bot. 
    asn = random.choice(as_list)
    emu.addBinding(Binding(vname, filter=Filter(asn=asn), action=Action.NEW))


###############################################################################

emu.addLayer(bot)
emu.addLayer(botClient)

emu.render()
emu.compile(Docker(platform=platform), './output', override=True)
