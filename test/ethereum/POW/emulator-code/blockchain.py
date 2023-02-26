#!/usr/bin/env python3
# encoding: utf-8

from seedemu import *

emu = Makers.makeEmulatorBaseWith10StubASAndHosts(1)

# Create the Ethereum layer
eth = EthereumService()

# Create the 2 Blockchain layers, which is a sub-layer of Ethereum layer
# Need to specify chainName and consensus when create Blockchain layer.

# blockchain1 is a POW based blockchain 
blockchain1 = eth.createBlockchain(chainName="POW", consensus=ConsensusMechanism.POW)

# Create blockchain1 nodes (POW Etheruem) (nodes in this layer are virtual)
e1 = blockchain1.createNode("pow-eth1")
e2 = blockchain1.createNode("pow-eth2")
e3 = blockchain1.createNode("pow-eth3")
e4 = blockchain1.createNode("pow-eth4")
e5 = blockchain1.createNode("pow-eth5")

# Set bootnodes on e1 and e5. The other nodes can use these bootnodes to find peers.
# Start mining on e1,e2 and e5,e6
# To start mine(seal) in POA consensus, the account should be unlocked first. 
e1.setBootNode(True).setBootNodeHttpPort(8090).startMiner()
e2.importAccount(keyfilePath='./resources/keyfile_to_import', password="admin", balance=10, unit=EthUnit.ETHER)
e2.startMiner()
# Set custom geth binary file instead of installing an original file.
e3.setCustomGeth("./resources/custom_geth")
e3.createAccount(balance=20, unit=EthUnit.ETHER, password="admin").unlockAccounts()

e3.enableGethHttp().setGethHttpPort(8540)

e4.setCustomGethCommandOption("--http --http.addr 0.0.0.0")

e5.startMiner()


# Customizing the display names (for visualization purpose)
emu.getVirtualNode('pow-eth1').setDisplayName('Ethereum-POW-1')
emu.getVirtualNode('pow-eth2').setDisplayName('Ethereum-POW-2')
emu.getVirtualNode('pow-eth3').setDisplayName('Ethereum-POW-3').addPortForwarding(8545, 8540)
emu.getVirtualNode('pow-eth4').setDisplayName('Ethereum-POW-4')
emu.getVirtualNode('pow-eth5').setDisplayName('Ethereum-POW-5')

# Binding virtual nodes to physical nodes
emu.addBinding(Binding('pow-eth1', filter = Filter(asn = 150, nodeName='host_0')))
emu.addBinding(Binding('pow-eth2', filter = Filter(asn = 151, nodeName='host_0')))
emu.addBinding(Binding('pow-eth3', filter = Filter(asn = 152, nodeName='host_0')))
emu.addBinding(Binding('pow-eth4', filter = Filter(asn = 153, nodeName='host_0')))
emu.addBinding(Binding('pow-eth5', filter = Filter(asn = 154, nodeName='host_0')))

# Add the layer
emu.addLayer(eth)

emu.render()

docker = Docker()

# If output directory exists and override is set to false, we call exit(1)
# updateOutputdirectory will not be called
emu.compile(docker, './output')