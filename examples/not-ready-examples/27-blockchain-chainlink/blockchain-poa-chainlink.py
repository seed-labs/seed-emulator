#!/usr/bin/env python3
# encoding: utf-8

from seedemu import *
import os, sys
import platform
from typing import List

###############################################################################
emu = Emulator()
base = Base()

# Load the pre-built components and merge them
emu.load('./hybrid-internet.bin')
base = emu.getLayer('Base')


###############################################################################
# Create the Ethereum layer

eth = EthereumService()
blockchain = eth.createBlockchain(chainName="POA", consensus=ConsensusMechanism.POA)

# Create 10 accounts, each with 100 Ethers. We will use these accounts to
# generate background traffic (sending random transactions from them).
words = "great amazing fun seed lab protect network system security prevent attack future"
blockchain.setLocalAccountParameters(mnemonic=words, total=10, balance=100)

# These 3 accounts are generated from the following phrase:
# "gentle always fun glass foster produce north tail security list example gain"
# They are for users. We will use them in MetaMask, as well as in our sample code.
blockchain.addLocalAccount(address='0xF5406927254d2dA7F7c28A61191e3Ff1f2400fe9',
                           balance=5000)
blockchain.addLocalAccount(address='0x2e2e3a61daC1A2056d9304F79C168cD16aAa88e9',
                           balance=9999999)
blockchain.addLocalAccount(address='0xCBF1e330F0abD5c1ac979CF2B2B874cfD4902E24',
                           balance=10)
blockchain.addLocalAccount(address='0xA08Ae0519125194cB516d72402a00A76d0126Af8', balance=20)


asns  = [150, 151, 152, 153, 154, 160, 161, 162, 163, 164]
hosts_total = 2    # The number of servers per AS
signers  = []
i = 0
for asn in asns:
    for id in range(hosts_total):
        vnode = 'eth{}'.format(i)
        e = blockchain.createNode(vnode)
        displayName = 'Ethereum-POA-%.2d'
        e.enableGethHttp()  # Enable HTTP on all nodes
        e.enableGethWs()    # Enable WS on all nodes for chainlink service to listen
        e.unlockAccounts()
        if i%2  == 0:
            e.startMiner()
            signers.append(vnode)
            displayName = displayName + '-Signer'
            emu.getVirtualNode(vnode).appendClassName("Signer")
        if i%3 == 0:
            e.setBootNode(True)
            displayName = displayName + '-BootNode'
            emu.getVirtualNode(vnode).appendClassName("BootNode")

        emu.getVirtualNode(vnode).setDisplayName(displayName%(i))
        emu.addBinding(Binding(vnode, filter=Filter(asn=asn, nodeName='host_{}'.format(id))))
        i = i+1


# Create the Faucet server
faucet:FaucetServer = blockchain.createFaucetServer(vnode='faucet', 
                                                     port=80, 
                                                     linked_eth_node='eth5',
                                                     balance=10000,
                                                     max_fund_amount=10)
# For testing purposes, we will fund some accounts
faucet.fund('0x72943017a1fa5f255fc0f06625aec22319fcd5b3', 2)
faucet.fund('0x5449ba5c5f185e9694146d60cfe72681e2158499', 5)

emu.addBinding(Binding('faucet', filter=Filter(asn=154, nodeName='host_2')))

# Create the Chainlink Init server
chainlink = ChainlinkService()
c_asns  = [150, 151]
cnode = 'chainlink_init_server'
c_init = chainlink.installInitializer(cnode)
c_init.setFaucetServerInfo(vnode = 'faucet', port = 80)
c_init.setRPCbyEthNodeName('eth2')
service_name = 'Chainlink-Init'
emu.getVirtualNode(cnode).setDisplayName(service_name)
emu.addBinding(Binding(cnode, filter = Filter(asn=164, nodeName='host_2')))

i = 0
# Create Chainlink normal servers
for asn in c_asns:
    cnode = 'chainlink_server_{}'.format(i)
    c_normal = chainlink.install(cnode)
    c_normal.setRPCbyEthNodeName('eth{}'.format(i))
    c_normal.setInitNodeIP("chainlink_init_server")
    c_normal.setFaucetServerInfo(vnode = 'faucet', port = 80)
    service_name = 'Chainlink-{}'.format(i)
    emu.getVirtualNode(cnode).setDisplayName(service_name)
    emu.addBinding(Binding(cnode, filter = Filter(asn=asn, nodeName='host_2')))
    i = i + 1
    
# Chainlink User Service
# This will work with the default jobs configured on the chainlink servers
'''
Flow of ChainlinkExampleService:
1. Create an instance of ChainlinkUserService
2. Install the service
3. Set the RPC server to connect to the Ethereum node
4. Set the Faucet server to connect to the Faucet server
'''
'''
Behind the scenes:
1. Wait for the chainlink init server to be up. Get LINK token contract address and oracle contract addresses
2. Fund the user account
3. Deploy the user contract
4. Set the LINK token contract address and oracle contract addresses in the user contract
5. Send 1ETH to the LINK token contract to fund the user account with LINK tokens
6. Transfer LINK token to the user contract
7. Call the main function in the user contract
'''
chainlink_user = ChainlinkUserService()
cnode = 'chainlink_user'
c_user = chainlink_user.install(cnode)
c_user.setRPCbyEthNodeName('eth2')
c_user.setFaucetServerInfo(vnode = 'faucet', port = 80)
c_user.setChainlinkServiceInfo(init_node_name='chainlink_init_server', number_of_normal_servers=2)
emu.getVirtualNode(cnode).setDisplayName('Chainlink-User')
emu.addBinding(Binding(cnode, filter = Filter(asn=153, nodeName='host_2')))

# Add the Ethereum layer
emu.addLayer(eth)

# Add the Chainlink layer
emu.addLayer(chainlink)

# Add the Chainlink User layer
emu.addLayer(chainlink_user)

# Render and compile
OUTPUTDIR = './emulator_20'
emu.render()

docker = Docker(internetMapEnabled=True, internetMapPort=8081, etherViewEnabled=True, platform=Platform.AMD64)

emu.compile(docker, OUTPUTDIR, override = True)
