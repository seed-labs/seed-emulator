#!/usr/bin/env python
# encoding: utf-8
# __author__ = 'Demon'


from seedemu.services.BotnetService import BotnetService, BotnetClientService

from seedemu.core import Emulator

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


sim = Emulator()

bot_c2 = BotnetService()
bot_client = BotnetClientService()

bot_c2.install("c2_server")

for i in range(10):
    b = bot_client.install("bot"+str(i))
    b.setServer(c2_server="10.150.0.71")


sim.addLayer(bot_c2)
sim.addLayer(bot_client)

sim.dump("botnet-component.bin")