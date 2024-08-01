#!/usr/bin/env python3
# encoding: utf-8

from seedemu.compiler import Docker, Platform
from seedemu.core import Binding, Emulator, Filter, Action
from seedemu.layers import Base
from seedemu.services import CAService, CAServer, WebService, WebServer, RootCAStore
import base_internet
import os, sys

###############################################################################
# Set the platform information
script_name = os.path.basename(__file__)

if len(sys.argv) == 1:
    platform = Platform.AMD64
elif len(sys.argv) == 2:
    if sys.argv[1].lower() == 'amd':
        platform = Platform.AMD64
    elif sys.argv[1].lower() == 'arm':
        platform = Platform.ARM64
    else:
        print(f"Usage:  {script_name} amd|arm")
        sys.exit(1)
else:
    print(f"Usage:  {script_name} amd|arm")
    sys.exit(1)

base_internet.run(dumpfile='./base_internet.bin')

emu = Emulator()
emu.load('./base_internet.bin')

base: Base = emu.getLayer('Base')

# Create a physical node for CA servers
as150 = base.getAutonomousSystem(150)
as150.createHost('ca1').joinNetwork('net0').addHostName('seedCA.net')
as150.createHost('ca2').joinNetwork('net0').addHostName('seedCA.com')

# Create two physical nodes for web servers
as151 = base.getAutonomousSystem(151)
as151.createHost('web1').joinNetwork('net0', address='10.151.0.7') \
                        .addHostName('example32.com')
as151.createHost('web2').joinNetwork('net0', address='10.151.0.8') \
                        .addHostName('bank32.com')

# Create and configure CA server vnodes
caStore1 = RootCAStore(caDomain='seedCA.net')
caStore2 = RootCAStore(caDomain='seedCA.com')
ca  = CAService()
caServer1: CAServer = ca.install('ca1-vnode')
caServer1.setCAStore(caStore1)
caServer1.setCertDuration("2160h")
caServer1.installCACert()

caServer2: CAServer = ca.install('ca2-vnode')
caServer2.setCAStore(caStore2)
caServer2.setCertDuration("2160h")
caServer2.installCACert()

# Create and configure web server vnodes
web = WebService()
webServer1: WebServer = web.install('web1-vnode')
webServer1.setServerNames(['example32.com'])
webServer1.setCAServer(caServer1).enableHTTPS()
webServer1.setIndexContent("<h1>Web server at example32.com</h1>")

webServer2: WebServer = web.install('web2-vnode')
webServer2.setServerNames(['bank32.com'])
webServer2.setCAServer(caServer2).enableHTTPS()
webServer2.setIndexContent("<h1>Web server at bank32.com</h1>")

# Bind vnodes to physical nodes
emu.addBinding(Binding('ca1-vnode', filter=Filter(nodeName='ca1'), action=Action.FIRST))
emu.addBinding(Binding('ca2-vnode', filter=Filter(nodeName='ca2'), action=Action.FIRST))
emu.addBinding(Binding('web1-vnode', filter=Filter(nodeName='web1'), action=Action.FIRST))
emu.addBinding(Binding('web2-vnode', filter=Filter(nodeName='web2'), action=Action.FIRST))


# Add layers, render and compile 
emu.addLayer(ca)
emu.addLayer(web)

emu.render()
emu.compile(Docker(platform=platform), './output', override=True)
