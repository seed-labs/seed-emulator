#!/usr/bin/env python3
# encoding: utf-8

from seedemu import *
import sys, os

example_dir = "/".join(os.path.realpath(__file__).split("/")[0:-2])
sys.path.insert(1, example_dir)

from D00_blockchain_poa import blockchain_poa

def run(dumpfile = None):
    ###############################################################################
    emu = Emulator()
    local_dump_path = './blockchain-poa.bin'
    if not os.path.exists(local_dump_path):
        blockchain_poa.run(dumpfile=local_dump_path)
    # Load the pre-built components and merge them
    emu.load(local_dump_path)

    # Create the Chainlink Init server
    chainlink = ChainlinkService()
    cnode = 'chainlink_init_server'
    c_init = chainlink.installInitializer(cnode)
    c_init.setFaucetServerInfo(vnode = 'faucet', port = 80)
    c_init.setRPCbyEthNodeName('eth2')
    service_name = 'Chainlink-Init'
    emu.getVirtualNode(cnode).setDisplayName(service_name)
    emu.addBinding(Binding(cnode, filter = Filter(asn=151, nodeName='host_2')))

    i = 0
    c_asns  = [152, 153]
    # Create Chainlink normal servers
    for asn in c_asns:
        cnode = 'chainlink_server_{}'.format(i)
        c_normal = chainlink.install(cnode)
        c_normal.setRPCbyEthNodeName('eth{}'.format(i))
        c_normal.setInitNodeIP("chainlink_init_server")
        c_normal.setFaucetServerInfo(vnode = 'faucet', port = 80)
        service_name = 'Chainlink-{}'.format(i)
        emu.getVirtualNode(cnode).setDisplayName(service_name)
        emu.addBinding(Binding(cnode, filter = Filter(asn=asn, nodeName='host_2')))
        i = i + 1
        
    # Add the Chainlink layer
    emu.addLayer(chainlink)

    if dumpfile is not None:
        emu.dump(dumpfile)
    else:
        # Render and compile
        OUTPUTDIR = './output'
        emu.render()
        docker = Docker(internetMapEnabled=True, internetMapPort=8081, etherViewEnabled=True, platform=Platform.AMD64)
        emu.compile(docker, OUTPUTDIR, override = True)

if __name__ == "__main__":
    run()