#!/usr/bin/env python3
# encoding: utf-8

from seedemu import *
from seedemu.services.ChainlinkService.ChainlinkTemplates import *
from examples.blockchain.D00_ethereum_poa import ethereum_poa
import os, sys
import random


def run(dumpfile = None, total_chainlink_nodes = 3):
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
    local_dump_path = './blockchain_poa.bin'
    ethereum_poa.run(dumpfile=local_dump_path, hosts_per_as=4, total_accounts_per_node=1)
    emu.load(local_dump_path)
    
    # Get the blockchain instance; we need to get some information from it
    eth = emu.getLayer('EthereumService')
    blockchain  = eth.getBlockchainByName(eth.getBlockchainNames()[0])

    # Create the Chainlink service
    chainlink = ChainlinkService(
                    eth_server=random.choice(blockchain.getEthServerNames()), 
                    faucet_server=blockchain.getFaucetServerNames()[0],
                    utility_server=blockchain.getUtilityServerNames()[0]
                )   

    # Create Chainlink nodes (called server in our code)
    server_names = []
    for i in range(total_chainlink_nodes):
        chainlink.install('chainlink_node_{}'.format(i)) \
                 .setDisplayName('Chainlink-{}'.format(i))
        server_names.append('chainlink_node_{}'.format(i)) 

    # Create a Chainlink user node
    chainlink.installUserServer('user_server') \
             .setChainlinkServers(server_names) \
             .setDisplayName('Chainlink-User')


    # Add the Chainlink layer
    emu.addLayer(chainlink)
    
    # Bind each Chainlink node to a physical node (no filters, so bind randomly)
    for server in server_names:
        emu.addBinding(Binding(server))

    emu.addBinding(Binding('user_server'))

    # Generate the emulator files
    if dumpfile is not None:
        emu.dump(dumpfile)
    else:
        emu.render()

        docker = Docker(etherViewEnabled=True, platform=platform)
        emu.compile(docker, './output', override = True)

    print("-----------------------------------------")
    print("Blockchain nodes: " + str(blockchain.getAllServerNames()))
    print("-----------------------------------------")
    print("Chainlink nodes:  " + str(chainlink.getAllServerNames()))

if __name__ == "__main__":
    run()
