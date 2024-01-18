#!/usr/bin/env python3

from seedemu.compiler import Docker,Graphviz
from seedemu.core import Emulator, Binding, Filter
from seedemu.layers import ScionBase, ScionRouting, ScionIsd, Scion
from seedemu.layers.Scion import LinkType as ScLinkType
from seedemu.services import ContainerDevelopmentService

# Initialize
emu = Emulator()
base = ScionBase()
routing = ScionRouting()
scion_isd = ScionIsd()
scion = Scion()
devsvc = ContainerDevelopmentService()

# SCION ISDs
base.createIsolationDomain(1)

# Internet Exchange
base.createInternetExchange(100)

# AS-150
as150 = base.createAutonomousSystem(150)
scion_isd.addIsdAs(1, 150, is_core=True)
as150.createNetwork('net0')
as150.createControlService('cs1').joinNetwork('net0')
as150_router = as150.createRouter('br0')
as150_router.joinNetwork('net0').joinNetwork('ix100')
as150_router.crossConnect(153, 'br0', '10.50.0.2/29')

# Create a host running the bandwidth test server
as150.createHost('node150_0').joinNetwork('net0', address='10.150.0.30')

devsvc.install('dev_peer150_0').addVSCodeExtension('golang.Go').checkoutRepo('https://github.com/scionproto/scion','/home/root/repos/scion','master')

emu.addBinding(Binding('dev_peer150_0', filter=Filter(nodeName='node150_0', asn=150)))


# AS-151
as151 = base.createAutonomousSystem(151)
scion_isd.addIsdAs(1, 151, is_core=True)
as151.createNetwork('net0')
as151.createControlService('cs1').joinNetwork('net0')
as151.createRouter('br0').joinNetwork('net0').joinNetwork('ix100')

as151.createHost('node151_0').joinNetwork('net0', address='10.151.0.30')
devsvc.install('dev_peer151_0').addVSCodeExtension('golang.Go').checkoutRepo('https://github.com/scionproto/scion','/home/root/repos/scion','master')

emu.addBinding(Binding('dev_peer151_0', filter=Filter(nodeName='node151_0', asn=151,allowBound=True)))

# AS-152
as152 = base.createAutonomousSystem(152)
scion_isd.addIsdAs(1, 152, is_core=True)
as152.createNetwork('net0')
as152.createControlService('cs1').joinNetwork('net0')
as152.createRouter('br0').joinNetwork('net0').joinNetwork('ix100')

as152.createHost('node152_0').joinNetwork('net0', address='10.152.0.30')
emu.addBinding(Binding('peer152_0', filter=Filter(nodeName='node152_0', asn=152)))

# AS-153
as153 = base.createAutonomousSystem(153)
scion_isd.addIsdAs(1, 153, is_core=False)
scion_isd.setCertIssuer((1, 153), issuer=150)
as153.createNetwork('net0')
as153.createControlService('cs1').joinNetwork('net0')
as153_router = as153.createRouter('br0')
as153_router.joinNetwork('net0')
as153_router.crossConnect(150, 'br0', '10.50.0.3/29')

as153.createHost('node153_0').joinNetwork('net0', address='10.153.0.30')
emu.addBinding(Binding('peer153_0', filter=Filter(nodeName='node153_0', asn=153)))

# Inter-AS routing
scion.addIxLink(100, (1, 150), (1, 151), ScLinkType.Core)
scion.addIxLink(100, (1, 151), (1, 152), ScLinkType.Core)
scion.addIxLink(100, (1, 152), (1, 150), ScLinkType.Core)
scion.addXcLink((1, 150), (1, 153), ScLinkType.Transit)

# Rendering
emu.addLayer(base)
emu.addLayer(routing)
emu.addLayer(scion_isd)
emu.addLayer(scion)
emu.addLayer(devsvc)

emu.render()

# Compilation
emu.compile(Docker(), './output')
emu.compile(Graphviz(), './output/graphs')
