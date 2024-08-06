#!/usr/bin/env python3
# encoding: utf-8

from examples.blockchain.D31_chainlink import chainlink
from seedemu import *
import os

emu = Emulator()

# Run and load the pre-built ethereum component; it is used as the base blockchain
local_dump_path = './blockchain_poa.bin'
chainlink.run(dumpfile=local_dump_path, total_chainlink_nodes=3)
emu.load(local_dump_path)
emu.addBinding(Binding('user_server'))

# Render and compile
OUTPUTDIR = './output'
emu.render()
eth:EthereumService = emu.getLayer('EthereumService')
blockchain:Blockchain = eth.getBlockchainByName(eth.getBlockchainNames()[0])
faucet_server = blockchain.getFaucetServerNames()[0]
utility_server = blockchain.getUtilityServerNames()[0]

chain:ChainlinkService = emu.getLayer('ChainlinkService')
chainlink_servers = chain.getAllServerNames()['ChainlinkServer']
print(chainlink_servers)
data = {}

data['utility'] = str(emu.getBindingFor(utility_server).getInterfaces()[0].getAddress())
data['faucet'] = str(emu.getBindingFor(faucet_server).getInterfaces()[0].getAddress())
data['chainlink'] = [str(emu.getBindingFor(chainlink_server).getInterfaces()[0].getAddress()) for chainlink_server in chainlink_servers]
# Save the data to a file
with open('./../chainlink_info.json', 'w') as f:
    json.dump(data, f)

# Access an environment variable
platform = os.environ.get('platform')

platform_mapping = {
    "amd": Platform.AMD64,
    "arm": Platform.ARM64
}
docker = Docker(internetMapEnabled=True, internetMapPort=8081, etherViewEnabled=True, platform=platform_mapping[platform])

emu.compile(docker, OUTPUTDIR, override = True)
