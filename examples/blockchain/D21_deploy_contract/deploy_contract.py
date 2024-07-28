#!/usr/bin/env python3
# encoding: utf-8

from seedemu import *
from examples.blockchain.D00_ethereum_poa import ethereum_poa
from seedemu.services.EthereumService import *
import os, sys

def run(dumpfile = None):
    ###############################################################################
    # Set the platform information
    if dumpfile is None:
        script_name = os.path.basename(__file__)

        if len(sys.argv) == 1:
            platform = Platform.AMD64
        elif len(sys.argv) == 2:
            if sys.argv[1].lower() == 'amd':
                platform = Platform.AMD64
            elif sys.argv[1].lower() == 'arm':
                platform = Platform.ARM64
            else:
                print(f"Usage:  {script_name} amd|arm")
                sys.exit(1)
        else:
            print(f"Usage:  {script_name} amd|arm")
            sys.exit(1)

    ###############################################################################
    emu = Emulator()

    # Run and load the pre-built ethereum component; it is used as the base blockchain
    # This component already has already created a utility server
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


