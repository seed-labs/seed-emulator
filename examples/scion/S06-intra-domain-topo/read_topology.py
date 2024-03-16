#!/usr/bin/env python3

from seedemu.compiler import Docker,Graphviz
from seedemu.core import Emulator, Binding, Filter
from seedemu.generators.intra import IntraASTopoReader,ASTopology, TopoFormat
from seedemu.layers import ScionBase, ScionRouting, ScionIsd, Scion,Ospf,Ibgp
from seedemu.layers.Scion import LinkType as ScLinkType

""" ___   _____    __                    __                                         __         
   /   | / ___/   / /_____  ____  ____  / /___  ____ ___  __   ________  ____ _____/ /__  _____
  / /| | \__ \   / __/ __ \/ __ \/ __ \/ / __ \/ __ `/ / / /  / ___/ _ \/ __ `/ __  / _ \/ ___/
 / ___ |___/ /  / /_/ /_/ / /_/ / /_/ / / /_/ / /_/ / /_/ /  / /  /  __/ /_/ / /_/ /  __/ /    
/_/  |_/____/   \__/\____/ .___/\____/_/\____/\__, /\__, /  /_/   \___/\__,_/\__,_/\___/_/     
                        /_/                  /____//____/                       2024                           
"""
# Initialize
ospf = Ospf()
emu = Emulator()
base = ScionBase()
routing = ScionRouting()
scion_isd = ScionIsd()
scion = Scion()

# SCION ISDs
base.createIsolationDomain(1)

# AS-150
as150 = base.createAutonomousSystem(150)
scion_isd.addIsdAs(1, 150, is_core=True)

# load the IntraDomainTopology for AS-150 from file
topo = ASTopology()
#topo.from_file("1221_r0.cch",TopoFormat.ROCKETFUEL)
topo.from_file("orbis_hot_simplified_3.txt",TopoFormat.ORBIS)
reader = IntraASTopoReader()
reader.generateAS(topo,as150)

as150.createControlService('cs1').joinNetwork('net_000')

# Rendering
emu.addLayer(base)
emu.addLayer(routing)
emu.addLayer(scion_isd)
emu.addLayer(scion)
emu.addLayer(ospf)


emu.render()

# Compilation
emu.compile(Docker(), './output')

