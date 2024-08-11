#!/usr/bin/env python3
# encoding: utf-8

import sys
from seedemu import *
from examples.blockchain.D05_ethereum_small import ethereum_small
import os, sys

###############################################################################
# Set the platform information
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
ethereum_small.run(dumpfile=local_dump_path)
emu.load(local_dump_path)

# Add two new nodes for oracle node and user node
base = emu.getLayer('Base')
as_  = base.getAutonomousSystem(150)
oracle_user = as_.createHost('oracle_user').joinNetwork('net0')
oracle_node = as_.createHost('oracle_node').joinNetwork('net0')

# Install needed software
installSoftware(oracle_user)
installSoftware(oracle_node)

# Set up the user node
oracle_user.setFile('/contract/Oracle.abi', 
             get_file_content('./contract/Oracle.abi'))

oracle_user.setFile('/oracle/user_create_account.py', 
             get_file_content('./code/user_create_account.py').format(
                chain_id=CHAIN_ID,
                eth_node=ETH_NODE1, eth_port=ETH_PORT,
                faucet_server=FAUCET, faucet_port=FAUCET_PORT
             ))

oracle_user.setFile('/oracle/user_get_price.py', 
             get_file_content('./code/user_get_price.py').format(
                chain_id=CHAIN_ID,
                faucet_server=FAUCET, faucet_port=FAUCET_PORT,
                utility_server=UTILITY, utility_port=UTILITY_PORT,
                eth_node=ETH_NODE1, eth_port=ETH_PORT, 
                oracle_contract_name=ORACLE_NAME
             ))

oracle_user.appendStartCommand('python3 /oracle/user_create_account.py &')

# Set up the oracle node 
oracle_node.setFile('/contract/Oracle.abi', 
             get_file_content('./contract/Oracle.abi'))
oracle_node.setFile('/contract/Oracle.bin', 
             get_file_content('./contract/Oracle.bin'))

oracle_node.setFile('/oracle/deploy_oracle_contract.py', 
             get_file_content('./code/deploy_oracle_contract.py').format(
                chain_id=CHAIN_ID,
                faucet_server=FAUCET, faucet_port=FAUCET_PORT,
                utility_server=UTILITY, utility_port=UTILITY_PORT,
                eth_node=ETH_NODE1, eth_port=ETH_PORT, 
                oracle_contract_name=ORACLE_NAME
              ))

oracle_node.setFile('/oracle/oracle_node_set_price.py', 
             get_file_content('./code/oracle_node_set_price.py').format(
                chain_id=CHAIN_ID,
                faucet_server=FAUCET, faucet_port=FAUCET_PORT,
                utility_server=UTILITY, utility_port=UTILITY_PORT,
                eth_node=ETH_NODE1, eth_port=ETH_PORT 
              ))


oracle_node.setFile('/oracle/oracle_node_start.sh', 
             get_file_content('./code/oracle_node_start.sh'))

oracle_node.appendStartCommand('bash /oracle/oracle_node_start.sh &')


emu.render()

docker = Docker(etherViewEnabled=True, platform=platform)
emu.compile(docker, './output', override=True)

