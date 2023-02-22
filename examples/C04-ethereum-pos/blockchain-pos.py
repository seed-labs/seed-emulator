#!/usr/bin/env python3
# encoding: utf-8

from seedemu import *

# Create Emulator Base with 10 Stub AS (150-154, 160-164) using Makers utility method.
# hosts_per_stub_as=3 : create 3 hosts per one stub AS.
# It will create hosts(physical node) named `host_{}`.format(counter), counter starts from 0. 
hosts_per_stub_as = 3
emu = Makers.makeEmulatorBaseWith10StubASAndHosts(hosts_per_stub_as = hosts_per_stub_as)

# Create the Ethereum layer
eth = EthereumService()

# Create the Blockchain layer which is a sub-layer of Ethereum layer.
# chainName="pos": set the blockchain name as "pos"
# consensus="ConsensusMechnaism.POS" : set the consensus of the blockchain as "ConsensusMechanism.POS".
# supported consensus option: ConsensusMechanism.POA, ConsensusMechanism.POW, ConsensusMechanism.POS
blockchain = eth.createBlockchain(chainName="pos", consensus=ConsensusMechanism.POS)

# set `terminal_total_difficulty`, which is the value to designate when the Merge is happen.
blockchain.setTerminalTotalDifficulty(30)

asns = [150, 151, 152, 153, 154, 160, 161, 162, 163, 164]

###################################################
# Ethereum Node

i = 1
for asn in asns:
    for id in range(hosts_per_stub_as):        
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

        # Set hosts in asn 152 and 162 with id 0 and 1 as validator node. 
        # Validator is added by deposit 32 Ethereum and is activated in realtime after the Merge.
        # isManual=True : deposit 32 Ethereum by manual. 
        #                 Other than deposit part, create validator key and running a validator node is done by codes.  
        if asn in [151]:
            if id == 0:
                e.enablePOSValidatorAtRunning()
            if id == 1:
                e.enablePOSValidatorAtRunning(is_manual=True)
        
        # Set hosts in asn 152, 153, 154, and 160 as validator node.
        # These validators are activated by default from genesis status.
        # Before the Merge, when the consensus in this blockchain is still POA, 
        # these hosts will be the signer nodes.
        if asn in [152,153,154,160,161,162,163,164]:
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

# Enable internetMap
# Enable etherView
docker = Docker(internetMapEnabled=True, etherViewEnabled=True)

# Add the 'rafaelawon/seedemu-lighthouse-base' custom image from dockerhub.
# This image contains custom lighthouse software.
docker.addImage(DockerImage('rafaelawon/seedemu-lighthouse-base', [], local=False), priority=-1)

# Add the 'rafaelawon/seedemu-lighthouse-base' custom image from dockerhub.
# This image contains custom lcli software.
docker.addImage(DockerImage('rafaelawon/seedemu-lcli-base', [], local=False), priority=-2)

base = emu.getLayer('Base')

# Get the physical nodes of all hosts from Base layer.
# The name of physical nodes generated from Makers.makeEmulatorBaseWith10StubASAndHosts() is 'host_{}'
# Base::getNodesByName('host') returns the physical nodes whose name starts with 'host'.
hosts = base.getNodesByName('host')

# Set all host nodes to use the custom 'seedemu-lighthouse-base' image.
for host in hosts:
   docker.setImageOverride(host, 'rafaelawon/seedemu-lighthouse-base')

# Get the physical node of beacon setup node. 
# The host in asn 150 with id 0 (ip : 10.150.0.71) is set as BeaconSetupNode.
# Base::getNodeByAsnAndName(150, 'host_0') returns the physical node whose name is 'host_0' in AS 150.
beacon_setup = base.getNodeByAsnAndName(150, 'host_0')

# Set the node to use the custom 'seedemu-lcli-base' image.
docker.setImageOverride(beacon_setup, 'rafaelawon/seedemu-lcli-base')

emu.compile(docker, './output', override = True)
