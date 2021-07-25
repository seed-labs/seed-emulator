#!/usr/bin/env python3
# encoding: utf-8

from seedemu.core import Emulator, Binding, Filter
from seedemu.services import BotnetService, BotnetClientService
from seedemu.services import DomainRegistrarService
from seedemu.compiler import Docker

emu = Emulator()

emu.load('../B00-mini-internet/base-component.bin')

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
base_layer = emu.getLayer('Base')
x = base_layer.getAutonomousSystem(150)
hosts = x.getHosts()

bot.install("c2_server")
emu.addBinding(Binding("c2_server", filter = Filter(asn = 150, nodeName=hosts[0], allowBound=True)))

for asn in [151,152,153,154,160]:
    vname = "bot" + str(asn)
    asn_base = base_layer.getAutonomousSystem(asn)
    c = bot_client.install(vname)
    c.setServer(enable_dga=True, dga=dga)
    emu.addBinding(Binding(vname, filter = Filter(asn = asn, nodeName=asn_base.getHosts()[0], allowBound=True)))


domain_registrar.install("domain_registrar")
emu.addBinding(Binding("domain_registrar", filter = Filter(asn = 161, nodeName="s_com_dns",  allowBound=True)))

emu.addLayer(bot)
emu.addLayer(bot_client)
emu.addLayer(domain_registrar)
emu.render()

###############################################################################

emu.compile(Docker(), './output')
