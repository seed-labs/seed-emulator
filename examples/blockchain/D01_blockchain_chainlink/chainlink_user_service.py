#!/usr/bin/env python3
# encoding: utf-8

from seedemu import *
from examples.blockchain.D01_blockchain_chainlink import chainlink_service
import os

local_dump_path = './blockchain-chainlink.bin'

if not os.path.exists(local_dump_path):
    chainlink_service.run(dumpfile=local_dump_path)

# Load the pre-built components and merge them
emu = Emulator()
emu.load('./blockchain-chainlink.bin')

# Chainlink User Service
# This will work with the default jobs configured on the chainlink servers
'''
Flow of ChainlinkUserService:
1. Create an instance of ChainlinkUserService
2. Install the service
3. Set the RPC server to connect to the Ethereum node
4. Set the Faucet server to connect to the Faucet server
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
emu.addBinding(Binding(cnode, filter = Filter(asn=160, nodeName='host_2')))


# Add the Chainlink User Service Layer
emu.addLayer(chainlink_user)

OUTPUTDIR = './output'
emu.render()

docker = Docker(internetMapEnabled=True, internetMapPort=8081, etherViewEnabled=True, platform=Platform.AMD64)

emu.compile(docker, OUTPUTDIR, override = True)
