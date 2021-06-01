#!/usr/bin/env python3
# encoding: utf-8

from seedsim.core import Simulator, Binding, Filter
from seedsim.services import BotnetService, BotnetClientService
from seedsim.services import DomainRegistrarService
from seedsim.compiler import Docker

sim = Simulator()

sim.load('mini-internet.bin')

bot = BotnetService()
bot_client = BotnetClientService()
domain_registrar = DomainRegistrarService()

###########################################

def dga() -> list:
    #Generate 10 domains for the given time.
    domain_list = []
    domain = ""
    import math, datetime
    today = datetime.datetime.utcnow()
    hour = today.hour
    day = today.day
    minute = today.minute
    minute = int(math.ceil(minute/5))*5

    for i in range(16):
        day = ((day ^ 8 * day) >> 11) ^ ((day & 0xFFFFFFF0) << 17)
        hour = ((hour ^ 4 * hour) >> 25) ^ 16 * (hour & 0xFFFFFFF8)
        minute = ((minute ^ (minute << 13)) >> 19) ^ ((minute & 0xFFFFFFFE) << 12)
        domain += chr(((day ^ hour ^ minute) % 25) + 97)
        if i > 6:
            domain_list.append(domain+ ".com")

    return domain_list

##########################################
base_layer = sim.getLayer('Base')
x = base_layer.getAutonomousSystem(150)
hosts = x.getHosts()

bot.install("c2_server")
sim.addBinding(Binding("c2_server", filter = Filter(asn = 150, nodeName=hosts[0], allowBound=True)))

for asn in [151,152,153,154,155]:
    vname = "bot" + str(asn)
    asn_base = base_layer.getAutonomousSystem(asn)
    c = bot_client.install(vname)
    c.setServer(enable_dga=True, dga=dga)
    sim.addBinding(Binding(vname, filter = Filter(asn = asn, nodeName=asn_base.getHosts()[0], allowBound=True)))


domain_registrar.install("domain_registrar")
sim.addBinding(Binding("domain_registrar", filter = Filter(asn = 161, nodeName="s_com_dns",  allowBound=True)))

sim.addLayer(bot)
sim.addLayer(bot_client)
sim.addLayer(domain_registrar)
sim.render()

###############################################################################

sim.compile(Docker(), './botnet-in-mini-internet')
