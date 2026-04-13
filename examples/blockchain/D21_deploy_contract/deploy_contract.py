#!/usr/bin/env python3
# encoding: utf-8

from seedemu import *
from examples.blockchain.D00_ethereum_poa import ethereum_poa
from examples.blockchain.D01_ethereum_pos import ethereum_pos
from seedemu.services.EthereumService import *
import os, sys

def run(dumpfile = None):
    ###############################################################################
    # Set the platform information
    consensus = 'poa'
    platform = Platform.AMD64
    if dumpfile is None:
        script_name = os.path.basename(__file__)

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

    ###############################################################################
    emu = Emulator()

    # Run and load the pre-built ethereum component; it is used as the base blockchain
    # This component already has already created a utility server
    if consensus == 'pos':
        local_dump_path = './blockchain_pos.bin'
        ethereum_pos.run(dumpfile=local_dump_path)
    else:
        local_dump_path = './blockchain_poa.bin'
        ethereum_poa.run(dumpfile=local_dump_path, hosts_per_as=1, 
                         total_eth_nodes=10, total_accounts_per_node=1)
    emu.load(local_dump_path)
    
    # Get the utility server 
    eth = emu.getLayer('EthereumService')
    blockchain = eth.getBlockchainByName(eth.getBlockchainNames()[0])
    name       = blockchain.getUtilityServerNames()[0]
    utility    = blockchain.getUtilityServerByName(name)

    # Deploy contract on the utility server
    # The actual deployment is carried out at the run time. 
    # This API just sets it up
    utility.deployContractByFilePath(contract_name='test',
                        abi_path="./Contracts/contract.abi",
                        bin_path="./Contracts/contract.bin")

    # Generate the emulator files
    if dumpfile is not None:
        emu.dump(dumpfile)
    else:
        emu.render()

        docker = Docker(etherViewEnabled=True, platform=platform)
        emu.compile(docker, './output', override = True)

if __name__ == "__main__":
    run()


