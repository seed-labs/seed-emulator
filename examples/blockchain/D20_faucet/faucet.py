#!/usr/bin/env python3
# encoding: utf-8

import sys
from seedemu import *
from examples.blockchain.D00_ethereum_poa import ethereum_poa


emu = Emulator()

# Run and load the pre-built ethereum component; it is used as the base blockchain
local_dump_path = './blockchain-poa.bin'
ethereum_poa.run(dumpfile=local_dump_path, total_accounts_per_node=1)
emu.load(local_dump_path)

# Get the faucet server instance
eth = emu.getLayer('EthereumService')
blockchain  = eth.getBlockchainByName(eth.getBlockchainNames()[0])
faucet_info = blockchain.getFaucetServerInfo()
faucet_name = blockchain.getFaucetServerNames()[0]
faucet      = blockchain.getFaucetServerByName(faucet_name)

# Funding accounts during the build time
faucet.fund('0x72943017a1fa5f255fc0f06625aec22319fcd5b3', 2)
faucet.fund('0x5449ba5c5f185e9694146d60cfe72681e2158499', 5)


# Funding accounts during the run time, i.e., after the emulation starts 
faucetUserService = FaucetUserService()
faucetUserService.install('faucetUser').setDisplayName('FaucetUser')
faucetUserService.setFaucetServerInfo(faucet_info[0]['name'], faucet_info[0]['port'])

# Binding virtual nodes to physical nodes
emu.addBinding(Binding('faucetUser', filter=Filter(asn = 164, nodeName='host_0')))

# Add the layer 
emu.addLayer(faucetUserService)


emu.render()

if len(sys.argv) == 1:
    platform = "amd"
else:
    platform = sys.argv[1]

platform_mapping = {
    "amd": Platform.AMD64,
    "arm": Platform.ARM64
}

docker = Docker(etherViewEnabled=True, platform=platform_mapping[platform])
emu.compile(docker, './output', override=True)

