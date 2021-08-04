#!/usr/bin/env python3
# encoding: utf-8
# __author__ = 'Demon'

from seedemu.core import Emulator, Binding, Filter
from seedemu.compiler import Docker

# Use the local copy for now (we made changes)
from EthereumService import EthereumService
#from seedemu.services import EthereumService

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


# Set boot nodes and http server port
e1.setBootNode(True).setBootNodeHttpPort(8081)
e2.setBootNode(True)

# add bindings
emu.addBinding(Binding('eth1', filter = Filter(asn = 150)))
emu.addBinding(Binding('eth2', filter = Filter(asn = 151)))
emu.addBinding(Binding('eth3', filter = Filter(asn = 152)))
emu.addBinding(Binding('eth4', filter = Filter(asn = 153)))

emu.addLayer(eth)
emu.render()

#Generate and deploy Smart Contract on node eth1
esm.startMinerInNode(e1, eth)
esm.startMinerInNode(e2, eth)
esm.startMinerInNode(e3, eth)
esm.startMinerInNode(e4, eth)
esm.deploySmartContractOn(e1, eth, "./SmartContract/contract.bin", "./SmartContract/contract.abi")
esm.createNewAccountInNode(e2, eth)

# Customization 
emu.getBindingFor('eth1').setDisplayName('Ethereum-1')
emu.getBindingFor('eth2').setDisplayName('Ethereum-2')
emu.getBindingFor('eth3').setDisplayName('Ethereum-3')
emu.getBindingFor('eth4').setDisplayName('Ethereum-4')

emu.compile(Docker(), './output')
