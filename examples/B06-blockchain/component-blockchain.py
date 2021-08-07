#!/usr/bin/env python3
# encoding: utf-8

from seedemu import *

emu = Emulator()

# Create the Ethereum layer
# saveState=True: will set the blockchain folder using `volumes`, 
# so the blockchain data will be preserved when containers are deleted.
# Note: right now we need to manually create the folder for each node (see README.md). 
eth = EthereumService(saveState = True)

# Create Ethereum nodes (nodes in this layer are virtual)
e1 = eth.install("eth1")
e2 = eth.install("eth2")
e3 = eth.install("eth3")
e4 = eth.install("eth4")
e5 = eth.install("eth5")
e6 = eth.install("eth6")

# Set bootnodes on e1 and e2. The other nodes can use these bootnodes to find peers.
# Start mining on e1 - e4
e1.setBootNode(True).setBootNodeHttpPort(8081).startMiner()
e2.setBootNode(True).startMiner()
e3.startMiner()
e4.startMiner()

# Create more accounts on e5 and e6
e5.createNewAccount().createNewAccount().createNewAccount()
e6.createNewAccount().createNewAccount()

# Create a smart contract and deploy it from node e3 
# We need to put the compiled smart contracts inside the Contracts/ folder
smart_contract = SmartContract("./Contracts/contract.bin", "./Contracts/contract.abi")
e3.deploySmartContract(smart_contract)

# Customizing the display names (for visualization purpose)
emu.getVirtualNode('eth1').setDisplayName('Ethereum-1')
emu.getVirtualNode('eth2').setDisplayName('Ethereum-2')
emu.getVirtualNode('eth3').setDisplayName('Ethereum-3')
emu.getVirtualNode('eth4').setDisplayName('Ethereum-4')
emu.getVirtualNode('eth5').setDisplayName('Ethereum-5')
emu.getVirtualNode('eth6').setDisplayName('Ethereum-6')

# Add the layer and save the component to a file
emu.addLayer(eth)
emu.dump('component-blockchain.bin')
