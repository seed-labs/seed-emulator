#!/usr/bin/env python3
# encoding: utf-8

from seedemu import *
import sys, os
import math, json
from eth_account import Account

###############################################################################
# Set the platform information
script_name = os.path.basename(__file__)

if len(sys.argv) < 2:
    print(f"Usage:  {script_name} <total_number_of_eth_nodes> [amd|arm]")
    # sys.exit(1)

# Read total number of Ethereum nodes from the command line argument
# try:
#     total_number_of_nodes = int(sys.argv[1])
# except ValueError:
#     print(f"Invalid number of Ethereum nodes: {sys.argv[1]}")
#     sys.exit(1)

# Optional platform argument
if len(sys.argv) == 3:
    if sys.argv[2].lower() == 'amd':
        platform = Platform.AMD64
    elif sys.argv[2].lower() == 'arm':
        platform = Platform.ARM64
    else:
        print(f"Usage:  {script_name} <total_number_of_eth_nodes> amd|arm")
        sys.exit(1)
else:
    platform = Platform.AMD64  # Default platform is AMD64




total_number_of_nodes=350
# Calculate how many hosts per stub AS are needed
# We know we have 10 stub AS (150-154, 160-164), and at least one node per AS is required
# to host a node (Beacon or Ethereum node).
total_stub_as = 10  # We have 10 ASNs available
hosts_per_stub_as = math.ceil(total_number_of_nodes / total_stub_as)

# Create Emulator Base with the calculated number of hosts per stub AS
emu = Makers.makeEmulatorBaseWith10StubASAndHosts(hosts_per_stub_as=hosts_per_stub_as)

print(f"Number of eth nodes per stub AS: {hosts_per_stub_as}")

# Create the Ethereum layer
eth = EthereumService()
###  ethserevice -> blockchain -> ethserver (gethserver/beaconserver/beaconsetup)
# Create the Blockchain layer which is a sub-layer of Ethereum layer. 说明是pos子类
blockchain = eth.createBlockchain(chainName="pos", consensus=ConsensusMechanism.POS)




# Generate a list of accounts and prefund them
accounts_total  = 1000
pre_funded_amount = 1000000
mnemonic = "gentle always fun glass foster produce north tail security list example gain"
Account.enable_unaudited_hdwallet_features()
for i in range(accounts_total):
     account = Account.from_mnemonic(mnemonic, account_path=f"m/44'/60'/0'/0/{i}")
     blockchain.addLocalAccount(address=account.address, balance=pre_funded_amount)


asns = [150, 151, 152, 153, 154, 160, 161, 162, 163, 164]

###################################################
# Ethereum GethNode
# geth_nodes_assigned = 0  # To track the number of Ethereum nodes assigned
beaconsetup_node_number=1


geth_node_number=100
beacon_node_number=100
vc_node_number=100



geth_nodes: List[PoSGethServer] = []
beacon_nodes: List[PoSBeaconServer] = []

vc_nodes: List[PoSVcServer] =[]

### 创建beaconsetupnode
beaconsetupServer: PoSBeaconSetupServer = blockchain.createBeaconSetupNode(f"BeaconSetupNode")
emu.getVirtualNode(f'BeaconSetupNode').setDisplayName('Ethereum-BeaconSetup')
### 创建gethnode
for i in range(geth_node_number):
    gethServer: PoSGethServer = blockchain.createGethNode(f"gethnode{i}")
    gethServer.enableGethHttp()
    gethServer.appendClassName(f'Ethereum-POS-Geth-{i+1}')
    geth_nodes.append(gethServer)
    emu.getVirtualNode(f'gethnode{i}').setDisplayName(f'Ethereum-POS-Geth-{i+1}')
## 创建beaconnode
for i in range(beacon_node_number):
    beaconServer: PoSBeaconServer = blockchain.createBeaconNode(f"beaconnode{i}")
    beaconServer.appendClassName(f'Ethereum-POS-Beacon-{i+1}')
    beaconServer.connectToGethNode(f"gethnode{(i+1)%len(geth_nodes)}")
    beacon_nodes.append(beaconServer)
    emu.getVirtualNode(f'beaconnode{i}').setDisplayName(f'Ethereum-POS-Beacon-{i+1}')
    # beaconServer.enablePOSValidatorAtGenesis()
# 设置bootnode
geth_nodes[0].setBootNode(True)
beacon_nodes[0].setBootNode(True)

for i in range(vc_node_number):
    VcServer: PoSVcServer=blockchain.createVcNode(f"vcnode{i}")
    VcServer.appendClassName(f'Ethereum-POS-Validator-{i+1}')

    VcServer.connectToBeaconNode(f"beaconnode{(i+1)%len(beacon_nodes)}")
    VcServer.enablePOSValidatorAtGenesis()
    vc_nodes.append(VcServer)
    emu.getVirtualNode(f'vcnode{i}').setDisplayName(f'Ethereum-POS-Validator-{i+1}')


assign_index = 0
total_nodes = len(geth_nodes) + len(beacon_nodes) + len(vc_nodes)
for asn in asns:
    for id in range(hosts_per_stub_as):
        if asn == 152 and id == 0:
            emu.addBinding(Binding('BeaconSetupNode',
                                   filter=Filter(asn=asn, nodeName=f'^host_{id}$'),
                                   action=Action.FIRST))
        else:
            if assign_index >= total_nodes:
                continue
            if assign_index < len(geth_nodes):
                name = f'gethnode{assign_index}'
            elif assign_index < len(geth_nodes) + len(beacon_nodes):
                name = f'beaconnode{assign_index - len(geth_nodes)}'
            else:
                name = f'vcnode{assign_index - len(geth_nodes) - len(beacon_nodes)}'
            emu.addBinding(Binding(name,
                                   filter=Filter(asn=asn, nodeName=f'^host_{id}$'),
                                   action=Action.FIRST))
            assign_index += 1



# Add Ethereum layer to the emulator
emu.addLayer(eth)
base_layer = emu.getLayer('Base')
for asn in asns:
    as_obj = base_layer.getAutonomousSystem(asn)
    net = as_obj.getNetwork('net0')
    # Extend host IP range from 71-99 to 71-199 (supports 129 hosts, enough for 50 per AS)
    # Router range is 200-254, so host must end at 199 to avoid conflict
    # Move DHCP range to 51-70 to avoid conflict with extended host range (71-199)
    net.setHostIpRange(hostStart=71, hostEnd=199, hostStep=1)

emu.render()

# Enable internetMap and etherView for visualization
docker = Docker(internetMapEnabled=True, etherViewEnabled=True, platform=platform)

# Compile the emulator to output
emu.compile(docker, './output', override=True)
