#!/usr/bin/env python3
# encoding: utf-8

from seedemu import *

CustomGenesisFileContent = '''\
{
        "nonce":"0x0",
        "timestamp":"0x621549f1",
        "parentHash":"0x0000000000000000000000000000000000000000000000000000000000000000",
        "extraData":"0x",
        "gasLimit":"0x80000000",
        "difficulty":"0x0",
        "mixhash":"0x0000000000000000000000000000000000000000000000000000000000000000",
        "coinbase":"0x0000000000000000000000000000000000000000",
        "number": "0x0",
        "gasUsed": "0x0",
        "baseFeePerGas": null,
        "config": {
            "chainId": 11,
            "homesteadBlock": 0,
            "eip150Block": 0,
            "eip150Hash": "0x0000000000000000000000000000000000000000000000000000000000000000",
            "eip155Block": 0,
            "eip158Block": 0,
            "byzantiumBlock": 0,
            "constantinopleBlock": 0,
            "petersburgBlock": 0,
            "istanbulBlock": 0,
            "ethash": {
            }
        },
        "alloc": {
        }
}
'''

emu = Makers.makeEmulatorBaseWith5StubASAndHosts(1)

# Create the Ethereum layer
# saveState=True: will set the blockchain folder using `volumes`, 
# so the blockchain data will be preserved when containers are deleted.
eth = EthereumService()

# Create the 2 Blockchain layers, which is a sub-layer of Ethereum layer
# Need to specify chainName and consensus when create Blockchain layer.

# blockchain is a POA based blockchain 
blockchain = eth.createBlockchain(chainName="POA", consensus=ConsensusMechanism.POA)

# Create blockchain nodes (POA Ethereum)
e1 = blockchain.createNode("poa-eth1")
e2 = blockchain.createNode("poa-eth2")
e3 = blockchain.createNode("poa-eth3")
e4 = blockchain.createNode("poa-eth4")
e5 = blockchain.createNode("poa-eth5")

e1.setBootNode(True).unlockAccounts().startMiner()
e1.enableGethWs().setGethWsPort(8541)
e1.enableGethHttp()

e2.importAccount(keyfilePath='./resources/keyfile_to_import', password="admin", balance=10)
e2.unlockAccounts().startMiner()
e3.createAccounts(total=3, balance=30, unit=EthUnit.ETHER, password="admin")

e5.setNoDiscover()

emu.getVirtualNode('poa-eth1').setDisplayName('Ethereum-POA-1')
emu.getVirtualNode('poa-eth2').setDisplayName('Ethereum-POA-2')
emu.getVirtualNode('poa-eth3').setDisplayName('Ethereum-POA-3')
emu.getVirtualNode('poa-eth4').setDisplayName('Ethereum-POA-4')
emu.getVirtualNode('poa-eth5').setDisplayName('Ethereum-POA-5')


# Binding virtual nodes to physical nodes
emu.addBinding(Binding('poa-eth1', filter = Filter(asn = 150, nodeName='host_0')))
emu.addBinding(Binding('poa-eth2', filter = Filter(asn = 151, nodeName='host_0')))
emu.addBinding(Binding('poa-eth3', filter = Filter(asn = 152, nodeName='host_0')))
emu.addBinding(Binding('poa-eth4', filter = Filter(asn = 153, nodeName='host_0')))
emu.addBinding(Binding('poa-eth5', filter = Filter(asn = 154, nodeName='host_0')))

# Add the layer and save the component to a file
emu.addLayer(eth)
emu.dump('component-blockchain.bin')

emu.render()

docker = Docker(etherViewEnabled=True)

# Add the 'rafaelawon/seedemu-lighthouse-base' custom image from dockerhub.
# This image contains custom lighthouse software.
docker.addImage(DockerImage('rafaelawon/seed-geth-base:v1.10.26', [], local=False), priority=-1)

base = emu.getLayer('Base')

# Get the physical nodes of all hosts from Base layer.
# The name of physical nodes generated from Makers.makeEmulatorBaseWith10StubASAndHosts() is 'host_{}'
# Base::getNodesByName('host') returns the physical nodes whose name starts with 'host'.
hosts = base.getNodesByName('host')

# Set all host nodes to use the custom 'seedemu-lighthouse-base' image.
for host in hosts:
   docker.setImageOverride(host, 'rafaelawon/seed-geth-base:v1.10.26')

# If output directory exists and override is set to false, we call exit(1)
# updateOutputdirectory will not be called
emu.compile(docker, './output')
