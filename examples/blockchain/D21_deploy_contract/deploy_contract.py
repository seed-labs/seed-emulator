#!/usr/bin/env python3
# encoding: utf-8

from seedemu import *
from examples.blockchain.D00_ethereum_poa import ethereum_poa
from seedemu.services.EthereumService import *
import platform

def run(dumpfile = None):
    ###############################################################################
    emu = Emulator()

    # Run and load the pre-built ethereum component; it is used as the base blockchain
    # This component already has already created a utility server
    local_dump_path = './blockchain-poa.bin'
    ethereum_poa.run(dumpfile=local_dump_path, hosts_per_as=1, 
                     total_eth_nodes=10, total_accounts_per_node=1)
    emu.load(local_dump_path)
    
    # Get the utility server 
    eth = emu.getLayer('EthereumService')
    blockchain = eth.getBlockchainByName(eth.getBlockchainNames()[0])
    name       = blockchain.getEthUtilityServerNames()[0]
    utility    = blockchain.getEthUtilityServerByName(name)

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
        if platform.machine() == 'aarch64' or platform.machine() == 'arm64':
            current_platform = Platform.ARM64
        else:
            current_platform = Platform.AMD64

        docker = Docker(etherViewEnabled=True, platform=current_platform)
        emu.compile(docker, './output', override = True)

if __name__ == "__main__":
    run()


