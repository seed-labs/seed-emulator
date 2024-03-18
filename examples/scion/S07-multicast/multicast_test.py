#!/usr/bin/env python3

from seedemu.compiler import Docker,Graphviz
from seedemu.core import Emulator, Binding, Filter
from seedemu.generators.intra import IntraASTopoReader,ASTopology, TopoFormat
from seedemu.layers import ScionBase, ScionRouting, ScionIsd, Scion, Pim
from seedemu.layers.Scion import LinkType as ScLinkType

# Initialize
emu = Emulator()
base = ScionBase()
routing = ScionRouting()
scion_isd = ScionIsd()
pim_ospf = Pim()
scion = Scion()

# SCION ISDs
base.createIsolationDomain(1)

# AS-150
as150 = base.createAutonomousSystem(150)
scion_isd.addIsdAs(1, 150, is_core=True)

# load the IntraDomainTopology for AS-150 from file
topo = ASTopology()
topo.from_file("tiny_topo.txt",TopoFormat.ORBIS)
reader = IntraASTopoReader()
reader.generateAS(topo,as150)

as150.createControlService('cs1').joinNetwork('net_000')

pim_ospf.enableOn(150)

# Rendering
emu.addLayer(base)
emu.addLayer(routing)
emu.addLayer(scion_isd)
emu.addLayer(scion)
emu.addLayer(pim_ospf)


emu.render()

# Compilation
emu.compile(Docker(), './output')

