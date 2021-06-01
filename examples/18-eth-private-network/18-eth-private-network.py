#!/usr/bin/env python
# encoding: utf-8
# __author__ = 'Demon'

from seedsim.core import Simulator, Binding, Filter, Action
from seedsim.compiler import Docker
from seedsim.services import EthereumService
from seedsim.services import WebService


sim = Simulator()
eth = EthereumService()

sim.load('base-component.bin')

#Create eth node
eth.install("eth1")
eth.install("eth2")
eth.install("eth3")
eth.install("eth4")


#Add bindings
sim.addBinding(Binding('eth1', filter = Filter(asn = 150)))
sim.addBinding(Binding('eth2', filter = Filter(asn = 151)))
sim.addBinding(Binding('eth3', filter = Filter(asn = 152)))
sim.addBinding(Binding('eth4', filter = Filter(asn = 153)))


sim.addLayer(eth)
sim.render()

sim.compile(Docker(), './eth-private-network')