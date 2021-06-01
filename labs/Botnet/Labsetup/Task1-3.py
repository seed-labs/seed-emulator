#!/usr/bin/env python3
# encoding: utf-8

from seedsim.core import Simulator, Binding, Filter
from seedsim.services import BotnetService, BotnetClientService
from seedsim.services import DomainRegistrarService
from seedsim.compiler import Docker

sim = Simulator()

sim.load('mini-internet.bin')

bot = BotnetService()    # Create botnet service instance
bot_client = BotnetClientService() # Create botnet client service instance

base_layer = sim.getLayer('Base') #Get Base layer in base component
x = base_layer.getAutonomousSystem(150) # Get object of AS150
hosts = x.getHosts() # Get hosts list in AS150

bot.install("c2_server")
sim.addBinding(Binding("c2_server", filter = Filter(asn = 150, nodeName=hosts[0], allowBound=True)))

c2_server_ip = "10.150.0.71"

for asn in [151,152,153,154,155]:
    vname = "bot" + str(asn)
    asn_base = base_layer.getAutonomousSystem(asn)
    c = bot_client.install(vname)
    c.setServer(c2_server=c2_server_ip)
    sim.addBinding(Binding(vname, filter = Filter(asn = asn, nodeName=asn_base.getHosts()[0], allowBound=True)))

sim.addLayer(bot)
sim.addLayer(bot_client)
sim.render()

###############################################################################

sim.compile(Docker(), './Task1-2')
