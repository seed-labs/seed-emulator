#!/usr/bin/env python3
# encoding: utf-8

from seedemu import *
from examples.blockchain.D00_ethereum_poa import ethereum_poa
from seedemu.services.EthereumService import *
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
    ethInitInfo:EthInitAndInfoServer = blockchain.createEthInitAndInfoServer(vnode='eth_init_info', 
                                                                             port=5000, 
                                                                             linked_eth_node=random.choice(eth_nodes),
                                                                             linked_faucet_node=random.choice(faucet_info))
    ethInitInfo.deployContractByFilePath(contract_name='test', 
                        abi_path="./Contracts/contract.abi",
                        bin_path="./Contracts/contract.bin")
    ethInitInfo.setDisplayName('EthInitAndInfo')

    emu.addBinding(Binding('eth_init_info'))

    # Generate the emulator files
    if dumpfile is not None:
        emu.dump(dumpfile)
    else:
        emu.render()
        data = {}
        data['eth_init_info'] = str(emu.getBindingFor('eth_init_info').getInterfaces()[0].getAddress())
        data['faucet'] = str(emu.getBindingFor(random.choice(faucet_info)).getInterfaces()[0].getAddress())
        data['eth_node'] = str(emu.getBindingFor(random.choice(eth_nodes)).getInterfaces()[0].getAddress())
        # Save the data to a file
        with open('./../eth_init_info.json', 'w') as f:
            json.dump(data, f)
        if platform.machine() == 'aarch64' or platform.machine() == 'arm64':
            current_platform = Platform.ARM64
        else:
            current_platform = Platform.AMD64

        docker = Docker(etherViewEnabled=True, platform=current_platform, internetMapEnabled=False)
        emu.compile(docker, './output', override = True)

if __name__ == "__main__":
    run()


