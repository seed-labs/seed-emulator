#!/usr/bin/env python3
# encoding: utf-8

from seedemu.core import Emulator, Binding, Filter, Action
from seedemu.services import BotnetService, BotnetClientService
from seedemu.compiler import Docker

emu = Emulator()

# load the pre-built component
emu.load('../B00-mini-internet/base-component.bin')

# create services for botnet controller and client
bot = BotnetService()
botClient = BotnetClientService()

# pick an IP for botnet controller
controllerIp = '10.150.0.66'

# create a virtual node for bot controller
bot.install('bot_controller')

# use binding with NEW action to create a new physical node for the controller.
emu.addBinding(Binding('bot_controller', filter = Filter(ip = controllerIp), action = Action.NEW))

for asn in [151, 152, 153, 154]:
    vname = 'bot{}'.format(asn)

    # create a virtual node for bot client
    botClient.install(vname).setServer(server = controllerIp)

    # use binding with NEW action to create a new physical node for the client.
    emu.addBinding(Binding(vname, filter = Filter(asn = asn), action = Action.NEW))

emu.addLayer(bot)
emu.addLayer(botClient)
emu.render()

###############################################################################

emu.compile(Docker(), './output')
