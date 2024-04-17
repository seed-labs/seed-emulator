#!/usr/bin/env python3
# encoding: utf-8

from seedemu import *
import os, sys
import platform
from typing import List

###############################################################################
emu = Emulator()
# Load the pre-built components and merge them
emu.load('./blockchain-poa.bin')

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

# Dump the merged topology
emu.dump('blockchain-chainlink.bin')

# Render and compile
OUTPUTDIR = './output'
emu.render()

docker = Docker(internetMapEnabled=True, internetMapPort=8081, etherViewEnabled=True, platform=Platform.AMD64)

emu.compile(docker, OUTPUTDIR, override = True)
