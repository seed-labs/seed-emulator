#!/usr/bin/env python3
# encoding: utf-8

from seedemu.compiler import Docker
from seedemu.core import Binding, Emulator, Filter, Action
from seedemu.layers import Base
from seedemu.services import DomainNameService, CAService, WebService, WebServer, RootCAStore
from basenetwithDNS import dump

emu = Emulator()
basenet = dump()
emu.load(basenet)

base: Base = emu.getLayer('Base')
dns: DomainNameService = emu.getLayer('DomainNameService')

caStore = RootCAStore(caDomain='ca.internal')
ca = CAService(caStore)
web = WebService()

ca.setCertDuration("2160h")

# Add records to zones
dns.getZone('ca.internal.').addRecord('@ A 10.150.0.7')
dns.getZone('user1.internal.').addRecord('@ A 10.151.0.7')
dns.getZone('user2.internal.').addRecord('@ A 10.151.0.8')

ca.install('ca-vnode')
ca.installCACert()

as150 = base.getAutonomousSystem(150)
# Do not install the CA cert on the CA host
host_ca = as150.createHost('ca').joinNetwork('net0', address='10.150.0.7')

as151 = base.getAutonomousSystem(151)
host_web = as151.createHost('web1').joinNetwork('net0', address='10.151.0.7')
host_web = as151.createHost('web2').joinNetwork('net0', address='10.151.0.8')

webServer1: WebServer = web.install('web1-vnode')
webServer1.setServerNames(['user1.internal'])
webServer1.useCAService(ca).enableHTTPS()
webServer2: WebServer = web.install('web2-vnode')
webServer2.setServerNames(['user2.internal'])
webServer2.useCAService(ca).enableHTTPS()
emu.addBinding(Binding('ca-vnode', filter=Filter(nodeName='ca'), action=Action.FIRST))
emu.addBinding(Binding('web1-vnode', filter=Filter(nodeName='web1'), action=Action.FIRST))
emu.addBinding(Binding('web2-vnode', filter=Filter(nodeName='web2'), action=Action.FIRST))

emu.addLayer(ca)
emu.addLayer(web)

emu.render()
emu.compile(Docker(), './output', override=True)
