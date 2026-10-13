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


@contextmanager
def pushd(directory: Path):
    previous = Path.cwd()
    os.chdir(directory)
    try:
        yield
    finally:
        os.chdir(previous)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the D20 Faucet example.")
    parser.add_argument(
        "legacy_args",
        nargs="*",
        help="legacy form: [poa|pos] [amd|arm]",
    )
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
    with tempfile.TemporaryDirectory(prefix="seedemu-d20-") as tempdir:
        temp_path = Path(tempdir)
        dump_path = temp_path / f"blockchain_{consensus}.bin"
        with pushd(temp_path):
            if consensus == "pos":
                ethereum_pos.run(dumpfile=str(dump_path))
            else:
                ethereum_poa.run(dumpfile=str(dump_path), total_accounts_per_node=1)
        emu.load(str(dump_path))
    return emu


def build_emulator(consensus: str = "poa") -> Emulator:
    emu = load_base_blockchain(consensus)

    eth = emu.getLayer("EthereumService")
    blockchain = eth.getBlockchainByName(eth.getBlockchainNames()[0])
    faucet_name = blockchain.getFaucetServerNames()[0]
    faucet = blockchain.getFaucetServerByName(faucet_name)

    # Funding accounts during build time. The actual funding is carried out
    # after the emulation starts.
    faucet.fund("0x72943017a1fa5f255fc0f06625aec22319fcd5b3", 2)
    faucet.fund("0x5449ba5c5f185e9694146d60cfe72681e2158499", 5)

    # Funding accounts during run time, i.e., after the emulation starts.
    faucet_user_service = FaucetUserService()
    faucet_user_service.install("faucetUser").setDisplayName("FaucetUser")
    faucet_info = blockchain.getFaucetServerInfo()
    faucet_user_service.setFaucetServerInfo(faucet_info[0]["name"], faucet_info[0]["port"])
    emu.addBinding(Binding("faucetUser"))
    emu.addLayer(faucet_user_service)

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
    docker = Docker(internetMapEnabled=False, platform=platform)
            
    internet_map_bundle = InternetMap(emu, ".map.seed")
    internet_map_bundle.setDefaultNetwork("internet_map_network")
    internet_map_bundle.setPorts(list(range(8080, 8089)))
    docker.addContainerBundle(internet_map_bundle)

    eth_explorer_bundle = EthExplorer(emu, ".eth.explorer.seed")
    eth_explorer_bundle.setDefaultNetwork("eth_explorer_network")
    eth_explorer_bundle.setPorts(list(range(8090, 8099)))
    eth = emu.getLayer("EthereumService")
    blockchain = eth.getBlockchainByName(eth.getBlockchainNames()[0])
    eth_explorer_bundle.setBeaconHost(blockchain.getBeaconBootNodeIP()[0])
    eth_explorer_bundle.setGethHost(blockchain.getGethBootNodeIP()[0])
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
