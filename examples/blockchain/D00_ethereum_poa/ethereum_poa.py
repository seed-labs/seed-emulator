#!/usr/bin/env python3
# encoding: utf-8

from seedemu import *
from examples.internet.B03_hybrid_internet import hybrid_internet
from examples.blockchain.D00_ethereum_poa import component_poa

def run(dumpfile = None, hosts_per_as=3, total_eth_nodes=20, total_accounts_per_node=2):

    # Run and load the pre-built Internet component
    emuA = Emulator()
    hybrid_internet.run(dumpfile='./component_base.bin', hosts_per_as=hosts_per_as)
    emuA.load('./component_base.bin')

    # Run and load the pre-built Ethereum component
    emuB = Emulator()
    component_poa.run(dumpfile='./component_poa.bin', 
                      total_eth_nodes=total_eth_nodes, 
                      total_accounts_per_node=total_accounts_per_node)
    emuB.load('./component_poa.bin')

    # Merge the two pre-built components
    emu = emuA.merge(emuB, DEFAULT_MERGERS)

    eth:EthereumService = emu.getLayer('EthereumService')
    blockchain: Blockchain =  eth.getBlockchainByName(eth.getBlockchainNames()[0])

    # Print out blockchain component information
    print(blockchain.getFaucetServerNames())
    print(blockchain.getFaucetServerInfo())
    print(blockchain.getEthServerInfo())
    print(blockchain.getEthServerNames())


    # Bind each node to a randomly selected physical nodes (no filters)
    faucet_servers = blockchain.getFaucetServerNames()
    eth_servers    = blockchain.getEthServerNames()
    for faucet in faucet_servers:
        emu.addBinding(Binding(faucet))
    for server in eth_servers:
        emu.addBinding(Binding(server))

    # Generate output
    if dumpfile is not None:
        emu.dump(dumpfile)
    else:
        emu.render()
        docker = Docker(etherViewEnabled=True)
        emu.compile(docker, './output', override=True)

if __name__ == "__main__":
    run()
