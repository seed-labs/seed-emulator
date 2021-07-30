#!/usr/bin/env python3
# encoding: utf-8

from seedemu.core import Emulator, Binding, Filter, Action
from seedemu.services import BotnetService, BotnetClientService
from seedemu.compiler import Docker

emu = Emulator()

# Load the pre-built component
emu.load('../B00-mini-internet/base-component.bin')

###############################################################################
# Build a botnet

# Create services for botnet controller and client
bot = BotnetService()
botClient = BotnetClientService()

# Pick an IP for botnet controller
controllerIp = '10.150.0.66'

# Create a virtual node for bot controller,
# and add a file to this node
f = open("./ddos.py", "r")
bot.install('bot_controller').addFile(f.read(), "/tmp/ddos.py")

# Bind the virtual node to a physical node (create a new one)
emu.addBinding(Binding('bot_controller', filter = Filter(ip = controllerIp), action = Action.NEW))

for asn in [151, 152, 153, 154]:
    vname = 'bot{}'.format(asn)

    # Create a virtual node for each bot client
    botClient.install(vname).setServer('bot_controller')

    # Bind the virtual node to a physical node (new)
    emu.addBinding(Binding(vname, filter = Filter(asn = asn), action = Action.NEW))

###############################################################################

emu.addLayer(bot)
emu.addLayer(botClient)
emu.render()

###############################################################################
# Customize the display names of the controller and bots.

emu.getBindingFor('bot_controller').setDisplayName('Bot-Controller'.format(asn))
for asn in [151, 152, 153, 154]:
    vname = 'bot{}'.format(asn)
    emu.getBindingFor(vname).setDisplayName('Bot-{}'.format(asn))

###############################################################################

emu.compile(Docker(), './output')
