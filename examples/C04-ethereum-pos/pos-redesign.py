#!/usr/bin/env python3
# encoding: utf-8

from seedemu import *

hosts_total_per_as = 3

# Create Emulator Base with 10 Stub AS (150-154, 160-164) using Makers utility method.
# It will create hosts(physical node) named `host_{}`.format(counter), counter starts from 0. 
emu = Makers.makeEmulatorBaseWith10StubASAndHosts(hosts_total_per_as)

# Create the Ethereum layer
eth = EthereumService()

# Create the Blockchain layer which is a sub-layer of Ethereum layer.
# chainName="pos": set the blockchain name as "pos"
# consensus="ConsensusMechnaism.POS" : set the consensus of the blockchain as "ConsensusMechanism.POS".
# supported consensus option: ConsensusMechanism.POA, ConsensusMechanism.POW, ConsensusMechanism.POS
blockchain = eth.createBlockchain(chainName="pos", consensus=ConsensusMechanism.POS)

asns = [150, 151, 152, 153, 154, 160, 161, 162, 163, 164]

###################################################
# Ethereum Node

i = 1
for asn in asns:
    for id in range(hosts_total_per_as):        
        # Create a blockchain virtual node named "eth{}".format(i)
        e:EthereumServer = blockchain.createNode("eth{}".format(i))   
        
        # Create Docker Container Label named 'Ethereum-POS-i'
        e.appendClassName('Ethereum-POS-{}'.format(i))

        # Enable Geth to communicate with geth node via http
        e.enableGethHttp()

        # Set host in asn 150 with id 0 (ip : 10.150.0.71) as BeaconSetupNode.
        if asn == 150 and id == 0:
                e.setBeaconSetupNode()

        # Set host in asn 150 with id 1 (ip : 10.150.0.72) as BootNode. 
        # This node will serve as a BootNode in both execution layer (geth) and consensus layer (lighthouse).
        if asn == 150 and id == 1:
                e.setBootNode(True)

        if asn in [152, 162]:
            if id == 0:
                e.enablePOSValidatorAtRunning()
            if id == 1:
                e.enablePOSValidatorAtRunning(is_manual=True)

        if asn in [151,153,154,160]:
            e.enablePOSValidatorAtGenesis()
            e.startMiner()

        # Customizing the display names (for visualiztion purpose)
        if e.isBeaconSetupNode():
            emu.getVirtualNode('eth{}'.format(i)).setDisplayName('Ethereum-BeaconSetup')
        else:
            emu.getVirtualNode('eth{}'.format(i)).setDisplayName('Ethereum-POS-{}'.format(i))

        # Binding the virtual node to the physical node. 
        emu.addBinding(Binding('eth{}'.format(i), filter=Filter(asn=asn, nodeName='host_{}'.format(id))))

        i = i+1


# Add layer to the emulator
emu.addLayer(eth)

emu.render()

docker = Docker(mapClientEnabled=True)
docker.addImage(DockerImage('rafaelawon/seedemu-lighthouse-base', [], local=False), priority=-1)
docker.addImage(DockerImage('rafaelawon/seedemu-lcli-base', [], local=False), priority=-2)

base = emu.getLayer('Base')

beacon_nodes = base.getNodesByName('host')
for beacon in beacon_nodes:
   docker.setImageOverride(beacon, 'rafaelawon/seedemu-lighthouse-base')

beacon_setup = base.getNodeByAsnAndName(150, 'host_0')
docker.setImageOverride(beacon_setup, 'rafaelawon/seedemu-lcli-base')

emu.compile(docker, './output', override = True)