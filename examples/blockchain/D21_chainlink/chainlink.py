#!/usr/bin/env python3
# encoding: utf-8

from seedemu import *
from examples.blockchain.D00_ethereum_poa import ethereum_poa
import platform
import random


def run(dumpfile = None, total_chainlink_nodes = 3):
    ###############################################################################
    emu = Emulator()

    # Run and load the pre-built ethereum component; it is used as the base blockchain
    local_dump_path = './blockchain-poa.bin'
    ethereum_poa.run(dumpfile=local_dump_path, hosts_per_as=4)
    emu.load(local_dump_path)
    
    # Get the blockchain and faucet information
    eth:EthereumService = emu.getLayer('EthereumService')
    blockchain: Blockchain =  eth.getBlockchainByName(eth.getBlockchainNames()[0])
    faucet_info = blockchain.getFaucetServerInfo()
    eth_nodes   = blockchain.getEthServerNames()
    
    # Create the Chainlink service, and set the faucet server. 
    # Accounts will be created for the Chainlink service, and they
    # will be funded via the faucet server. 
    chainlink = ChainlinkService()
    chainlink.setFaucetServerInfo(faucet_info[0]['name'], faucet_info[0]['port'])
    
    # Create the Chainlink initialization server.
    # This server will be used to deploy the necessary contract, and provide
    # contract addresses to the Chainlink servers
    # We need to provide a blockchain node for this server to send transactions
    # to the blockchain. This is done via the setLinkedEthNode() method. 
    chainlink.installInitializer('chainlink_init_server') \
            .setLinkedEthNode(name=random.choice(eth_nodes)) \
            .setDisplayName('Chainlink-Init')

    # Create Chainlink nodes (called server in our code)
    # We need to provide a blockchain node for this node to send transactions
    # to the blockchain. 
    for i in range(total_chainlink_nodes):
        chainlink.install('chainlink_node_{}'.format(i)) \
                .setLinkedEthNode(name=random.choice(eth_nodes)) \
                .setDisplayName('Chainlink-{}'.format(i))

    # Add the Chainlink layer
    emu.addLayer(chainlink)

    # Get the Chainlink node names
    init_node    = chainlink.getChainlinkInitServerName()
    server_nodes = chainlink.getChainlinkServerNames()
    
    # Bind each Chainlink node to a physical node (no filters, so random binding)
    emu.addBinding(Binding(init_node))
    for cnode in server_nodes:
        emu.addBinding(Binding(cnode))

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
    print("Chainlink initialization node: " + init_node)

if __name__ == "__main__":
    run()
