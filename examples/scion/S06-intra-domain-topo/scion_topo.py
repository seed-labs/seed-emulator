#!/usr/bin/env python3

from seedemu.compiler import Docker,Graphviz
from seedemu.generators import DefaultScionGenerator
from seedemu.generators.providers import ScionTopoJsonProvider
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
read topology.json files from real SCION deployment and run virtual experiments
 with your configuration without jeopardising the physical deployment """

provider = ScionTopoJsonProvider("tiny_topo.json")

generator = DefaultScionGenerator(provider)

emu = generator.generate(2,6)

emu.render()

# Compilation
emu.compile(Docker(), './output')
emu.compile(Graphviz(), './output_graph')
