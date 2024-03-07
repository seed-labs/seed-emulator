#!/usr/bin/env python3

from seedemu.compiler import Docker,Graphviz
from seedemu.core import Emulator, Binding, Filter
from seedemu.generators.intra import IntraASTopoReader,ASTopology, TopoFormat
from seedemu.layers import ScionBase, ScionRouting, ScionIsd, Scion,Ospf,Ibgp
from seedemu.layers.Scion import LinkType as ScLinkType

# Initialize
ospf = Ospf()
emu = Emulator()
base = ScionBase()
routing = ScionRouting()
scion_isd = ScionIsd()
scion = Scion()


# load the IntraDomainTopology for all ASes from file
topo = ASTopology()

topo.from_file("orbis_hot_super_simple.txt",TopoFormat.ORBIS)
reader = IntraASTopoReader()

# SCION ISDs
base.createIsolationDomain(1)

# Internet Exchange
base.createInternetExchange(100) # 150-152
base.createInternetExchange(101) # 150-151
base.createInternetExchange(102) # 151-152

# AS-150
as150 = base.createAutonomousSystem(150)
scion_isd.addIsdAs(1, 150, is_core=True)
reader.generateAS(topo,as150)
as150.createControlService('cs1').joinNetwork('net_000')

as150.getRouter('001').joinNetwork('ix100')
as150.getRouter('103').joinNetwork('ix101')


# AS-151
as151 = base.createAutonomousSystem(151)
scion_isd.addIsdAs(1, 151, is_core=True)
reader.generateAS(topo,as151)
as151.createControlService('cs1').joinNetwork('net_000')

as151.getRouter('001').joinNetwork('ix101')
as151.getRouter('103').joinNetwork('ix102')


# AS-152
as152 = base.createAutonomousSystem(152)
scion_isd.addIsdAs(1, 152, is_core=True)
reader.generateAS(topo,as152)
as152.createControlService('cs1').joinNetwork('net_000')

as152.getRouter('001').joinNetwork('ix100')
as152.getRouter('103').joinNetwork('ix102')

# Inter-AS routing
scion.addIxLink(101, (1, 150), (1, 151), ScLinkType.Core)
scion.addIxLink(102, (1, 151), (1, 152), ScLinkType.Core)
scion.addIxLink(100, (1, 152), (1, 150), ScLinkType.Core)

# Rendering
emu.addLayer(base)
emu.addLayer(routing)
emu.addLayer(scion_isd)
emu.addLayer(scion)
emu.addLayer(ospf)


emu.render()

# Compilation
emu.compile(Docker(), './output')

