#!/usr/bin/env python3
# encoding: utf-8


from MiniInternet import reg, renderer, Node, docker_compiler, dns
from seedsim.layers import BotnetService
from seedsim.layers import DomainRegistrarService
import datetime

bot = BotnetService()
domain_registrar = DomainRegistrarService()


###########################################

def dga() -> list:
    """Generate 10 domains for the given time."""
    domain_list = []
    domain = ""
    import math, datetime
    today = datetime.datetime.today()
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
c2_server_ip = "10.150.0.71"
for ((scope, type, name), object) in reg.getAll().items():
    if type != 'hnode': continue
    host: Node = object
    if host.getAsn() == 150:
        bot.installC2(host)
        c2_server_ip == format(host.getInterfaces()[0].getAddress())
    elif host.getAsn() in [151,152]:
        bot.installBot(node=host, C2ServerIp=c2_server_ip, dga=dga)
    elif 's_com_dns' in host.getName():
        domain_registrar.installOn(host)



renderer.addLayer(bot)
renderer.addLayer(domain_registrar)
renderer.render()

docker_compiler.compile('./botnet-in-mini-internet')