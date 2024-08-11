#!/usr/bin/env python3
# encoding: utf-8

from seedemu import *
from L2Util import generateAccounts, writeConfig
from lib.services.EthereumLayer2Service import *
from lib.services.EthereumService.EthUtil import CustomGenesis
from lib.services.EthereumService.EthereumService import CustomBlockchain

import sys

# Configs for L2Util
L1_PORT = 12545
L2_PORT = 8545
DEPLOYER_PORT = 8888

# Generate privileged & test accounts for layer2
accs = generateAccounts()

emu = Makers.makeEmulatorBaseWith10StubASAndHosts(1)

if len(sys.argv) == 1:
    platform = "amd"
else:
    platform = sys.argv[1]

platform_mapping = {"amd": Platform.AMD64, "arm": Platform.ARM64}
docker = Docker(etherViewEnabled=True, platform=platform_mapping[platform])

# Create the Ethereum layer
eth = EthereumService(override=True)

# Create the 1 Blockchain layers, which is a sub-layer of Ethereum layer
blockchain = eth.createBlockchain(chainName="POA", consensus=ConsensusMechanism.POA)
blockchain.__class__ = CustomBlockchain

# Customize blockchain genesis file
initBal = 10**8
# Set the gas limit per block to 30,000,000 for layer2 smart contract deployment
blockchain.setGasLimitPerBlock(30_000_000)
# Pre-deploy the smart contract factory for layer2 smart contract deployment
blockchain.addLocalAccount(EthereumLayer2SCFactory.ADDRESS.value, 0)
blockchain.addCode(
    EthereumLayer2SCFactory.ADDRESS.value, EthereumLayer2SCFactory.BYTECODE.value
)
# Funding accounts
blockchain.addLocalAccount(accs[EthereumLayer2Account.GS_ADMIN][0], initBal)
blockchain.addLocalAccount(accs[EthereumLayer2Account.GS_BATCHER][0], initBal)
blockchain.addLocalAccount(accs[EthereumLayer2Account.GS_PROPOSER][0], initBal)
blockchain.addLocalAccount(accs[EthereumLayer2Account.GS_TEST][0], initBal)


# Create blockchain nodes (POA Ethereum)
e5 = blockchain.createNode("poa-eth5")
e6 = blockchain.createNode("poa-eth6")
e7 = blockchain.createNode("poa-eth7")
e8 = blockchain.createNode("poa-eth8")

# Set bootnodes on e5. The other nodes can use these bootnodes to find peers.
# Start mining on e5,e6
e5.setBootNode(True).unlockAccounts().startMiner()
e6.unlockAccounts().startMiner()

# Enable ws and http connections
# Set geth ws port to 8541 (Default : 8546)
e5.enableGethWs().setGethWsPort(8541)
e5.enableGethHttp()
e6.enableGethHttp()
e7.enableGethHttp()

# Customizing the display names (for visualization purpose)
emu.getVirtualNode("poa-eth5").setDisplayName("Ethereum-POA-5")
emu.getVirtualNode("poa-eth6").setDisplayName("Ethereum-POA-6")
emu.getVirtualNode("poa-eth7").setDisplayName("Ethereum-POA-7").addPortForwarding(
    L1_PORT, e7.getGethHttpPort()
)
emu.getVirtualNode("poa-eth8").setDisplayName("Ethereum-POA-8")

### Start setting up Layer2 ###

# Create Layer2 service
l2 = EthereumLayer2Service()

# Create a Layer2 blockchain, name is required
l2Bkc = l2.createL2Blockchain("test")

# Set the layer1 node to be connected for all the nodes in this layer2 blockchain
# All the layer2 nodes are required to connect to a layer1 node
l2Bkc.setL1VNode("poa-eth5", e5.getGethHttpPort())

# Configure the admin accounts for layer2 blockchain
# Admin, batcher, proposer, and test must be funded in the layer1 blockchain
l2Bkc.setAdminAccount(
    EthereumLayer2Account.GS_ADMIN, accs[EthereumLayer2Account.GS_ADMIN]
)
l2Bkc.setAdminAccount(
    EthereumLayer2Account.GS_BATCHER, accs[EthereumLayer2Account.GS_BATCHER]
)
l2Bkc.setAdminAccount(
    EthereumLayer2Account.GS_PROPOSER, accs[EthereumLayer2Account.GS_PROPOSER]
)
l2Bkc.setAdminAccount(
    EthereumLayer2Account.GS_SEQUENCER, accs[EthereumLayer2Account.GS_SEQUENCER]
)
l2Bkc.setAdminAccount(
    EthereumLayer2Account.GS_TEST, accs[EthereumLayer2Account.GS_TEST]
)

# Create layer2 nodes
# Set l2-1 to be a sequencer node, only one sequencer node is allowed in a layer2 blockchain
l2_1 = l2Bkc.createNode("l2-1", EthereumLayer2Node.SEQUENCER)

# Each node can have a individual layer1 node to connect to,
# this setting will override the blockchain setting
l2_2 = l2Bkc.createNode("l2-2").setL1VNode("poa-eth6", e6.getGethHttpPort())

# Default type of the node is the non-sequencer node
# Set the http port for l2-3 (default: 8545)
l2_3 = l2Bkc.createNode("l2-3").setHttpPort(9545)
# Set the ws port for l2-4  (default: 8546)
l2_4 = l2Bkc.createNode("l2-4").setWSPort(9547)

# Set the deployer node, which is used to deploy the smart contract
# Only one deployer node is allowed in a layer2 blockchain
deployer = l2Bkc.createNode("l2-deployer", EthereumLayer2Node.DEPLOYER)

# Set an external port for user interaction
emu.getVirtualNode("l2-1").addPortForwarding(L2_PORT, l2_1.getHttpPort())
emu.getVirtualNode("l2-deployer").addPortForwarding(
    DEPLOYER_PORT, EthereumLayer2Template.WEB_SERVER_PORT
)

# Save the configuration to interact with the layer2 blockchain
writeConfig(L1_PORT, L2_PORT, DEPLOYER_PORT, blockchain.getChainId(), l2Bkc.getChainID())

# Binding virtual nodes to physical nodes
emu.addBinding(Binding("poa-eth5", filter=Filter(asn=160, nodeName="host_0")))
emu.addBinding(Binding("poa-eth6", filter=Filter(asn=161, nodeName="host_0")))
emu.addBinding(Binding("poa-eth7", filter=Filter(asn=162, nodeName="host_0")))
emu.addBinding(Binding("poa-eth8", filter=Filter(asn=163, nodeName="host_0")))

# Add the ethereum layer
emu.addLayer(eth)

emu.addBinding(Binding("l2-1", filter=Filter(asn=150, nodeName="host_0")))
emu.addBinding(Binding("l2-2", filter=Filter(asn=151, nodeName="host_0")))
emu.addBinding(Binding("l2-3", filter=Filter(asn=152, nodeName="host_0")))
emu.addBinding(Binding("l2-4", filter=Filter(asn=153, nodeName="host_0")))
emu.addBinding(Binding("l2-deployer", filter=Filter(asn=154, nodeName="host_0")))

emu.addLayer(l2)
# Save the component to a file
emu.dump("component-blockchain.bin")

emu.render()

# If output directory exists and override is set to false, we call exit(1)
# updateOutputdirectory will not be called
emu.compile(docker, "./output", override=True)
