#!/usr/bin/env python3
# encoding: utf-8

from seedemu import *
from examples.internet.B03_hybrid_internet import hybrid_internet
from examples.blockchain.D00_ethereum_poa import component_poa

def run(dumpfile = None, hosts_per_as=3, total_eth_nodes=20, total_accounts_per_node=2):
    ###############################################################################

    # Run and load the pre-built Internet component
    emuA = Emulator()
    hybrid_internet.run(dumpfile='./component_base.bin', hosts_per_as=hosts_per_as)
    emuA.load('./component_base.bin')

    # Run and load the pre-built Ethereum component
    emuB = Emulator()
    vnode_list = component_poa.run(dumpfile='./component_poa.bin', 
                                   total_eth_nodes=total_eth_nodes, 
                                   total_accounts_per_node=total_accounts_per_node)
    emuB.load('./component_poa.bin')

    # Merge the two pre-built components
    emu = emuA.merge(emuB, DEFAULT_MERGERS)

    # Bind each v-node to a randomly selected physical nodes (no filters)
    for vnode in vnode_list:
        emu.addBinding(Binding(vnode))

    if dumpfile is not None:
        emu.dump(dumpfile)
    else:
        # Rendering and generate output files
        emu.render()
        docker = Docker(etherViewEnabled=True)
        emu.compile(docker, './output', override=True)

if __name__ == "__main__":
    run()
