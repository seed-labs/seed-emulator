#!/usr/bin/env python3
# encoding: utf-8

from seedemu import *
from seedemu.services.ChainlinkService.ChainlinkTemplates import *
from examples.blockchain.D00_ethereum_poa import ethereum_poa
import platform
import random


def run(dumpfile = None, total_chainlink_nodes = 3):
    ###############################################################################
    emu = Emulator()

    # Run and load the pre-built ethereum component; it is used as the base blockchain
    local_dump_path = './blockchain-poa.bin'
    ethereum_poa.run(dumpfile=local_dump_path, hosts_per_as=4, total_accounts_per_node=1)
    emu.load(local_dump_path)
    
    # Get the utility server instance
    # This server will be used to deploy the necessary contract, and provide
    # contract addresses to the Chainlink servers
    eth = emu.getLayer('EthereumService')
    blockchain = eth.getBlockchainByName(eth.getBlockchainNames()[0])
    util_name  = blockchain.getUtilityServerNames()[0]
    utility    = blockchain.getUtilityServerByName(util_name)

    # Create the Chainlink service, and set the faucet server. 
    # Accounts will be created for the Chainlink service, and they
    # will be funded via the faucet server. 
    chainlink = ChainlinkService()
    #chainlink.setEthServer(random.choice(eth_nodes)['name'])
    #chainlink.setFaucetServer(faucet_info[0]['name'])
    chainlink.setEthServer('eth5')
    chainlink.setFaucetServer('faucet')
    chainlink.setUtilityServer(util_name)
    
    # Create Chainlink nodes (called server in our code)
    # We need to provide a blockchain node for this node to send transactions
    # to the blockchain. 
    for i in range(total_chainlink_nodes):
        chainlink.install('chainlink_node_{}'.format(i)) \
                .setDisplayName('Chainlink-{}'.format(i))

    # Add the Chainlink layer
    emu.addLayer(chainlink)
    
    # Bind each Chainlink node to a physical node (no filters, so random binding)
    server_nodes = chainlink.getAllServerNames()
    for server_node in server_nodes['ChainlinkServer']:
        emu.addBinding(Binding(server_node))

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

    print("-----------------------------------------")
    print("Chainlink nodes: " + str(server_nodes))
    for type, server_list in blockchain.getAllServerNames().items():
        print("EthNodes: - type: "+ type + " - list: " + str(server_list))

if __name__ == "__main__":
    run()
