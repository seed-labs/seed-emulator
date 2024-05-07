#!/usr/bin/env python3
# encoding: utf-8

from seedemu.compiler import Docker
from seedemu.core import Binding, Emulator, Filter, Action
from seedemu.layers import Base
from seedemu.services import DomainNameService, CAService, WebService, WebServer, RootCAStore
import base_internet

base_internet.run(dumpfile='./base-internet.bin')

emu = Emulator()
emu.load('./base-internet.bin')

base: Base = emu.getLayer('Base')

# Create a physical node for CA servers
as150 = base.getAutonomousSystem(150)
as150.createHost('ca').joinNetwork('net0').addHostName('seedCA.net')

# Create two physical nodes for web servers
as151 = base.getAutonomousSystem(151)
as151.createHost('web1').joinNetwork('net0', address='10.151.0.7') \
                        .addHostName('example32.com')
as151.createHost('web2').joinNetwork('net0', address='10.151.0.8') \
                        .addHostName('bank32.com')

# Create and configure CA server vnodes
caStore = RootCAStore(caDomain='seedCA.net')
ca  = CAService(caStore)
ca.setCertDuration("2160h")
ca.install('ca-vnode')
ca.installCACert()

# Create and configure web server vnodes
web = WebService()
webServer1: WebServer = web.install('web1-vnode')
webServer1.setServerNames(['example32.com'])
webServer1.useCAService(ca).enableHTTPS()
webServer1.setIndexContent("<h1>Web server at example32.com</h1>")

webServer2: WebServer = web.install('web2-vnode')
webServer2.setServerNames(['bank32.com'])
webServer2.useCAService(ca).enableHTTPS()
webServer2.setIndexContent("<h1>Web server at bank32.com</h1>")

# Bind vnodes to physical nodes
emu.addBinding(Binding('ca-vnode', filter=Filter(nodeName='ca'), action=Action.FIRST))
emu.addBinding(Binding('web1-vnode', filter=Filter(nodeName='web1'), action=Action.FIRST))
emu.addBinding(Binding('web2-vnode', filter=Filter(nodeName='web2'), action=Action.FIRST))


# Add layers, render and compile 
emu.addLayer(ca)
emu.addLayer(web)

emu.render()
emu.compile(Docker(), './output', override=True)
