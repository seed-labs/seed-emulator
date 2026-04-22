#!/usr/bin/env python3
# encoding: utf-8

from seedemu import *
import sys, os
import math
from eth_account import Account

DOMAIN = ".net"

def run(dumpfile = None, total_beacon_nodes=3, vc_per_beacon=3):
    ###############################################################################
    # Set the platform information
    if dumpfile is None:
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

    # Configure the number of nodes
    geth_node_number = total_beacon_nodes
    beacon_node_number = total_beacon_nodes
    vc_node_number = vc_per_beacon * beacon_node_number
    # Create Emulator Base with 10 Stub AS (150-154, 160-164) using Makers utility method.
    # hosts_per_stub_as=3 : create 3 hosts per one stub AS.
    # It will create hosts(physical node) named `host_{}`.format(counter), counter starts from 0. 
    hosts_per_stub_as = 3
    emu = Makers.makeEmulatorBaseWith10StubASAndHosts(hosts_per_stub_as = hosts_per_stub_as)
    
    # Create the Ethereum layer
    eth = EthereumService()
    # Create the Blockchain layer which is a sub-layer of Ethereum layer.
    # chainName="pos": set the blockchain name as "pos"
    # consensus="ConsensusMechnaism.POS" : set the consensus of the blockchain as "ConsensusMechanism.POS".
    # supported consensus option: ConsensusMechanism.POA, ConsensusMechanism.POW, ConsensusMechanism.POS
    blockchain = eth.createBlockchain(chainName="pos", consensus=ConsensusMechanism.POS)
    # Generate a list of accounts and prefund them
    accounts_total  = 10
    pre_funded_amount = 1000000
    mnemonic = "gentle always fun glass foster produce north tail security list example gain"
    Account.enable_unaudited_hdwallet_features()
    for i in range(accounts_total):
        account = Account.from_mnemonic(mnemonic, account_path=f"m/44'/60'/0'/0/{i}")
        blockchain.addLocalAccount(address=account.address, balance=pre_funded_amount)
    asns = [150, 151, 152, 153, 154, 160, 161, 162, 163, 164]
    geth_nodes: List[PoSGethServer] = []
    beacon_nodes: List[PoSBeaconServer] = []
    vc_nodes: List[PoSVcServer] =[]
    # Create the BeaconSetupNode
    beaconsetupServer: PoSBeaconSetupServer = blockchain.createBeaconSetupNode(f"BeaconSetupNode")
    emu.getVirtualNode(f'BeaconSetupNode').setDisplayName('Ethereum-POS-BeaconSetup')
    for i in range(geth_node_number):
        gethServer: PoSGethServer = blockchain.createGethNode(f"gethnode{i}")
        gethServer.enableGethHttp()
        gethServer.appendClassName(f'Ethereum-POS-Geth-{i+1}')
        gethServer.addHostName(f"gethnode{i}" + DOMAIN)
        geth_nodes.append(gethServer)
        emu.getVirtualNode(f'gethnode{i}').setDisplayName(f'Ethereum-POS-Geth-{i+1}')
    
    # Create Beacon nodes and connect to Geth nodes
    for i in range(beacon_node_number):
        beaconServer: PoSBeaconServer = blockchain.createBeaconNode(f"beaconnode{i}")
        beaconServer.appendClassName(f'Ethereum-POS-Beacon-{i+1}')
        beaconServer.connectToGethNode(f"gethnode{(i+1)%len(geth_nodes)}")
        beacon_nodes.append(beaconServer)
        emu.getVirtualNode(f'beaconnode{i}').setDisplayName(f'Ethereum-POS-Beacon-{i+1}')
    
    # Set boot nodes
    geth_nodes[0].setBootNode(True)
    beacon_nodes[0].setBootNode(True)
    
    # Create Validator nodes and connect to Beacon nodes
    for i in range(vc_node_number):
        VcServer: PoSVcServer=blockchain.createVcNode(f"vcnode{i}")
        VcServer.appendClassName(f'Ethereum-POS-Validator-{i+1}')
        VcServer.connectToBeaconNode(f"beaconnode{(i+1)%len(beacon_nodes)}")
        VcServer.enablePOSValidatorAtGenesis()
        vc_nodes.append(VcServer)
        emu.getVirtualNode(f'vcnode{i}').setDisplayName(f'Ethereum-POS-Validator-{i+1}')
    
    # Create the Faucet server
    faucet:FaucetServer = blockchain.createFaucetServer(
                vnode='faucet',
                port=80,
                linked_eth_node='gethnode1',
                balance=10000,
                max_fund_amount=10)
    faucet.setDisplayName('Faucet')
    faucet.addHostName('faucet' + DOMAIN)
    # Create the Utility server
    util_server:EthUtilityServer = blockchain.createEthUtilityServer(
                vnode='utility',
                port=5000,
                linked_eth_node='gethnode2',
                linked_faucet_node='faucet')
    util_server.setDisplayName('UtilityServer')
    util_server.addHostName('utility' + DOMAIN)
    
    # Add Ethereum service to the emulator
    emu.addLayer(eth)
    
    # Bind all virtual servers (including faucet/utility) to physical hosts
    for _, servers in blockchain.getAllServerNames().items():
        for server in servers:
            emu.addBinding(Binding(server, filter=Filter(nodeName="host_*"),
                           action=Action.FIRST))
    
    # Add /etc/hosts layer
    emu.addLayer(EtcHosts())
    
    # Configure IP range for each AS
    base_layer = emu.getLayer('Base')
    for asn in asns:
        as_obj = base_layer.getAutonomousSystem(asn)
        net = as_obj.getNetwork('net0')
        net.setHostIpRange(hostStart=71, hostEnd=199, hostStep=1)
        
    # Generate the emulator output
    if dumpfile is not None:
        emu.dump(dumpfile)
    else:
        emu.render()
        docker = Docker(internetMapEnabled=True, etherViewEnabled=True, platform=platform)
        emu.compile(docker, './output', override=True)

if __name__ == "__main__":
    run()
