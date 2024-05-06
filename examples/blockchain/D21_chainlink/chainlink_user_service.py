#!/usr/bin/env python3
# encoding: utf-8

from seedemu import *
import chainlink_service
import os
import platform

local_dump_path = './blockchain-chainlink.bin'

if not os.path.exists(local_dump_path):
    chainlink_service.run(dumpfile=local_dump_path)

# Load the pre-built component
emuA = Emulator()
emuA.load('./blockchain-chainlink.bin')

# Chainlink User Service
emuB = Emulator()
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

# Add the Chainlink User Service Layer
emuB.addLayer(chainlink_user)

# Merge the two components
emu = emuA.merge(emuB, DEFAULT_MERGERS)

# Bind the chainlink user service to a random physical node
emu.getVirtualNode(cnode).setDisplayName('Chainlink-User')
emu.addBinding(Binding(cnode))

OUTPUTDIR = './output'
emu.render()

if platform.machine() == 'aarch64' or platform.machine() == 'arm64':
    current_platform = Platform.ARM64
else:
    current_platform = Platform.AMD64

docker = Docker(internetMapEnabled=True, internetMapPort=8081, etherViewEnabled=True, platform=current_platform)
emu.compile(docker, OUTPUTDIR, override = True)
