#!/usr/bin/env python3
# encoding: utf-8

from seedemu import *

emu = Emulator()

# Create the Ethereum layer
# saveState=True: will set the blockchain folder using `volumes`,
# manual: requires you to trigger the /tmp/run.sh bash files in each container to lunch the ethereum nodes
# so the blockchain data will be preserved when containers are deleted.
# Note: right now we need to manually create the folder for each node (see README.md). 
eth = EthereumService(saveState = True, manual=True)

eth.setBaseConsensusMechanism(ConsensusMechanism.POA)

# Create Ethereum nodes (nodes in this layer are virtual)
start=1
end=15
sealers=[]
bootnodes=[]
hport=8544
#cport=8545 remix
cport=8546 # visualization

# Currently the minimum amount to have to be a validator in proof of stake
balance = 32 * pow(10, 18)

# Setting a third of nodes as bootnodes
for i in range(start, end):
    e = eth.install("eth{}".format(i))
    if i%3 == 0:
        e.setBootNode(True)
        bootnodes.append(i)
    else:
        e.createPrefundedAccounts(balance, 1)
        e.unlockAccounts().startMiner() 
        sealers.append(i)
    
    e.enableExternalConnection() # not recommended for sealers in production mode
    emu.getVirtualNode('eth{}'.format(i)).setDisplayName('Ethereum-{}-poa'.format(i)).addPortForwarding(hport, cport)
    hport = hport + 1

print("There are {} sealers and {} bootnodes".format(len(sealers), len(bootnodes)))
print("Sealers {}".format(sealers))
print("Bootnodes {}".format(bootnodes))

start = end
end = start + 1
for i in range(start, end):
    e = eth.install("eth{}".format(i))
    e.setConsensusMechanism(ConsensusMechanism.POW)
    e.unlockAccounts().startMiner()
    e.enableExternalConnection()
    emu.getVirtualNode("eth{}".format(i)).setDisplayName('Ethereum-{}-pow'.format(i)).addPortForwarding(hport, cport)

print("Created {} nodes that use PoW consensus mechanism".format(end - start))

# Add the layer and save the component to a file
emu.addLayer(eth)
emu.dump('component-blockchain.bin')
