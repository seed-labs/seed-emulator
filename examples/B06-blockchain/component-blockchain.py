#!/usr/bin/env python3
# encoding: utf-8

from seedemu import *

emu = Emulator()

# Create the Ethereum layer
# saveState=True: will set the blockchain folder using `volumes`, 
# so the blockchain data will be preserved when containers are deleted.
eth = EthereumService(saveState = True)


# Create POW Ethereum nodes (nodes in this layer are virtual)
e1 = eth.install("eth1")
e2 = eth.install("eth2")
e3:EthereumServer = eth.install("eth3")

# Create POA Ethereum nodes
e4 = eth.install("eth4").setConsensusMechanism(ConsensusMechanism.POA)
e5 = eth.install("eth5").setConsensusMechanism(ConsensusMechanism.POA)
e6 = eth.install("eth6").setConsensusMechanism(ConsensusMechanism.POA)

# Set bootnodes on e1 and e4. The other nodes can use these bootnodes to find peers.
# Start mining on e1,e2 and e4,e5
# To start mine(seal) in POA consensus, the account should be unlocked first. 
e1.setBootNode(True).startMiner()
e2.startMiner()

e4.setBootNode(True).unlockAccounts().startMiner()
e5.unlockAccounts().startMiner()

# Create more accounts with Balance on e3 and e6
# Create one account with createAccount() method
# Create multiple accounts with createAccounts() method
e3.createAccount(balance= 32 * pow(10,18), password="admin")
e6.createAccounts(3, balance = 32*pow(10,18), password="admin")

# Enable external connection on e3
e3.enableGethHttp()

# Set custom geth binary file instead of installing an original file.
e3.setCustomGeth("./geth_1.10.13_attacker")

# Customizing the display names (for visualization purpose)
emu.getVirtualNode('eth1').setDisplayName('Ethereum-POW-1')
emu.getVirtualNode('eth2').setDisplayName('Ethereum-POW-2')
emu.getVirtualNode('eth3').setDisplayName('Ethereum-POW-3').addPortForwarding(8545, 8545)
emu.getVirtualNode('eth4').setDisplayName('Ethereum-POA-4')
emu.getVirtualNode('eth5').setDisplayName('Ethereum-POA-5')
emu.getVirtualNode('eth6').setDisplayName('Ethereum-POA-6')

# Add the layer and save the component to a file
emu.addLayer(eth)
emu.dump('component-blockchain.bin')
