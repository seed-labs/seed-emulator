#!/usr/bin/env python3

from seedemu.compiler import Docker, Graphviz
from seedemu.core import Emulator, Binding, Filter
from seedemu.layers import ScionBase, ScionRouting, ScionIsd, Scion, Ospf
from seedemu.layers.Scion import LinkType as ScLinkType
from seedemu.services import ScionSIGService



# Initialize
emu = Emulator()
base = ScionBase()
routing = ScionRouting()
scion_isd = ScionIsd()
scion = Scion()
ospf = Ospf()
sig = ScionSIGService()

# SCION ISDs
base.createIsolationDomain(1)

# Internet Exchange
base.createInternetExchange(100)

# AS-150
as150 = base.createAutonomousSystem(150)
scion_isd.addIsdAs(1, 150, is_core=True)
as150.createNetwork('net0')
as150_cs = as150.createControlService('cs1').joinNetwork('net0')
as150_router = as150.createRouter('br0')
as150_router.joinNetwork('net0').joinNetwork('ix100')
as150_router.crossConnect(153, 'br0', '10.50.0.2/29')


# node with node_name has to exist before its possible to create sig config
as150.createHost("sig0").joinNetwork('net0')

as150.setSigConfig(sig_name="sig0",node_name="sig0",other_ia=(1,153), local_net = "172.16.11.0/24", remote_net = "172.16.12.0/24")
config = as150.getSigConfig("sig0")

sig.install("sig150").setConfig("sig0",config)
emu.addBinding(Binding('sig150', filter=Filter(nodeName='sig0', asn=150)))



# AS-151
as151 = base.createAutonomousSystem(151)
scion_isd.addIsdAs(1, 151, is_core=True)
as151.createNetwork('net0')
as151.createControlService('cs1').joinNetwork('net0')
as151_router = as151.createRouter('br0').joinNetwork('net0').joinNetwork('ix100')

as151.createHost("sig").joinNetwork('net0')

# there has to be a host with node name in AS
as151.setSigConfig(sig_name="sig0",node_name="sig", other_ia=(1,153), local_net = "172.16.14.0/24", remote_net = "172.16.13.0/24")

config = as151.getSigConfig("sig0")


sig.install("sig151").setConfig("sig0",config)
emu.addBinding(Binding('sig151', filter=Filter(nodeName='sig', asn=151)))

# AS-152
as152 = base.createAutonomousSystem(152)
scion_isd.addIsdAs(1, 152, is_core=True)
as152.createNetwork('net0')
as152.createControlService('cs1').joinNetwork('net0')
as152.createRouter('br0').joinNetwork('net0').joinNetwork('ix100')

# AS-153
as153 = base.createAutonomousSystem(153)
scion_isd.addIsdAs(1, 153, is_core=False)
scion_isd.setCertIssuer((1, 153), issuer=150)
as153.createNetwork('net0')
as153_cs = as153.createControlService('cs1').joinNetwork('net0')
as153_router = as153.createRouter('br0')
as153_router.joinNetwork('net0')
as153_router.crossConnect(150, 'br0', '10.50.0.3/29')

as153.createHost("sig").joinNetwork('net0')

as153.setSigConfig(sig_name="sig0",node_name="sig", other_ia=(1,150), local_net = "172.16.12.0/24", remote_net = "172.16.11.0/24")
as153.setSigConfig(sig_name="sig1",node_name="sig", other_ia=(1,151), local_net = "172.16.13.0/24", remote_net = "172.16.14.0/24", ctrl_port=30260, data_port=30261, probe_port=30857)

config_sig0 = as153.getSigConfig("sig0")
config_sig1 = as153.getSigConfig("sig1")


sig.install("sig153").setConfig(sig_name="sig0",config=config_sig0)
sig.install("sig153").setConfig(sig_name="sig1",config=config_sig1)

emu.addBinding(Binding('sig153', filter=Filter(nodeName='sig', asn=153)))




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
emu.addLayer(ospf)
emu.addLayer(sig)

emu.render()

# Compilation
emu.compile(Docker(internetMapEnabled=True), './seed-compiled', override=True)
emu.compile(Graphviz(), './seed-compiled/graphviz', override=True)
