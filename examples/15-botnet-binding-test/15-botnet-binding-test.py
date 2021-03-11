#!/usr/bin/env python
# encoding: utf-8
# __author__ = 'Demon'

from seedsim.core import Simulator, Binding, Filter, Action
from seedsim.compiler import Docker


simA = Simulator()
simB = Simulator()

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
