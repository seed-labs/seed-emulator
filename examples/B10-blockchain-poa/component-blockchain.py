#!/usr/bin/env python3
# encoding: utf-8

from seedemu import *

emu = Emulator()

# Create the Ethereum layer
# saveState=True: will set the blockchain folder using `volumes`, 
# so the blockchain data will be preserved when containers are deleted.
eth = EthereumService()

for i in range (1, 61):
    e = eth.install("eth{}".format(i)).setConsensusMechanism(ConsensusMechanism.POA)
    if i == 1:
        e.setBootNode(True)
    if i == 2: 
        e.enableGethHttp()
        emu.getVirtualNode('eth{}'.format(i)).addPortForwarding(8545, 8545)
    if i % 3 == 0:
        e.unlockAccounts().startMiner()
    # Customizing the display names (for visualization purpose)
    emu.getVirtualNode('eth{}'.format(i)).setDisplayName('Ethereum-POA-{}'.format(i))

# Add the layer and save the component to a file
emu.addLayer(eth)
emu.dump('component-blockchain.bin')
