#!/usr/bin/env python3
# encoding: utf-8

from seedemu import *
from modify_df import change_line
import sys

CustomGenesisFileContent = """\
{
    "config": {
        "chainId": 1337,
        "homesteadBlock": 0,
        "eip150Block": 0,
        "eip150Hash": "0x0000000000000000000000000000000000000000000000000000000000000000",
        "eip155Block": 0,
        "eip158Block": 0,
        "byzantiumBlock": 0,
        "constantinopleBlock": 0,
        "petersburgBlock": 0,
        "istanbulBlock": 0,
        "muirGlacierBlock": 0,
        "berlinBlock": 0,
        "londonBlock": 0,
        "arrowGlacierBlock": 0,
        "grayGlacierBlock": 0,
        "clique": {
        "period": 2,
        "epoch": 30000
        }
    },
    "nonce": "0x0",
    "timestamp": "0x622a4e1a",
    "extraData": "0x0",
    "gasLimit": "0x1c9c380",
    "difficulty": "0x1",
    "mixHash": "0x0000000000000000000000000000000000000000000000000000000000000000",
    "coinbase": "0x0000000000000000000000000000000000000000",
    "alloc": {
        "0x4e59b44847b379578588920cA78FbF26c0B4956C": {
          "code": "0x7fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffe03601600081602082378035828234f58015156039578182fd5b8082525050506014600cf3",
          "balance": "0x0"
        },
        "0xdFC7d61047DAc7735d42Fd517e39e89C57083b45": {
          "balance": "0x200000000000000000000000000000000000000000000000000000000000000"
        },
        "0x9C1EA6d1f5E3E8aE21fdaF808b2e13698737643C": {
          "balance": "0x200000000000000000000000000000000000000000000000000000000000000"
        },
        "0x30ca907e4028346E93c081f30345d3319cb20972": {
          "balance": "0x200000000000000000000000000000000000000000000000000000000000000"
        },
        "0x2DDAaA366dc75119A256C41b9bd483D13A64389d": {
          "balance": "0x200000000000000000000000000000000000000000000000000000000000000"
        }
    },
    "number": "0x0",
    "gasUsed": "0x0",
    "parentHash": "0x0000000000000000000000000000000000000000000000000000000000000000",
    "baseFeePerGas": null
}
"""

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
blockchain.setGenesis(CustomGenesisFileContent)

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

l2_1 = l2Bkc.createNode("l2-1")
l2_2 = l2Bkc.createNode("l2-2")
l2_3 = l2Bkc.createNode("l2-3")
l2_4 = l2Bkc.createNode("l2-4")

l2_1.setSequencer(True)

# SC deployer node
# deployerHostname = base.getAutonomousSystem(154).getHosts()
# deployerHost = base.getAutonomousSystem(154).getHost(deployerHostname[0])
# deployerImageName = "sc-deployer:latest"
# deployerImage = DockerImage(deployerImageName, software=[])
# docker.addImage(deployerImage)
# docker.setImageOverride(deployerHost, deployerImageName)
# deployerHost.addBuildCommand("sed -i 's/net0/eth0/g' /start.sh")
# deployerHost.appendStartCommand("/l2/build.sh &> deployer.log", fork=True)

# Add external port
emu.getVirtualNode("l2-4").addPortForwarding(8545, l2_4.getRPCPort())


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
emu.addLayer(l2)

emu.dump("component-blockchain.bin")

emu.render()

# If output directory exists and override is set to false, we call exit(1)
# updateOutputdirectory will not be called
emu.compile(docker, "./output", override=True)
