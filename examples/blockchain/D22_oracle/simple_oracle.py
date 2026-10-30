#!/usr/bin/env python3
# encoding: utf-8

from __future__ import annotations

import argparse
import os
from contextlib import contextmanager
from pathlib import Path
import sys
import tempfile


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from seedemu import *
from examples.blockchain.D00_ethereum_poa import ethereum_poa
from examples.blockchain.D01_ethereum_pos import ethereum_pos
from seedemu.services.EthereumService import *


@contextmanager
def pushd(directory: Path):
    previous = Path.cwd()
    os.chdir(directory)
    try:
        yield
    finally:
        os.chdir(previous)


def get_file_content(filename: str) -> str:
    return (SCRIPT_DIR / filename).read_text(encoding="utf-8")


def installSoftware(node: Node):
    software_list = ["curl", "python3", "python3-pip", "build-essential", "python3-dev"]
    for software in software_list:
        node.addSoftware(software)

    node.addBuildCommand(
        "pip3 install --break-system-packages web3==6.20.4 requests || pip3 install web3==6.20.4 requests"
    )

    node.setFile("/oracle/EthereumHelper.py", get_file_content("code/EthereumHelper.py"))
    node.setFile("/oracle/FaucetHelper.py", get_file_content("code/FaucetHelper.py"))
    node.setFile("/oracle/UtilityServerHelper.py", get_file_content("code/UtilityServerHelper.py"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the D22 oracle example.")
    parser.add_argument("legacy_args", nargs="*", help="legacy form: [poa|pos] [amd|arm]")
    parser.add_argument("--consensus", default=str("pos"), choices=["poa", "pos"])
    parser.add_argument("--platform", choices=["amd", "arm"])
    parser.add_argument("--output", default=str(SCRIPT_DIR / "output"))
    parser.add_argument("--dumpfile")
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

    legacy_consensus = None
    legacy_platform = None
    for item in args.legacy_args:
        value = item.lower()
        if value in ("poa", "pos") and legacy_consensus is None:
            legacy_consensus = value
        elif value in ("amd", "arm") and legacy_platform is None:
            legacy_platform = value
        else:
            parser.error("legacy arguments must be: [poa|pos] [amd|arm]")

    args.consensus = args.consensus or legacy_consensus or "poa"
    args.platform = args.platform or legacy_platform or "amd"
    return args


def resolve_platform(name: str) -> Platform:
    return Platform.AMD64 if name == "amd" else Platform.ARM64


def load_base_blockchain(consensus: str) -> Emulator:
    emu = Emulator()
    with tempfile.TemporaryDirectory(prefix="seedemu-d22-") as tempdir:
        temp_path = Path(tempdir)
        dump_path = temp_path / f"blockchain_{consensus}.bin"
        with pushd(temp_path):
            if consensus == "pos":
                ethereum_pos.run(dumpfile=str(dump_path))
            else:
                ethereum_poa.run(
                    dumpfile=str(dump_path),
                    hosts_per_as=1,
                    total_eth_nodes=10,
                    total_accounts_per_node=1,
                )
        emu.load(str(dump_path))
    return emu


def build_emulator(consensus: str = "poa") -> Emulator:
    if consensus == "pos":
        eth_node1 = "gethnode1.net"
    else:
        eth_node1 = "eth3.net"

    faucet = "faucet.net"
    utility = "utility.net"
    faucet_port = 80
    utility_port = 5000
    eth_port = 8545
    chain_id = 1337
    oracle_name = "oracle-contract"

    emu = load_base_blockchain(consensus)

    base_layer = emu.getLayer("Base")
    as_ = base_layer.getAutonomousSystem(164)
    oracle_user = as_.createHost("oracle_user").joinNetwork("net0")
    oracle_node = as_.createHost("oracle_node").joinNetwork("net0")

    installSoftware(oracle_user)
    installSoftware(oracle_node)

    oracle_user.setFile("/contract/Oracle.abi", get_file_content("contract/Oracle.abi"))
    oracle_user.setFile(
        "/oracle/user_create_account.py",
        get_file_content("code/user_create_account.py").format(
            chain_id=chain_id,
            eth_node=eth_node1,
            eth_port=eth_port,
            faucet_server=faucet,
            faucet_port=faucet_port,
        ),
    )
    oracle_user.setFile(
        "/oracle/user_get_price.py",
        get_file_content("code/user_get_price.py").format(
            chain_id=chain_id,
            faucet_server=faucet,
            faucet_port=faucet_port,
            utility_server=utility,
            utility_port=utility_port,
            eth_node=eth_node1,
            eth_port=eth_port,
            oracle_contract_name=oracle_name,
        ),
    )
    oracle_user.appendStartCommand("python3 /oracle/user_create_account.py &")

    oracle_node.setFile("/contract/Oracle.abi", get_file_content("contract/Oracle.abi"))
    oracle_node.setFile("/contract/Oracle.bin", get_file_content("contract/Oracle.bin"))
    oracle_node.setFile(
        "/oracle/deploy_oracle_contract.py",
        get_file_content("code/deploy_oracle_contract.py").format(
            chain_id=chain_id,
            faucet_server=faucet,
            faucet_port=faucet_port,
            utility_server=utility,
            utility_port=utility_port,
            eth_node=eth_node1,
            eth_port=eth_port,
            oracle_contract_name=oracle_name,
        ),
    )
    oracle_node.setFile(
        "/oracle/oracle_node_set_price.py",
        get_file_content("code/oracle_node_set_price.py").format(
            chain_id=chain_id,
            faucet_server=faucet,
            faucet_port=faucet_port,
            utility_server=utility,
            utility_port=utility_port,
            eth_node=eth_node1,
            eth_port=eth_port,
        ),
    )
    oracle_node.setFile("/oracle/oracle_node_start.sh", get_file_content("code/oracle_node_start.sh"))
    oracle_node.appendStartCommand("bash /oracle/oracle_node_start.sh &")

    return emu


def run(
    *,
    consensus: str = "poa",
    dumpfile=None,
    output=None,
    platform=Platform.AMD64,
    override: bool = True,
    render: bool = True,
    ether_view_enabled: bool = True,
):
    emu = build_emulator(consensus=consensus)
    if dumpfile is not None:
        emu.dump(dumpfile)
        return

    if render:
        emu.render()

    output_dir = Path(output or SCRIPT_DIR / "output").resolve()
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    docker = Docker(platform=platform)
    
    # Add Internet visualization services: topology, geographic map, and traffic observation.
    # The second argument is a container name suffix that distinguishes bundle instances.
    internet_map_bundle = InternetMap(emu, ".map.seed")
    # Provide a host port pool (range excludes the stop value); InternetMap needs at least 3 ports.
    internet_map_bundle.setPorts(list(range(8081, 8089)))
    # Register the bundle with the Docker compiler to generate its containers during emu.compile().
    docker.addContainerBundle(internet_map_bundle)

    # Add an Ethereum explorer with an indexing backend, a Web frontend, and supporting services.
    eth_explorer_bundle = EthExplorer(emu, ".eth.explorer.seed")
    # The explorer Web frontend needs at least 1 host port; ports are taken from the list's end.
    eth_explorer_bundle.setPorts(list(range(8090, 8099)))
    # Include the explorer bundle in this Docker compilation.
    docker.addContainerBundle(eth_explorer_bundle)
        
    emu.compile(docker, str(output_dir), override=override)


def main() -> int:
    args = parse_args()
    run(
        consensus=args.consensus,
        dumpfile=args.dumpfile,
        output=str(Path(args.output).resolve()),
        platform=resolve_platform(args.platform),
        override=args.override,
        render=args.render,
        ether_view_enabled=args.ether_view_enabled,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
