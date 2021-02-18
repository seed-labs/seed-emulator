#!/usr/bin/env python3
# encoding: utf-8


from seedsim.core import Simulator
from seedsim.services import BotnetService, BotnetClientService
from seedsim.services import DomainRegistrarService
from seedsim.compiler import Docker
import datetime

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
c2_server_ip = "10.150.0.71"

bot.installByName(150, hosts[0])

for asn in [151,152,153,154,155]:
    asn_base = base_layer.getAutonomousSystem(asn)
    c = bot_client.installByName(asn, asn_base.getHosts()[0])
    c.setServer(c2_server_ip, enable_dga=True, dga=dga)


domain_registrar.installByName(161, "s_com_dns")

sim.addLayer(bot)
sim.addLayer(bot_client)
sim.addLayer(domain_registrar)
sim.render()

###############################################################################

sim.compile(Docker(), './botnet-in-mini-internet')
