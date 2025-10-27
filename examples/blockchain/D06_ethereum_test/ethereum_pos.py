#!/usr/bin/env python3
# encoding: utf-8

from seedemu import *
import sys, os
import math

###############################################################################
# Set the platform information
script_name = os.path.basename(__file__)

if len(sys.argv) < 2:
    print(f"Usage:  {script_name} <total_number_of_eth_nodes> [amd|arm]")
    sys.exit(1)

# Read total number of Ethereum nodes from the command line argument
try:
    total_number_of_eth_nodes = int(sys.argv[1])
except ValueError:
    print(f"Invalid number of Ethereum nodes: {sys.argv[1]}")
    sys.exit(1)

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

# Calculate how many hosts per stub AS are needed
# We know we have 10 stub AS (150-154, 160-164), and at least one node per AS is required
# to host a node (Beacon or Ethereum node).
total_stub_as = 10  # We have 10 ASNs available
hosts_per_stub_as = math.ceil(total_number_of_eth_nodes / total_stub_as)

# Create Emulator Base with the calculated number of hosts per stub AS
emu = Makers.makeEmulatorBaseWith10StubASAndHosts(hosts_per_stub_as=hosts_per_stub_as)

# Create the Ethereum layer
eth = EthereumService()

# Create the Blockchain layer which is a sub-layer of Ethereum layer.
blockchain = eth.createBlockchain(chainName="pos", consensus=ConsensusMechanism.POS)

asns = [150, 151, 152, 153, 154, 160, 161, 162, 163, 164]

###################################################
# Ethereum Node
i = 1
eth_nodes_assigned = 0  # To track the number of Ethereum nodes assigned

for asn in asns:
    for id in range(hosts_per_stub_as):
        # Skip creating more Ethereum nodes than required
        if eth_nodes_assigned >= total_number_of_eth_nodes:
            break
        
        # Create a blockchain virtual node
        e: EthereumServer = blockchain.createNode(f"eth{i}")
        
        # Create Docker Container Label
        e.appendClassName(f'Ethereum-POS-{i}')
        
        # Enable Geth to communicate via HTTP
        e.enableGethHttp()

        # Set the Beacon Setup Node for ASN 150, id 0 (Beacon node doesn't count towards total Ethereum nodes)
        if asn == 150 and id == 0:
            e.setBeaconSetupNode()
        
            # Beacon node is not counted as an Ethereum node, so we don't increment eth_nodes_assigned


        # Set Boot Node for ASN 151, id 0
        elif asn == 151 and id == 0:
            e.setBootNode(True)
            eth_nodes_assigned += 1

        # Set Validator at Running for ASN 152 (id 0) as the first node
        elif asn == 152 and id == 0:
            e.enablePOSValidatorAtRunning()
            eth_nodes_assigned += 1

        # Set Validator at Genesis for all other nodes
        else:
            e.enablePOSValidatorAtGenesis()
            eth_nodes_assigned += 1

        # Customizing the display names for visualization
        if e.isBeaconSetupNode():
            emu.getVirtualNode(f'eth{i}').setDisplayName('Ethereum-BeaconSetup')
        else:
            emu.getVirtualNode(f'eth{i}').setDisplayName(f'Ethereum-POS-{i}')

        # Binding the virtual node to the physical node
        emu.addBinding(Binding(f'eth{i}', filter=Filter(asn=asn, nodeName=f'host_{id}')))
        
        # Increment the Ethereum node index
        i += 1

        if eth_nodes_assigned >= total_number_of_eth_nodes:
            break

# Add Ethereum layer to the emulator
emu.addLayer(eth)

# Render the emulator setup
emu.render()

# Enable internetMap and etherView for visualization
docker = Docker(internetMapEnabled=True, etherViewEnabled=True, platform=platform)

# Compile the emulator to output
emu.compile(docker, './output', override=True)
