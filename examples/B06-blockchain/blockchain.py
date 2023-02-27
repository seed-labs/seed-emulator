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

emu = Makers.makeEmulatorBaseWith10StubASAndHosts(1)

# Create the Ethereum layer
# saveState=True: will set the blockchain folder using `volumes`, 
# so the blockchain data will be preserved when containers are deleted.
eth = EthereumService(saveState = True, override=True)

# Create the 2 Blockchain layers, which is a sub-layer of Ethereum layer
# Need to specify chainName and consensus when create Blockchain layer.

# blockchain1 is a POW based blockchain 
blockchain1 = eth.createBlockchain(chainName="POW", consensus=ConsensusMechanism.POW)

# blockchain2 is a POA based blockchain 
blockchain2 = eth.createBlockchain(chainName="POA", consensus=ConsensusMechanism.POA)

# Create blockchain1 nodes (POW Etheruem) (nodes in this layer are virtual)
e1 = blockchain1.createNode("pow-eth1")
e2 = blockchain1.createNode("pow-eth2")
e3 = blockchain1.createNode("pow-eth3")
e4 = blockchain1.createNode("pow-eth4")

# Create blockchain2 nodes (POA Ethereum)
e5 = blockchain2.createNode("poa-eth5")
e6 = blockchain2.createNode("poa-eth6")
e7 = blockchain2.createNode("poa-eth7")
e8 = blockchain2.createNode("poa-eth8")

# Set bootnodes on e1 and e5. The other nodes can use these bootnodes to find peers.
# Start mining on e1,e2 and e5,e6
# To start mine(seal) in POA consensus, the account should be unlocked first. 
e1.setBootNode(True).setBootNodeHttpPort(8090).startMiner()
e2.startMiner()
e5.setBootNode(True).unlockAccounts().startMiner()
e6.unlockAccounts().startMiner()

# Create more accounts with Balance on e3 and e7
# Create one account with createAccount() method
# Create multiple accounts with createAccounts() method
e3.createAccount(balance=20, unit=EthUnit.ETHER, password="admin").unlockAccounts()
e7.createAccounts(total=3, balance=30, unit=EthUnit.ETHER, password="admin")

# Import account with balance 0 on e2
e2.importAccount(keyfilePath='./resources/keyfile_to_import', password="admin", balance=10)

# Enable http connection on e3 
# Set geth http port to 8540 (Default : 8545)
e3.enableGethHttp().setGethHttpPort(8540)

# # Set custom genesis on e4 geth
# e4.setGenesis(CustomGenesisFileContent)

# Set custom geth command option on e4
# Possible to enable geth http using setCustomGethCommandOption() method 
# instead of using enableGethHttp() method
e4.setCustomGethCommandOption("--http --http.addr 0.0.0.0")

# Enable ws connection on e5 geth
# Set geth ws port to 8541 (Default : 8546)
e5.enableGethWs().setGethWsPort(8541)
e5.enableGethHttp()

# Set nodiscover option on e8 geth
e8.setNoDiscover()

# Set custom geth binary file instead of installing an original file.
e3.setCustomGeth("./resources/custom_geth")

# Customizing the display names (for visualization purpose)
emu.getVirtualNode('pow-eth1').setDisplayName('Ethereum-POW-1')
emu.getVirtualNode('pow-eth2').setDisplayName('Ethereum-POW-2')
emu.getVirtualNode('pow-eth3').setDisplayName('Ethereum-POW-3').addPortForwarding(8545, 8540)
emu.getVirtualNode('pow-eth4').setDisplayName('Ethereum-POW-4')

emu.getVirtualNode('poa-eth5').setDisplayName('Ethereum-POA-5')
emu.getVirtualNode('poa-eth6').setDisplayName('Ethereum-POA-6')
emu.getVirtualNode('poa-eth7').setDisplayName('Ethereum-POA-7')
emu.getVirtualNode('poa-eth8').setDisplayName('Ethereum-POA-8')

# Binding virtual nodes to physical nodes
emu.addBinding(Binding('pow-eth1', filter = Filter(asn = 150, nodeName='host_0')))
emu.addBinding(Binding('pow-eth2', filter = Filter(asn = 151, nodeName='host_0')))
emu.addBinding(Binding('pow-eth3', filter = Filter(asn = 152, nodeName='host_0')))
emu.addBinding(Binding('pow-eth4', filter = Filter(asn = 153, nodeName='host_0')))

emu.addBinding(Binding('poa-eth5', filter = Filter(asn = 160, nodeName='host_0')))
emu.addBinding(Binding('poa-eth6', filter = Filter(asn = 161, nodeName='host_0')))
emu.addBinding(Binding('poa-eth7', filter = Filter(asn = 162, nodeName='host_0')))
emu.addBinding(Binding('poa-eth8', filter = Filter(asn = 163, nodeName='host_0')))

# Add the layer and save the component to a file
emu.addLayer(eth)
emu.dump('component-blockchain.bin')

emu.render()

docker = Docker(etherViewEnabled=True)

# If output directory exists and override is set to false, we call exit(1)
# updateOutputdirectory will not be called
emu.compile(docker, './output')
