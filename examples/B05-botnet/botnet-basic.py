#!/usr/bin/env python3
# encoding: utf-8

from seedemu.core import Emulator, Binding, Filter
from seedemu.services import BotnetService, BotnetClientService
from seedemu.services import DomainRegistrarService
from seedemu.compiler import Docker

emu = Emulator()

emu.load('../B00-mini-internet/base-component.bin')

bot = BotnetService()    # Create botnet service instance
bot_client = BotnetClientService() # Create botnet client service instance

base = emu.getLayer('Base') 
hosts = base.getAutonomousSystem(150).getHosts() 

bot.install("c2_server")
emu.addBinding(Binding("c2_server", filter = Filter(asn = 150, nodeName=hosts[0], allowBound=True)))

c2_server_ip = "10.150.0.71"

for asn in [151,152,153,154]:
    vname = "bot" + str(asn)
    asn_base = base.getAutonomousSystem(asn)
    c = bot_client.install(vname)
    c.setServer(c2_server=c2_server_ip)
    emu.addBinding(Binding(vname, filter = Filter(asn=asn, nodeName=asn_base.getHosts()[0], allowBound=True)))

emu.addLayer(bot)
emu.addLayer(bot_client)
emu.render()

###############################################################################

emu.compile(Docker(), './output')
