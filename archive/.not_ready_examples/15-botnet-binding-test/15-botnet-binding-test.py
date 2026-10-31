#!/usr/bin/env python
# encoding: utf-8
# __author__ = 'Demon'

from seedemu.core import Emulator, Binding, Filter, Action
from seedemu.compiler import Docker


simA = Emulator()
simB = Emulator()

simA.load('botnet-component.bin')
simB.load('base-component.bin')

merged = simB.merge(simA,[])

#Binding C2 Server
merged.addBinding(Binding("c2_server", filter = Filter(asn = 150), action=Action.FIRST))


#Binding BOTS
merged.addBinding(Binding("bot\w", filter = Filter()))

merged.render()

###############################################################################

merged.compile(Docker(), './botnet-binding')
