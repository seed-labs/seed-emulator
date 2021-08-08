#!/usr/bin/env python3
# encoding: utf-8

from seedemu.core import Emulator, Binding, Filter, Action
from seedemu.services import BotnetService, BotnetClientService, DomainNameService, DomainNameCachingService
from seedemu.compiler import Docker

emu = Emulator()

# load the pre-built component
emu.load('../B00-mini-internet/base-component.bin')

# create services for botnet controller and client
bot = BotnetService()
botClient = BotnetClientService()

# create services for DNS, so we can use DGA
dns = DomainNameService()
ldns = DomainNameCachingService()

# pick an IP for botnet controller
controllerIp = '10.150.0.71'

# make a script that output candidate domain names.
# not really how it works in real-world. in real world, one would probably use TLD.
DGA_SCRIPT = '''\
#!/bin/bash
for i in {1..10}; do echo "$RANDOM.attacker.com:446"; done
'''

# points *.attacker.com to botnet controller - our "DGA" generates xxxx.attacker.com.
dns.getZone('attacker.com').addRecord('* A {}'.format(controllerIp))

# build a mini dns infrastructure: step 1: create zones
dns.install('root').addZone('.')
dns.install('com').addZone('com.')
dns.install('attacker').addZone('attacker.com.')

# mini dns infra: step 2: bind zone servers to physical nodes
emu.addBinding(Binding('root', filter = Filter(asn = 171)))
emu.addBinding(Binding('com', filter = Filter(asn = 161)))
emu.addBinding(Binding('attacker', filter = Filter(asn = 162)))

# mini dns infra: step 3: create a recursive server
ldns.install('global-dns')
emu.addBinding(Binding('global-dns', filter = Filter(nodeName = 'gdns', ip = '10.153.0.53'), action = Action.NEW))

# mini dns infra: step 4: make everyone use the said recursive server
emu.getLayer('Base').setNameServers(['10.153.0.53'])

# create and bind bot controller
bot.install('bot_controller')
emu.addBinding(Binding('bot_controller', filter = Filter(ip = controllerIp, allowBound = True)))

# create and bind bot clients
for asn in [151, 152, 153, 154, 160]:
    vname = 'bot{}'.formt(asn)
    botClient.install(vname).setDga(DGA_SCRIPT)
    emu.addBinding(Binding(vname, filter = Filter(asn = asn, allowBound = True)))

emu.addLayer(bot)
emu.addLayer(botClient)
emu.addLayer(dns)
emu.addLayer(ldns)
emu.render()

emu.compile(Docker(), './output2')
