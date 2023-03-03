#!/usr/bin/env python3

from seedemu.compiler import Docker, Graphviz
from seedemu.core import Emulator, Binding, Filter
from seedemu.layers import ScionBase, ScionRouting, Ospf, ScionIsd, Scion
from seedemu.layers.Scion import LinkType as ScLinkType
from seedemu.services import ScionBwtestServerService

# Initialize
emu = Emulator()
base = ScionBase()
routing = ScionRouting()
ospf = Ospf()
scion_isd = ScionIsd()
scion = Scion()
bwtest_server = ScionBwtestServerService()

# SCION ISDs
base.createIsolationDomain(1)

# ASes
as150 = base.createAutonomousSystem(150)
as151 = base.createAutonomousSystem(151)
as152 = base.createAutonomousSystem(152)

as150_router = as150.createRouter('br1')
as151_router = as151.createRouter('br1')
as152_router = as152.createRouter('br1')

as150.createNetwork('net0')
as151.createNetwork('net0')
as152.createNetwork('net0')

as150.createControlService('cs1').joinNetwork('net0')
as151.createControlService('cs1').joinNetwork('net0')
as152.createControlService('cs1').joinNetwork('net0')

as150_router.joinNetwork('net0')
as151_router.joinNetwork('net0')
as152_router.joinNetwork('net0')


scion_isd.addIsdAs(1, 150, is_core=True)
scion_isd.addIsdAs(1, 151, is_core=False)
scion_isd.addIsdAs(1, 152, is_core=False)

scion_isd.setCertIssuer((1, 151), issuer=150)
scion_isd.setCertIssuer((1, 152), issuer=150)

as150_router.crossConnect(151, 'br1', '10.150.254.2/29')
as150_router.crossConnect(152, 'br1', '10.150.253.2/29')
as151_router.crossConnect(150, 'br1', '10.150.254.3/29')
as152_router.crossConnect(150, 'br1', '10.150.253.3/29')

# Bandwidth Test Service
as150.createHost('bwtest_server').joinNetwork('net0', address='10.150.0.30')
# Setting the port only has to be done if the default value of 40002 should not be used
bwtest_server.install('bwtest_server').setPort(40000)
emu.addBinding(Binding('bwtest_server', filter = Filter(nodeName='bwtest_server', asn=150)))

# BGP Peering
scion.addXcLink((1, 150), (1, 151), ScLinkType.Transit)
scion.addXcLink((1, 150), (1, 152), ScLinkType.Transit)

# Rendering
emu.addLayer(base)
emu.addLayer(routing)
emu.addLayer(ospf)
emu.addLayer(scion_isd)
emu.addLayer(scion)
emu.addLayer(bwtest_server)

emu.render()

# Compilation
emu.compile(Docker(), './output')
emu.compile(Graphviz(), "./output/graphs")
