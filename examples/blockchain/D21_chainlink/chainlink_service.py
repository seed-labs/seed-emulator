#!/usr/bin/env python3
# encoding: utf-8

from seedemu import *
from examples.blockchain.D00_ethereum_poa import ethereum_poa
import platform
import random


def run(dumpfile = None, total_chainlink_nodes = 3):
    ###############################################################################
    emuA = Emulator()
    local_dump_path = './blockchain-poa.bin'
    # Run and load the pre-built ethereum poa component
    ethereum_poa.run(dumpfile=local_dump_path, hosts_per_as=4)
    emuA.load(local_dump_path)
    
    eth:EthereumService = emuA.getLayer('EthereumService')
    blockchain: Blockchain =  eth.getBlockchainByName(eth.getBlockchainNames()[0])
    faucet_dict = blockchain.getFaucetServerInfo()
    eth_nodes = blockchain.getEthServerNames()
    
    emuB = Emulator()
    # Build the chainlink service
    chainlink_nodes = []
    chainlink = ChainlinkService()
    # Set the faucet server in the service class
    chainlink.setFaucetServer(faucet_dict[0]['name'], faucet_dict[0]['port'])
    
    # Create Chainlink init server
    cnode = 'chainlink_init_server'
    chainlink.installInitializer(cnode) \
            .setLinkedEthNode(name=random.choice(eth_nodes)) \
            .setDisplayName('Chainlink-Init')

    # Create Chainlink normal servers
    for i in range(total_chainlink_nodes):
        cnode = 'chainlink_server_{}'.format(i)
        chainlink.install(cnode) \
                .setLinkedEthNode(name=random.choice(eth_nodes)) \
                .setDisplayName('Chainlink-{}'.format(i))

    init_node    = chainlink.getChainlinkInitServerName()
    server_nodes = chainlink.getChainlinkServerNames()
    
    # Add the Chainlink layer
    emuB.addLayer(chainlink)
    
    # Merge the two components
    emu = emuA.merge(emuB, DEFAULT_MERGERS)
    
    # Bind each v-node to a randomly selected physical nodes (no filters)
    emu.addBinding(Binding(init_node))
    for cnode in server_nodes:
        emu.addBinding(Binding(cnode))
    
    if dumpfile is not None:
        emu.dump(dumpfile)
    else:
        # Render and compile
        emu.render()
        if platform.machine() == 'aarch64' or platform.machine() == 'arm64':
            current_platform = Platform.ARM64
        else:
            current_platform = Platform.AMD64

        docker = Docker(etherViewEnabled=True, platform=current_platform)
        emu.compile(docker, './output', override = True)

    print("-------------------")
    print("Chainlink server nodes: " + str(server_nodes))
    print("Chainlink initialization node: " + init_node)

if __name__ == "__main__":
    run()
