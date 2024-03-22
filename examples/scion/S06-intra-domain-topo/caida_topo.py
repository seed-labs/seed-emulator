#!/usr/bin/env python3

from seedemu.compiler import Docker,Graphviz
from seedemu.generators import DefaultScionGenerator, CommonRouterForAllIF
from seedemu.generators.providers import CaidaDataProvider
from seedemu.core import Emulator, Binding, Filter
from seedemu.core.enums import NetworkType
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

provider = CaidaDataProvider("5_geo_rel.xml")

generator = DefaultScionGenerator(provider,CommonRouterForAllIF)

emu = generator.generate(2,5)


base = emu.getLayer('Base')
reg = emu.getRegistry()
for asn in provider.getASes():
    
    _as = base.getAutonomousSystem(asn)   
    host = _as.createHost('host00')
    for netname in _as.getNetworks():
        net = _as.getNetwork(netname)
        if net.getType() == NetworkType.Local:
           host.joinNetwork(net.getName()) 
           break
            


emu.render()

# Compilation
emu.compile(Docker(), './output')
emu.compile(Graphviz(), './output_graph')

