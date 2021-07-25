#!/usr/bin/env python3
# encoding: utf-8

from seedemu.core import Emulator, Binding, Filter, Action
from seedemu.services import BotnetService, BotnetClientService, DomainNameService, DomainNameCachingService
from seedemu.compiler import Docker

emu = Emulator()

emu.load('../B00-mini-internet/base-component.bin')

bot = BotnetService()
bot_client = BotnetClientService()
dns = DomainNameService()

###########################################

c2_server_ip = "10.150.0.71"

###########################################

dns.install('root').addZone('.')
dns.install('com').addZone('com.')
dns.install('attacker').addZone('attacker.com.')

###########################################

dns.getZone('attacker.com').addRecord('* A {}'.format(c2_server_ip))

###########################################

emu.addBinding(Binding('root', filter=Filter(asn=171)))
emu.addBinding(Binding('com', filter=Filter(asn=161)))
emu.addBinding(Binding('attacker', filter=Filter(asn=162)))

###########################################

ldns = DomainNameCachingService()
ldns.install('global-dns')
emu.addBinding(Binding('global-dns', filter = Filter(nodeName="gdns", ip = '10.153.0.53'), action = Action.NEW))

###########################################

# not really how it works in real-world. in real world, one would use TLD.
DGA_SCRIPT = '''\
#!/bin/bash
for i in {1..10}; do echo "$RANDOM.attacker.com"; done
'''

##########################################
base_layer = emu.getLayer('Base')
base_layer.setNameServers(['10.153.0.53'])

x = base_layer.getAutonomousSystem(150)
hosts = x.getHosts()

bot.install("c2_server")
emu.addBinding(Binding("c2_server", filter = Filter(ip = c2_server_ip, allowBound=True)))

for asn in [151,152,153,154,160]:
    vname = "bot" + str(asn)
    asn_base = base_layer.getAutonomousSystem(asn)
    c = bot_client.install(vname)
    c.setDga(DGA_SCRIPT)
    emu.addBinding(Binding(vname, filter = Filter(asn = asn, nodeName=asn_base.getHosts()[0], allowBound=True)))



emu.addLayer(bot)
emu.addLayer(bot_client)
emu.addLayer(dns)
emu.addLayer(ldns)
emu.render()

###############################################################################

emu.compile(Docker(), './output')
