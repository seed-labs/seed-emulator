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
    """Generate 10 domains for the given time."""
    domain_list = []
    domain = ""
    import math, datetime
    today = datetime.datetime.utcnow()
    year = today.year
    month = today.month
    minute = today.minute
    minute = int(math.ceil(minute/5))*5

    for i in range(16):
        year = ((year ^ 8 * year) >> 11) ^ ((year & 0xFFFFFFF0) << 17)
        month = ((month ^ 4 * month) >> 25) ^ 16 * (month & 0xFFFFFFF8)
        minute = ((minute ^ (minute << 13)) >> 19) ^ ((minute & 0xFFFFFFFE) << 12)
        domain += chr(((year ^ month ^ minute) % 25) + 97)
        if i > 6:
            domain_list.append(domain+ ".com")

    return domain_list

##########################################
reg = sim.getRegistry()

c2_server_ip = "10.150.0.71"
for ((scope, type, name), object) in reg.getAll().items():
    if type != 'hnode': continue
    host: Node = object
    if host.getAsn() == 150 and "webservice" in host.getName():
        bot.installByName(150, host.getName())

    elif host.getAsn() in [151,152]:
        c = bot_client.installByName(host.getAsn(), host.getName())
        c.setServer(c2_server_ip, enable_dga=True, dga=dga)
    elif 's_com_dns' in host.getName():
        domain_registrar.installOn(host)
#
#
#
sim.addLayer(bot)
sim.addLayer(domain_registrar)
sim.render()

###############################################################################

sim.compile(Docker(), './botnet-in-mini-internet')