#!/usr/bin/env python3
# encoding: utf-8

from seedemu import *
from modify_df import change_line
import sys

# Admin accounts
ADMIN_ACC = (
    "0xdFC7d61047DAc7735d42Fd517e39e89C57083b45",
    "0xd1e9509fa96d231fe323bda01cd954d4a74796a859ebe9dd638d5f0824d1ebd4",
)
BATCHER_ACC = (
    "0x9C1EA6d1f5E3E8aE21fdaF808b2e13698737643C",
    "0x742dd19d7c2ed107027d8844e72ebc34b83091e1f58a7e95009e829fe06a7b12",
)
PROPOSER_ACC = (
    "0x30ca907e4028346E93c081f30345d3319cb20972",
    "0x00683c828f09af18e0febb495ebee48fb2c581e2a6fa83e6ddaee3a359358af9",
)
SEQUENCER_ACC = (
    "0x0e259e03bABD47f8bab8Ec93a2C5fB39DB443a3d",
    "0x9a031a3aee8b73427b86d195b387a10dd471f5707709923a16882141b37a1c17",
)
TEST_ACC = (
    "0x2DDAaA366dc75119A256C41b9bd483D13A64389d",
    "0x4ba1ada11a1d234c3a03c08395c82e65320b5ae4aecca4a70143f4c157230528",
)
FACTORY_ACC = ("0x4e59b44847b379578588920cA78FbF26c0B4956C", "")

FACTORY_CODE = "0x7fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffe03601600081602082378035828234f58015156039578182fd5b8082525050506014600cf3"

emu = Makers.makeEmulatorBaseWith10StubASAndHosts(1)

if len(sys.argv) == 1:
    platform = "amd"
else:
    platform = sys.argv[1]

platform_mapping = {"amd": Platform.AMD64, "arm": Platform.ARM64}
docker = Docker(etherViewEnabled=True, platform=platform_mapping[platform])

# Create the Ethereum layer
# saveState=True: will set the blockchain folder using `volumes`,
# so the blockchain data will be preserved when containers are deleted.
eth = EthereumService(override=True)

# Create the 1 Blockchain layers, which is a sub-layer of Ethereum layer
# Need to specify chainName and consensus when create Blockchain layer.

# blockchain is a POA based blockchain
blockchain = eth.createBlockchain(chainName="POA", consensus=ConsensusMechanism.POA)

# Set custom genesis
initBal = 100000
blockchain.setGasLimitPerBlock(30_000_000)
blockchain.addLocalAccount(FACTORY_ACC[0], 0)
blockchain.addCode(FACTORY_ACC[0], FACTORY_CODE)
blockchain.addLocalAccount(ADMIN_ACC[0], initBal)
blockchain.addLocalAccount(BATCHER_ACC[0], initBal)
blockchain.addLocalAccount(PROPOSER_ACC[0], initBal)
blockchain.addLocalAccount(TEST_ACC[0], initBal)

# print(blockchain.getGenesis().getGenesis())

# Create blockchain nodes (POA Ethereum)
e5 = blockchain.createNode("poa-eth5")
e6 = blockchain.createNode("poa-eth6")
e7 = blockchain.createNode("poa-eth7")
e8 = blockchain.createNode("poa-eth8")

# Set bootnodes on e5. The other nodes can use these bootnodes to find peers.
# Start mining on e5,e6
# To start mine(seal) in POA consensus, the account should be unlocked first.
e5.setBootNode(True).unlockAccounts().startMiner()
e6.unlockAccounts().startMiner()

# Enable ws connection on e5 geth
# Set geth ws port to 8541 (Default : 8546)
e5.enableGethWs().setGethWsPort(8541)
e5.enableGethHttp()
e7.enableGethHttp()

# Customizing the display names (for visualization purpose)
emu.getVirtualNode("poa-eth5").setDisplayName("Ethereum-POA-5")
emu.getVirtualNode("poa-eth6").setDisplayName("Ethereum-POA-6")
emu.getVirtualNode("poa-eth7").setDisplayName("Ethereum-POA-7").addPortForwarding(
    12545, e7.getGethHttpPort()
)
emu.getVirtualNode("poa-eth8").setDisplayName("Ethereum-POA-8")

# Create Layer2 nodes
l2 = Layer2Service()
l2Bkc = l2.createL2Blockchain("test")

l2Bkc.setL1Node("poa-eth5", e5.getGethHttpPort())
l2Bkc.setAdminAccount(L2Account.GS_ADMIN, ADMIN_ACC)
l2Bkc.setAdminAccount(L2Account.GS_BATCHER, BATCHER_ACC)
l2Bkc.setAdminAccount(L2Account.GS_PROPOSER, PROPOSER_ACC)
l2Bkc.setAdminAccount(L2Account.GS_SEQUENCER, SEQUENCER_ACC)

l2_1 = l2Bkc.createNode("l2-1", L2Node.SEQUENCER)
l2_2 = l2Bkc.createNode("l2-2")
l2_3 = l2Bkc.createNode("l2-3")
l2_4 = l2Bkc.createNode("l2-4")
deployer = l2Bkc.createNode("l2-deployer", L2Node.DEPLOYER)

# Set external port
emu.getVirtualNode("l2-3").addPortForwarding(8545, l2_3.getRPCPort())


# Binding virtual nodes to physical nodes

emu.addBinding(Binding("poa-eth5", filter=Filter(asn=160, nodeName="host_0")))
emu.addBinding(Binding("poa-eth6", filter=Filter(asn=161, nodeName="host_0")))
emu.addBinding(Binding("poa-eth7", filter=Filter(asn=162, nodeName="host_0")))
emu.addBinding(Binding("poa-eth8", filter=Filter(asn=163, nodeName="host_0")))

# Add the layer and save the component to a file
emu.addLayer(eth)

emu.addBinding(Binding("l2-1", filter=Filter(asn=150, nodeName="host_0")))
emu.addBinding(Binding("l2-2", filter=Filter(asn=151, nodeName="host_0")))
emu.addBinding(Binding("l2-3", filter=Filter(asn=152, nodeName="host_0")))
emu.addBinding(Binding("l2-4", filter=Filter(asn=153, nodeName="host_0")))
emu.addBinding(Binding("l2-deployer", filter=Filter(asn=154, nodeName="host_0")))

emu.addLayer(l2)

emu.dump("component-blockchain.bin")

emu.render()

# If output directory exists and override is set to false, we call exit(1)
# updateOutputdirectory will not be called
emu.compile(docker, "./output", override=True)
