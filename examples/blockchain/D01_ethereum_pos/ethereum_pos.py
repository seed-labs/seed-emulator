#!/usr/bin/env python3
# encoding: utf-8

from __future__ import annotations

import argparse
from pathlib import Path
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from seedemu import *


DOMAIN = ".net"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the D01 Ethereum PoS example.")
    parser.add_argument("legacy_platform", nargs="?", choices=["amd", "arm"])
    parser.add_argument("--platform", choices=["amd", "arm"])
    parser.add_argument("--output", default=str(SCRIPT_DIR / "output"))
    parser.add_argument("--dumpfile")
    parser.add_argument(
        "--beacon-nodes",
        type=int,
        default=3,
        help="number of geth/beacon node pairs",
    )
    parser.add_argument(
        "--validators-per-beacon",
        type=int,
        default=3,
        help="validator clients per beacon node",
    )
    parser.add_argument(
        "--ether-view",
        dest="ether_view_enabled",
        action="store_true",
        default=True,
        help="enable Eth Explorer output in generated Docker files (default)",
    )
    parser.add_argument(
        "--no-ether-view",
        dest="ether_view_enabled",
        action="store_false",
        help="disable Eth Explorer output; useful for CI builds",
    )
    parser.add_argument("--override", dest="override", action="store_true", default=True)
    parser.add_argument("--no-override", dest="override", action="store_false")
    parser.add_argument("--skip-render", dest="render", action="store_false", default=True)
    args = parser.parse_args()
    args.platform = args.platform or args.legacy_platform or "amd"
    if args.beacon_nodes < 1:
        parser.error("--beacon-nodes must be >= 1")
    if args.validators_per_beacon < 1:
        parser.error("--validators-per-beacon must be >= 1")
    return args


def resolve_platform(name: str) -> Platform:
    return Platform.AMD64 if name == "amd" else Platform.ARM64


def build_emulator(total_beacon_nodes: int = 3, vc_per_beacon: int = 3) -> Emulator:
    ###############################################################################
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
    # Generate a list of wallet-compatible local accounts and prefund them.
    accounts_total  = 10
    pre_funded_amount = 1000000
    mnemonic = "gentle always fun glass foster produce north tail security list example gain"
    blockchain.addLocalAccountsFromMnemonic(
        mnemonic=mnemonic,
        total=accounts_total,
        balance=pre_funded_amount,
    )
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

    faucet_geth_node = "gethnode{}".format(1 if geth_node_number > 1 else 0)
    utility_geth_node = "gethnode{}".format(2 if geth_node_number > 2 else geth_node_number - 1)

    # Create the Faucet server
    faucet:FaucetServer = blockchain.createFaucetServer(
                vnode='faucet',
                port=80,
                linked_eth_node=faucet_geth_node,
                balance=10000,
                max_fund_amount=10)
    faucet.setDisplayName('Faucet')
    faucet.addHostName('faucet' + DOMAIN)
    # Create the Utility server
    util_server:EthUtilityServer = blockchain.createEthUtilityServer(
                vnode='utility',
                port=5000,
                linked_eth_node=utility_geth_node,
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
    
    return emu


def run(
    dumpfile=None,
    total_beacon_nodes: int = 3,
    vc_per_beacon: int = 3,
    output=None,
    platform=Platform.AMD64,
    override: bool = True,
    render: bool = True,
    ether_view_enabled: bool = True,
):
    emu = build_emulator(total_beacon_nodes=total_beacon_nodes, vc_per_beacon=vc_per_beacon)
    if dumpfile is not None:
        emu.dump(dumpfile)
        return

    if render:
        emu.render()
    
    output_dir = Path(output or SCRIPT_DIR / "output").resolve()
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    docker = Docker(internetMapEnabled=False, platform=platform)

    internet_map_bundle = InternetMap(emu, ".map.seed")
    internet_map_bundle.setDefaultNetwork("internet_map_network")
    internet_map_bundle.setPorts(list(range(8080, 8089)))
    docker.addContainerBundle(internet_map_bundle)

    eth_explorer_bundle = EthExplorer(emu, ".eth.explorer.seed")
    eth_explorer_bundle.setDefaultNetwork("eth_explorer_network")
    eth_explorer_bundle.setPorts(list(range(8090, 8099)))
    blockchain = emu.getLayer("EthereumService").getBlockchainByName('pos')
    eth_explorer_bundle.setBeaconHost(blockchain.getBeaconBootNodeIP()[0])
    eth_explorer_bundle.setGethHost(blockchain.getGethBootNodeIP()[0])
    docker.addContainerBundle(eth_explorer_bundle)

    emu.compile(docker, str(output_dir), override=override)


def main() -> int:
    args = parse_args()
    run(
        dumpfile=args.dumpfile,
        total_beacon_nodes=args.beacon_nodes,
        vc_per_beacon=args.validators_per_beacon,
        output=str(Path(args.output).resolve()),
        platform=resolve_platform(args.platform),
        override=args.override,
        render=args.render,
        ether_view_enabled=args.ether_view_enabled,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
