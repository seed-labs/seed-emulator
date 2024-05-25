#!/usr/bin/env python3
# encoding: utf-8

from seedemu import *
import chainlink
import platform
import random

emu = Emulator()

# Run and load the pre-built component
local_dump_path = './blockchain-with-chainlink.bin'
chainlink.run(dumpfile=local_dump_path)
emu.load(local_dump_path)

eth:EthereumService    = emu.getLayer('EthereumService')
blockchain: Blockchain = eth.getBlockchainByName(eth.getBlockchainNames()[0])
faucet_info = blockchain.getFaucetServerInfo()
eth_nodes   = blockchain.getEthServerNames()

chainlink: ChainlinkService = emu.getLayer('ChainlinkService')
init_server = chainlink.getChainlinkInitServerName()

# Chainlink User Service
# This will work with the default jobs configured on the Chainlink servers
chainlink_user = ChainlinkUserService()
cnode = 'chainlink_user'
chainlink_user.install(cnode) \
      .setLinkedEthNode(name=random.choice(eth_nodes)) \
      .setFaucetServerInfo(faucet_info[0]['name'], faucet_info[0]['port']) \
      .setChainlinkServiceInfo(init_server, len(chainlink.getChainlinkServerNames()))\
      .setDisplayName('Chainlink-User')


# Add the Chainlink User Service Layer
emu.addLayer(chainlink_user)

# Bind the chainlink user service to a random physical node
emu.addBinding(Binding(cnode))

emu.render()

if platform.machine() == 'aarch64' or platform.machine() == 'arm64':
    current_platform = Platform.ARM64
else:
    current_platform = Platform.AMD64

docker = Docker(etherViewEnabled=True, platform=current_platform)
emu.compile(docker, './output', override = True)


'''
Flow of ChainlinkUserService:

Behind the scenes:
1. Wait for the chainlink init server to be up. Get LINK token contract address and oracle contract addresses
2. Fund the user account
3. Deploy the user contract
4. Set the LINK token contract address and oracle contract addresses in the user contract
5. Send 1ETH to the LINK token contract to fund the user account with LINK tokens
6. Transfer LINK token to the user contract
7. Call the main function in the user contract
'''
