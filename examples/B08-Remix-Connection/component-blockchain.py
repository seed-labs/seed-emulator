#!/usr/bin/env python3
# encoding: utf-8

from seedemu import *

emu = Emulator()

# Create the Ethereum layer
# saveState=True: will set the blockchain folder using `volumes`, 
# so the blockchain data will be preserved when containers are deleted.
# Note: right now we need to manually create the folder for each node (see README.md). 
eth = EthereumService(saveState = True)
blockchain = eth.createBlockchain("eth", consensus=ConsensusMechanism.POA)

# Create Ethereum nodes (nodes in this layer are virtual)
e1 = blockchain.createNode("eth1")
e2 = blockchain.createNode("eth2")
e3 = blockchain.createNode("eth3")
e4 = blockchain.createNode("eth4")
e5 = blockchain.createNode("eth5")
e6 = blockchain.createNode("eth6")

# Set bootnodes on e1 and e2. The other nodes can use these bootnodes to find peers.
# Start mining on e1 - e4
e1.setBootNode(True).setBootNodeHttpPort(8081).startMiner()
e2.setBootNode(True).startMiner()
e3.startMiner()
e4.startMiner()

# Create more accounts on e5 and e6
e5.startMiner()
e6.startMiner().createAccounts(total=2, balance=20).unlockAccounts()

# Create a smart contract and deploy it from node e3 
# We need to put the compiled smart contracts inside the Contracts/ folder
smart_contract = SmartContract("./Contracts/contract.bin", "./Contracts/contract.abi")
e3.deploySmartContract(smart_contract)

# Set node port that accepts connections
e3.enableGethHttp()
e6.enableGethHttp().setGethHttpPort(8545)

# Get node port that accepts connections
# Same api used in the EthereumService to set the listening port
e3_port_forward = e3.getGethHttpPort() # Uses default 8545 port
e6_port_forward = e6.getGethHttpPort() # Uses custom port, in this case also using 8545

# Customizing the display names (for visualization purpose)
emu.getVirtualNode('eth1').setDisplayName('Ethereum-1')
emu.getVirtualNode('eth2').setDisplayName('Ethereum-2')
emu.getVirtualNode('eth3').setDisplayName('Ethereum-3').addPortForwarding(8545, e3_port_forward)
emu.getVirtualNode('eth4').setDisplayName('Ethereum-4')
emu.getVirtualNode('eth5').setDisplayName('Ethereum-5')
emu.getVirtualNode('eth6').setDisplayName('Ethereum-6').addPortForwarding(8546, e6_port_forward)

# Add the layer and save the component to a file
emu.addLayer(eth)
emu.dump('component-blockchain.bin')
