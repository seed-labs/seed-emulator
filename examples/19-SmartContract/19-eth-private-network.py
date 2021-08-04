#!/usr/bin/env python
# encoding: utf-8
# __author__ = 'Demon'

from seedemu.core import Emulator, Binding, Filter
from seedemu.compiler import Docker
from seedemu.services import EthereumService
from EthereumConsoleManager import EthereumConsoleManager

emu = Emulator()
eth = EthereumService()
esm = EthereumConsoleManager()

emu.load('base-component.bin')

# create eth node
e1 = eth.install("eth1")
e2 = eth.install("eth2")
e3 = eth.install("eth3")
e4 = eth.install("eth4")

# optionally, set boot nodes.
e1.setBootNode(True)
e2.setBootNode(True)

# optionally, set boot node http server port
e1.setBootNodeHttpPort(8081)

# add bindings
emu.addBinding(Binding('eth1', filter = Filter(asn = 150)))
emu.addBinding(Binding('eth2', filter = Filter(asn = 151)))
emu.addBinding(Binding('eth3', filter = Filter(asn = 152)))
emu.addBinding(Binding('eth4', filter = Filter(asn = 153)))

emu.addLayer(eth)
emu.render()

#Generate and deploy Smart Contract on node eth1
esm.startMinerInNode(e1,eth)
esm.deploySmartContractOn(e1, eth, "./examples/19-SmartContract/SmartContract/contract.bin", "./examples/19-SmartContract/SmartContract/contract.abi")
esm.createNewAccountInNode(e2, eth)

emu.getBindingFor('eth1').setDisplayName('ethereumNode-1')
emu.getBindingFor('eth2').setDisplayName('ethereumNode-2')
emu.getBindingFor('eth3').setDisplayName('ethereumNode-3')
emu.getBindingFor('eth4').setDisplayName('ethereumNode-4')

emu.compile(Docker(), './output')