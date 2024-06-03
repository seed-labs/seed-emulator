#!/usr/bin/env python3
# encoding: utf-8

import sys
from seedemu import *
from examples.blockchain.D00_ethereum_poa import ethereum_poa


emu = Emulator()

# Run and load the pre-built ethereum component; it is used as the base blockchain
local_dump_path = './blockchain-poa.bin'
ethereum_poa.run(dumpfile=local_dump_path, total_accounts_per_node=1)
emu.load(local_dump_path)

# Get the faucet server instance
eth = emu.getLayer('EthereumService')
blockchain  = eth.getBlockchainByName(eth.getBlockchainNames()[0])
faucet_info = blockchain.getFaucetServerInfo()
faucet_name = blockchain.getFaucetServerNames()[0]
faucet      = blockchain.getFaucetServerByName(faucet_name)

# Funding accounts during the build time
# faucet.fund('0x72943017a1fa5f255fc0f06625aec22319fcd5b3', 2)
faucet.fund('0x5449ba5c5f185e9694146d60cfe72681e2158499', 5)
faucet.setDisplayName('faucet')
faucet.addHostName('faucet.com')


# The following API returns a script (bash or python). 
# The script will take the address and amount as command line arguments.
# It uses the hostname to refer to the faucet server, instead of the IP
fund_script = faucet.getFundingScript()
base: Base = emu.getLayer('Base')
as152 = base.getAutonomousSystem(152)
user_node = as152.createHost('user_node').joinNetwork('net0')
# Set python script to create ethereum address
user_node.setFile('create_eth.py', '''\
from eth_account import Account
import os

# Define the directory and file path
fund_queue_dir = '/fund_queue'
if not os.path.exists(fund_queue_dir):
    os.makedirs(fund_queue_dir)

file_path = os.path.join(fund_queue_dir, 'test.txt')

for i in range(3):
    # Generate a new Ethereum account
    account = Account.create()

    # Extract the address and private key
    address = account.address

    # Save the address and private key to a file
    with open(file_path, 'a') as f:
        f.write(f"{address}:10\\n")
    
    with open('test.txt', 'a') as f:
        f.write(f"{address}:10\\n")

print(f"Ethereum address and private key saved to {file_path}")
''')
user_node.addSoftware('python3 python3-pip')
user_node.addBuildCommand('pip3 install eth-account')
user_node.appendUserStartCommand('python3 /create_eth.py')
user_node.setFile('fund.sh', fund_script)
user_node.setFile('/fund_queue/test2.txt', '0x72943017a1fa5f255fc0f06625aec22319fcd5b3:10')
user_node.appendUserStartCommand('chmod +x fund.sh')
user_node.appendUserStartCommand('/fund.sh &')
user_node.setDisplayName('user_node')

# Funding accounts during the run time, i.e., after the emulation starts 
faucetUserService = FaucetUserService()
faucetUserService.install('faucetUser').setDisplayName('FaucetUser')
faucetUserService.setFaucetServerInfo(faucet_info[0]['name'], faucet_info[0]['port'])

# Binding virtual nodes to physical nodes
# emu.addBinding(Binding('faucet'), fileter=Filter(asn=1))
emu.addBinding(Binding('faucetUser', filter=Filter(asn = 164, nodeName='host_2')))

# Add the layer 
emu.addLayer(faucetUserService)
emu.addLayer(EtcHosts())

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
# user_node.print(indent=4)

