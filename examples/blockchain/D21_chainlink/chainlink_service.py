#!/usr/bin/env python3
# encoding: utf-8

from seedemu import *
from examples.blockchain.D00_ethereum_poa import ethereum_poa
import os
import platform


def run(dumpfile = None, total_chainlink_nodes = 3):
    ###############################################################################
    emuA = Emulator()
    local_dump_path = './blockchain-poa.bin'
    if not os.path.exists(local_dump_path):
        ethereum_poa.run(dumpfile=local_dump_path, hosts_per_as=4)
    # Load the pre-built ethereum poa component
    emuA.load(local_dump_path)

    # Build the chainlink service
    emuB = Emulator()
    cnode_dict = {}
    chainlink = ChainlinkService()
    cnode = 'chainlink_init_server'
    c_init = chainlink.installInitializer(cnode)
    c_init.setFaucetServerInfo(vnode = 'faucet', port = 80)
    c_init.setRPCbyEthNodeName('eth2')
    service_name = 'Chainlink-Init'
    cnode_dict[cnode] = service_name

    # Create Chainlink normal servers
    for i in range(total_chainlink_nodes):
        cnode = 'chainlink_server_{}'.format(i)
        c_normal = chainlink.install(cnode)
        c_normal.setRPCbyEthNodeName('eth{}'.format(i))
        c_normal.setInitNodeIP("chainlink_init_server")
        c_normal.setFaucetServerInfo(vnode = 'faucet', port = 80)
        service_name = 'Chainlink-{}'.format(i)
        cnode_dict[cnode] = service_name
        i = i + 1
    
    # Add the Chainlink layer
    emuB.addLayer(chainlink)
    
    # Merge the two components
    emu = emuA.merge(emuB, DEFAULT_MERGERS)
    
    # Bind each v-node to a randomly selected physical nodes (no filters)
    for cnode in cnode_dict:
        emu.getVirtualNode(cnode).setDisplayName(cnode_dict[cnode])
        emu.addBinding(Binding(cnode))
    
    if dumpfile is not None:
        emu.dump(dumpfile)
    else:
        # Render and compile
        OUTPUTDIR = './output'
        emu.render()
        if platform.machine() == 'aarch64' or platform.machine() == 'arm64':
            current_platform = Platform.ARM64
        else:
            current_platform = Platform.AMD64
        docker = Docker(internetMapEnabled=True, internetMapPort=8081, etherViewEnabled=True, platform=current_platform)
        emu.compile(docker, OUTPUTDIR, override = True)

if __name__ == "__main__":
    run()
