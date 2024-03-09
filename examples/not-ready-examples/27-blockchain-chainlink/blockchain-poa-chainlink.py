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
# Custom chainlink image
CHAINLINK_IMAGE_AMD64 = 'amanvelani/chainlink-develop:amd64'
CHAINLINK_IMAGE_ARM64 = 'amanvelani/chainlink-develop:arm64'

if platform.machine().endswith('64'):
    if 'aarch' in platform.machine().lower() or 'arm' in platform.machine().lower():
        CHAINLINK_IMAGE = CHAINLINK_IMAGE_ARM64
    else:
        CHAINLINK_IMAGE = CHAINLINK_IMAGE_AMD64


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
                           balance=30)
blockchain.addLocalAccount(address='0x2e2e3a61daC1A2056d9304F79C168cD16aAa88e9',
                           balance=9999999)
blockchain.addLocalAccount(address='0xCBF1e330F0abD5c1ac979CF2B2B874cfD4902E24',
                           balance=10)


# Create the Ethereum servers.
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

# Create the Chainlink layer
chainlink = ChainlinkService()
cnode = 'chainlink_node'
# Curl deployment using initializer server
# chainlink.installInitializer(cnode).setContractOwner(<Owner Address>).deploymentType(CURL).setRPCURL(<RPC URL>)
# Web3 deployment  using initializer server
c = chainlink.installInitializer(cnode)
c.setContractOwner('0x2e2e3a61daC1A2056d9304F79C168cD16aAa88e9')
c.setOwnerPrivateKey('20aec3a7207fcda31bdef03001d9caf89179954879e595d9a190d6ac8204e498')
c.setDeploymentType("web3")
c.setRPCURL("10.164.0.71")
service_name = 'Chainlink-0'
emu.getVirtualNode(cnode).setDisplayName(service_name)
emu.addBinding(Binding(cnode, filter = Filter(asn=164, nodeName='host_2')))

# Add the Ethereum layer
emu.addLayer(eth)

# Add the Chainlink layer
emu.addLayer(chainlink)

# Render and compile
OUTPUTDIR = './emulator_20'
emu.render()

docker = Docker(internetMapEnabled=True, internetMapPort=8081, etherViewEnabled=True, platform=Platform.AMD64)

emu.compile(docker, OUTPUTDIR, override = True)
