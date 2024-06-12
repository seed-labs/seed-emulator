#!/usr/bin/env python3
# encoding: utf-8

import sys
from seedemu import *
from examples.blockchain.D05_ethereum_small import ethereum_small

# These hostnames are already set up in D05_ethereum_small
ETH_NODE1 = 'eth-3.net'
ETH_NODE2 = 'eth-5.net'
FAUCET    = 'faucet.net'
UTILITY   = 'utility.net'
FAUCET_PORT  = 80
UTILITY_PORT = 5000
ETH_PORT     = 8545
CHAIN_ID     = 1337
ORACLE_NAME  = 'oracle-contract'

def get_file_content(filename):
    """!
    @brief Get the content of a file
    """
    with open(filename, "r") as f:
        return f.read()

def installSoftware(node: Node):
    """
    @brief Install the software and library
    """
    software_list = ['curl', 'python3', 'python3-pip']
    for software in software_list:
        node.addSoftware(software)

    node.addBuildCommand('pip3 install web3==5.31.1')

    node.setFile('/oracle/EthereumHelper.py',
             get_file_content('./code/EthereumHelper.py'))

    node.setFile('/oracle/FaucetHelper.py',
             get_file_content('./code/FaucetHelper.py'))

    node.setFile('/oracle/UtilityServerHelper.py',
             get_file_content('./code/UtilityServerHelper.py'))



emu = Emulator()

# Run and load the pre-built ethereum component
local_dump_path = './ethereum-small.bin'
#ethereum_small.run(dumpfile=local_dump_path)
emu.load(local_dump_path)

# Add two new nodes for oracle node and user node
base = emu.getLayer('Base')
as_  = base.getAutonomousSystem(150)
node1 = as_.createHost('user').joinNetwork('net0')


emu.render()

if len(sys.argv) == 1:
    platform = "amd"
else:
    platform = sys.argv[1]

platform_mapping = {
    "amd": Platform.AMD64,
    "arm": Platform.ARM64
}

docker = Docker(etherViewEnabled=True, platform=platform_mapping[platform])
emu.compile(docker, './output', override=True)

