#!/usr/bin/env python3
# encoding: utf-8

import sys, os
from seedemu import *
from examples.blockchain.D00_ethereum_poa import ethereum_poa
from examples.blockchain.D01_ethereum_pos import ethereum_pos

###############################################################################
# Set the platform information
script_name = os.path.basename(__file__)

consensus = 'poa'
platform = Platform.AMD64
if len(sys.argv) >= 2:
    arg1 = sys.argv[1].lower()
    if arg1 in ['poa', 'pos']:
        consensus = arg1
        if len(sys.argv) == 3:
            arg2 = sys.argv[2].lower()
            if arg2 == 'amd':
                platform = Platform.AMD64
            elif arg2 == 'arm':
                platform = Platform.ARM64
            else:
                print(f"Usage:  {script_name} [poa|pos] [amd|arm]")
                sys.exit(1)
        elif len(sys.argv) > 3:
            print(f"Usage:  {script_name} [poa|pos] [amd|arm]")
            sys.exit(1)
    else:
        if arg1 == 'amd':
            platform = Platform.AMD64
        elif arg1 == 'arm':
            platform = Platform.ARM64
        else:
            print(f"Usage:  {script_name} [poa|pos] [amd|arm]")
            sys.exit(1)

emu = Emulator()

if consensus == 'pos':
    local_dump_path = './blockchain_pos.bin'
    ethereum_pos.run(dumpfile=local_dump_path)
else:
    local_dump_path = './blockchain_poa.bin'
    ethereum_poa.run(dumpfile=local_dump_path, total_accounts_per_node=1)
emu.load(local_dump_path)

# Get the faucet server instance
eth = emu.getLayer('EthereumService')
blockchain  = eth.getBlockchainByName(eth.getBlockchainNames()[0])
faucet_name = blockchain.getFaucetServerNames()[0]
faucet      = blockchain.getFaucetServerByName(faucet_name)

# Funding accounts during the build time. The actual funding
# is carried out after the emulator starts
faucet.fund('0x72943017a1fa5f255fc0f06625aec22319fcd5b3', 2)
faucet.fund('0x5449ba5c5f185e9694146d60cfe72681e2158499', 5)

# Funding accounts during the run time, i.e., after the emulation starts 
faucetUserService = FaucetUserService()
faucetUserService.install('faucetUser').setDisplayName('FaucetUser')
faucet_info = blockchain.getFaucetServerInfo()
faucetUserService.setFaucetServerInfo(faucet_info[0]['name'], 
                                      faucet_info[0]['port'])
emu.addBinding(Binding('faucetUser'))
emu.addLayer(faucetUserService)

emu.render()

docker = Docker(etherViewEnabled=True, platform=platform)
emu.compile(docker, './output', override=True)
# user_node.print(indent=4)