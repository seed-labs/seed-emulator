#!/usr/bin/env python3
# encoding: utf-8

from seedemu import *
import sys, os
import math
from eth_account import Account

DOMAIN = ".net"

def run(dumpfile = None, total_beacon_nodes=3, vc_per_beacon=2):
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
    geth_node_number = total_beacon_nodes
    beacon_node_number = total_beacon_nodes
    vc_node_number = vc_per_beacon * beacon_node_number
    beaconsetup_node_number = 1
    total_number_of_nodes = geth_node_number + beacon_node_number + vc_node_number + beaconsetup_node_number
    total_stub_as = 10
    hosts_per_stub_as = math.ceil(total_number_of_nodes / total_stub_as)
    emu = Makers.makeEmulatorBaseWith10StubASAndHosts(hosts_per_stub_as=hosts_per_stub_as)
    print(f"Number of eth nodes per stub AS: {hosts_per_stub_as}")
    eth = EthereumService()
    blockchain = eth.createBlockchain(chainName="pos", consensus=ConsensusMechanism.POS)
    accounts_total  = 1000
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
    beaconsetupServer: PoSBeaconSetupServer = blockchain.createBeaconSetupNode(f"BeaconSetupNode")
    emu.getVirtualNode(f'BeaconSetupNode').setDisplayName('Ethereum-POS-BeaconSetup')
    for i in range(geth_node_number):
        gethServer: PoSGethServer = blockchain.createGethNode(f"gethnode{i}")
        gethServer.enableGethHttp()
        gethServer.appendClassName(f'Ethereum-POS-Geth-{i+1}')
        geth_nodes.append(gethServer)
        emu.getVirtualNode(f'gethnode{i}').setDisplayName(f'Ethereum-POS-Geth-{i+1}')
    for i in range(beacon_node_number):
        beaconServer: PoSBeaconServer = blockchain.createBeaconNode(f"beaconnode{i}")
        beaconServer.appendClassName(f'Ethereum-POS-Beacon-{i+1}')
        beaconServer.connectToGethNode(f"gethnode{(i+1)%len(geth_nodes)}")
        beacon_nodes.append(beaconServer)
        emu.getVirtualNode(f'beaconnode{i}').setDisplayName(f'Ethereum-POS-Beacon-{i+1}')
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

    faucet:FaucetServer = blockchain.createFaucetServer(
                vnode='faucet',
                port=80,
                linked_eth_node='gethnode1',
                balance=10000,
                max_fund_amount=10)
    faucet.setDisplayName('Faucet')
    faucet.addHostName('faucet' + DOMAIN)
    util_server:EthUtilityServer = blockchain.createEthUtilityServer(
                vnode='utility',
                port=5000,
                linked_eth_node='gethnode2',
                linked_faucet_node='faucet')
    util_server.setDisplayName('UtilityServer')
    util_server.addHostName('utility' + DOMAIN)
    
    
    
    emu.addLayer(eth)
    # Bind all virtual servers (including faucet/utility) to physical hosts
    for _, servers in blockchain.getAllServerNames().items():
        for server in servers:
            emu.addBinding(Binding(server, filter=Filter(nodeName="host_*"),
                           action=Action.FIRST))
    emu.addLayer(EtcHosts())
    base_layer = emu.getLayer('Base')
    for asn in asns:
        as_obj = base_layer.getAutonomousSystem(asn)
        net = as_obj.getNetwork('net0')
        net.setHostIpRange(hostStart=71, hostEnd=199, hostStep=1)
    if dumpfile is not None:
        emu.dump(dumpfile)
    else:
        emu.render()
        docker = Docker(internetMapEnabled=True, etherViewEnabled=True, platform=platform)
        emu.compile(docker, './output', override=True)

if __name__ == "__main__":
    run()
