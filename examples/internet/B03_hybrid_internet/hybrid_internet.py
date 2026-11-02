#!/usr/bin/env python3
# encoding: utf-8
#
# Purpose: build the B03 hybrid Internet example. Inputs are standard
# TestRunner CLI arguments. Outputs are Docker compiler files under --output.

from __future__ import annotations

import argparse
from pathlib import Path
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from examples.internet.B00_mini_internet import mini_internet
from seedemu.compiler import Docker, Platform
from seedemu.core import Emulator
from seedemu.layers import Base, Ebgp, PeerRelationship
from seedemu.raps import OpenVpnRemoteAccessProvider
from seedemu.containerBundle import InternetMap


SYRACUSE_ASN = 11872
SYRACUSE_EXAMPLE_PREFIXES = ["128.230.0.0/16"]
HYBRID_ASN = 99999
HYBRID_DEFAULT_PREFIXES = ["0.0.0.0/1", "128.0.0.0/1"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the B03 hybrid Internet example.")
    parser.add_argument("legacy_platform", nargs="?", choices=["amd", "arm"])
    parser.add_argument("--platform", choices=["amd", "arm"])
    parser.add_argument("--output", default=str(SCRIPT_DIR / "output"))
    parser.add_argument("--dumpfile")
    parser.add_argument("--hosts-per-as", type=int, default=2)
    parser.add_argument(
        "--live-prefixes",
        action="store_true",
        help="Fetch live prefixes for AS11872 instead of using deterministic example prefixes.",
    )
    parser.add_argument("--override", dest="override", action="store_true", default=True)
    parser.add_argument("--no-override", dest="override", action="store_false")
    parser.add_argument("--skip-render", dest="render", action="store_false", default=True)
    args = parser.parse_args()
    args.platform = args.platform or args.legacy_platform or "amd"
    return args


def resolve_platform(name: str) -> Platform:
    return Platform.AMD64 if name == "amd" else Platform.ARM64


def add_remote_access(base: Base) -> None:
    ovpn = OpenVpnRemoteAccessProvider()
    base.getAutonomousSystem(152).getNetwork("net0").enableRemoteAccess(ovpn)


def add_real_world_as(base: Base, ebgp: Ebgp, use_live_prefixes: bool = False) -> None:
    prefixes = None if use_live_prefixes else SYRACUSE_EXAMPLE_PREFIXES
    as11872 = base.createAutonomousSystem(SYRACUSE_ASN)
    as11872.createRealWorldRouter("rw-11872-syr", prefixes=prefixes).joinNetwork("ix102", "10.102.0.118")
    ebgp.addPrivatePeerings(102, [11], [SYRACUSE_ASN], PeerRelationship.Provider)


def add_default_real_world_gateway(base: Base, ebgp: Ebgp) -> None:
    as99999 = base.createAutonomousSystem(HYBRID_ASN)
    as99999.createRealWorldRouter(
        "rw-real-world",
        prefixes=HYBRID_DEFAULT_PREFIXES,
    ).joinNetwork("ix100", "10.100.0.99")
    ebgp.addPrivatePeerings(100, [3], [HYBRID_ASN], PeerRelationship.Provider)


def build_emulator(hosts_per_as: int = 2, use_live_prefixes: bool = False) -> Emulator:
    emu = mini_internet.build_emulator(hosts_per_as=hosts_per_as)

    base: Base = emu.getLayer("Base")
    ebgp: Ebgp = emu.getLayer("Ebgp")

    add_remote_access(base)
    add_real_world_as(base, ebgp, use_live_prefixes=use_live_prefixes)
    add_default_real_world_gateway(base, ebgp)
    return emu


def run(
    dumpfile=None,
    hosts_per_as: int = 2,
    output=None,
    platform=Platform.AMD64,
    override: bool = True,
    render: bool = True,
    use_live_prefixes: bool = False,
):
    emu = build_emulator(hosts_per_as=hosts_per_as, use_live_prefixes=use_live_prefixes)
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
    emu.compile(docker, str(output_dir), override=override)


def main() -> int:
    args = parse_args()
    run(
        dumpfile=args.dumpfile,
        hosts_per_as=args.hosts_per_as,
        output=str(Path(args.output).resolve()),
        platform=resolve_platform(args.platform),
        override=args.override,
        render=args.render,
        use_live_prefixes=args.live_prefixes,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())