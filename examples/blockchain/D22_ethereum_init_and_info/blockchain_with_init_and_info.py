#!/usr/bin/env python3
# encoding: utf-8

from seedemu import *
from examples.blockchain.D00_ethereum_poa import ethereum_poa
import random
import platform

def run(dumpfile = None):
    ###############################################################################
    emu = Emulator()

    # Run and load the pre-built ethereum component; it is used as the base blockchain
    local_dump_path = './blockchain-poa.bin'
    ethereum_poa.run(dumpfile=local_dump_path, hosts_per_as=1, total_eth_nodes=10, total_accounts_per_node=1)
    emu.load(local_dump_path)
    
    # Get the blockchain and faucet information
    eth:EthereumService = emu.getLayer('EthereumService')
    blockchain: Blockchain =  eth.getBlockchainByName(eth.getBlockchainNames()[0])
    faucet_info = blockchain.getFaucetServerNames()
    eth_nodes   = blockchain.getEthServerNames()
    
    # Create the EthInit server, and set the eth node and faucet server.
    ethInitInfo:EthInitAndInfoServer = blockchain.createEthInitAndInfoServer('eth_init_info')
    ethInitInfo.setLinkedEthNode(vnodeName=random.choice(eth_nodes))
    ethInitInfo.setLinkedFaucetNode(vnodeName=random.choice(faucet_info))
    ethInitInfo.deployContract(contract_name='test', 
                        abi_path="./Contracts/contract.abi",
                        bin_path="./Contracts/contract.bin")
    ethInitInfo.setDisplayName('EthInitAndInfo')

    emu.addBinding(Binding('eth_init_info'))

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


