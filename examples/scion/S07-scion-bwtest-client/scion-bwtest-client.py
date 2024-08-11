#!/usr/bin/env python3

from seedemu.compiler import Docker
from seedemu.core import Emulator, Binding, Filter
from seedemu.layers import ScionBase, ScionRouting, ScionIsd, Scion
from seedemu.layers.Scion import LinkType as ScLinkType
from seedemu.services import ScionBwtestService, ScionBwtestClientService

# Initialize
emu = Emulator()
base = ScionBase()
routing = ScionRouting()
scion_isd = ScionIsd()
scion = Scion()
bwtest = ScionBwtestService()
bwtestclient = ScionBwtestClientService()

# SCION ISDs
base.createIsolationDomain(1)

# AS-150
as150 = base.createAutonomousSystem(150)
scion_isd.addIsdAs(1, 150, is_core=True)
as150.createNetwork('net0')
as150.createControlService('cs1').joinNetwork('net0')
as150_router = as150.createRouter('br0').joinNetwork('net0')
as150_router.crossConnect(151, 'br0', '10.50.0.10/29', latency=10, bandwidth=1000000, packetDrop=0.01)
as150_router.crossConnect(152, 'br0', '10.50.0.18/29')
as150_router.crossConnect(153, 'br0', '10.50.0.3/29')

# Create a host running the bandwidth test server
as150.createHost('bwtest').joinNetwork('net0', address='10.150.0.30')
bwtest.install('bwtest150').setPort(40002) # Setting the port is optional (40002 is the default)
emu.addBinding(Binding('bwtest150', filter=Filter(nodeName='bwtest', asn=150)))

# AS-151
as151 = base.createAutonomousSystem(151)
scion_isd.addIsdAs(1, 151, is_core=True)
as151.createNetwork('net0')
as151.createControlService('cs1').joinNetwork('net0')
as151_br0 = as151.createRouter('br0').joinNetwork('net0').addSoftware("iperf3")
as151_br0.crossConnect(150, 'br0', '10.50.0.11/29', latency=10, bandwidth=1000000, packetDrop=0.01)
as151_br0.crossConnect(152, 'br0', '10.50.0.26/29')

as151.createHost('bwtest').joinNetwork('net0', address='10.151.0.30')
bwtest.install('bwtest151')
emu.addBinding(Binding('bwtest151', filter=Filter(nodeName='bwtest', asn=151)))

# AS-152
as152 = base.createAutonomousSystem(152)
scion_isd.addIsdAs(1, 152, is_core=True)
as152.createNetwork('net0')
as152.createControlService('cs1').joinNetwork('net0')
as152_br0 = as152.createRouter('br0').joinNetwork('net0')
as152_br0.crossConnect(150, 'br0', '10.50.0.19/29')
as152_br0.crossConnect(151, 'br0', '10.50.0.27/29')

as152.createHost('bwtest').joinNetwork('net0', address='10.152.0.30')
bwtest.install('bwtest152')
emu.addBinding(Binding('bwtest152', filter=Filter(nodeName='bwtest', asn=152)))

# AS-153
as153 = base.createAutonomousSystem(153)
scion_isd.addIsdAs(1, 153, is_core=False)
scion_isd.setCertIssuer((1, 153), issuer=150)
as153.createNetwork('net0')
as153.createControlService('cs1').joinNetwork('net0')
as153_router = as153.createRouter('br0')
as153_router.joinNetwork('net0')
as153_router.crossConnect(150, 'br0', '10.50.0.4/29')

as153.createHost('bwtestserver').joinNetwork('net0', address='10.153.0.30')
bwtest.install('bwtest153')
emu.addBinding(Binding('bwtest153', filter=Filter(nodeName='bwtestserver', asn=153)))

# AS-153 bwtestclient
as153.createHost('bwtestclient').joinNetwork('net0', address='10.153.0.31').addSharedFolder("/var/log", "/absolute/path/to/logs/on/host") # make logs of bwtestclient available on host
bwtestclient.install('bwtestclient153').setServerAddr('1-151,10.151.0.30').setWaitTime(20) # set the server address and time to wait before starting the test
emu.addBinding(Binding('bwtestclient153', filter=Filter(nodeName='bwtestclient', asn=153)))

# Inter-AS routing
scion.addXcLink((1, 150), (1, 151), ScLinkType.Core)
scion.addXcLink((1, 150), (1, 152), ScLinkType.Core)
scion.addXcLink((1, 151), (1, 152), ScLinkType.Core)
scion.addXcLink((1, 150), (1, 153), ScLinkType.Transit)

# Rendering
emu.addLayer(base)
emu.addLayer(routing)
emu.addLayer(scion_isd)
emu.addLayer(scion)
emu.addLayer(bwtest)
emu.addLayer(bwtestclient)

emu.render()

# Compilation
emu.compile(Docker(internetMapEnabled=True), './output')
