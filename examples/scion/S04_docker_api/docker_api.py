#!/usr/bin/env python3

import time

import docker
import python_on_whales

from seedemu.compiler import Docker
from seedemu.core import Emulator, Binding, Filter
from seedemu.layers import ScionBase, ScionRouting, ScionIsd, Scion
from seedemu.layers.Scion import LinkType as ScLinkType
from seedemu.services import ScionBwtestService


# Initialize
emu = Emulator()
base = ScionBase()
routing = ScionRouting()
scion_isd = ScionIsd()
scion = Scion()
bwtest = ScionBwtestService()

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
as150.createHost('bwtest').joinNetwork('net0', address='10.150.0.30')
bwtest.install('bwtest150').setPort(40002) # Setting the port is optional (40002 is the default)
emu.addBinding(Binding('bwtest150', filter=Filter(nodeName='bwtest', asn=150)))

# AS-151
as151 = base.createAutonomousSystem(151)
scion_isd.addIsdAs(1, 151, is_core=True)
as151.createNetwork('net0')
as151.createControlService('cs1').joinNetwork('net0')
as151.createRouter('br0').joinNetwork('net0').joinNetwork('ix100')

as151.createHost('bwtest').joinNetwork('net0', address='10.151.0.30')
bwtest.install('bwtest151')
emu.addBinding(Binding('bwtest151', filter=Filter(nodeName='bwtest', asn=151)))

# AS-152
as152 = base.createAutonomousSystem(152)
scion_isd.addIsdAs(1, 152, is_core=True)
as152.createNetwork('net0')
as152.createControlService('cs1').joinNetwork('net0')
as152.createRouter('br0').joinNetwork('net0').joinNetwork('ix100')

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
as153_router.crossConnect(150, 'br0', '10.50.0.3/29')

as153.createHost('bwtest').joinNetwork('net0', address='10.153.0.30')
bwtest.install('bwtest153')
emu.addBinding(Binding('bwtest153', filter=Filter(nodeName='bwtest', asn=153)))

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
emu.addLayer(bwtest)

emu.render()

# Compilation
emu.compile(Docker(), './output')

# Build Docker containers and run the network
whales = python_on_whales.DockerClient(compose_files=["./output/docker-compose.yml"])
whales.compose.build()
whales.compose.up(detach=True)

# Use Docker SDK to interact with the containers
client: docker.DockerClient = docker.from_env()
ctrs = {ctr.name: client.containers.get(ctr.id) for ctr in whales.compose.ps()}

time.sleep(10) # Give SCION some time
for name, ctr in ctrs.items():
    if "bwtest" not in name:
        continue
    print("Run bwtest in", name, end="")
    ec, output = ctr.exec_run("scion-bwtestclient -s 1-150,10.150.0.30:40002")
    for line in output.decode('utf8').splitlines():
        print("  " + line)

# Shut the network down
whales.compose.down()
