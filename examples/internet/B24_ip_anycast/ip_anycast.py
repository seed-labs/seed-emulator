#!/usr/bin/env python3
# encoding: utf-8
#
# Purpose: build the B24 IP anycast example. Inputs are standard TestRunner
# CLI arguments. Outputs are Docker compiler files under --output.

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
from seedemu.core import Binding, Emulator, Filter
from seedemu.layers import Base, Ebgp, PeerRelationship
from seedemu.services import WebService
from seedemu.containerBundle import InternetMap


ANYCAST_ADDRESS = "10.180.0.100"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the B24 IP anycast example.")
    parser.add_argument("legacy_platform", nargs="?", choices=["amd", "arm"])
    parser.add_argument("--platform", choices=["amd", "arm"])
    parser.add_argument("--output", default=str(SCRIPT_DIR / "output"))
    parser.add_argument("--dumpfile")
    parser.add_argument("--hosts-per-as", type=int, default=2)
    parser.add_argument("--override", dest="override", action="store_true", default=True)
    parser.add_argument("--no-override", dest="override", action="store_false")
    parser.add_argument("--skip-render", dest="render", action="store_false", default=True)
    args = parser.parse_args()
    args.platform = args.platform or args.legacy_platform or "amd"
    return args


def resolve_platform(name: str) -> Platform:
    return Platform.AMD64 if name == "amd" else Platform.ARM64


def build_emulator(hosts_per_as: int = 2) -> Emulator:
    emu = Emulator()

    base_component = SCRIPT_DIR / "base_internet.bin"
    mini_internet.run(dumpfile=str(base_component), hosts_per_as=hosts_per_as)
    emu.load(str(base_component))

    base: Base = emu.getLayer("Base")
    ebgp: Ebgp = emu.getLayer("Ebgp")
    web = WebService()

    # AS180 has two disconnected sites that both announce the same /24.
    as180 = base.createAutonomousSystem(180)
    as180.createNetwork("net0", "10.180.0.0/24")
    as180.createNetwork("net1", "10.180.0.0/24")

    as180.createHost("host-0").joinNetwork("net0", address=ANYCAST_ADDRESS)
    as180.createHost("host-1").joinNetwork("net1", address=ANYCAST_ADDRESS)

    as180.createRouter("router0").joinNetwork("net0").joinNetwork("ix100")
    ebgp.addPrivatePeerings(100, [3, 4], [180], PeerRelationship.Provider)

    as180.createRouter("router1").joinNetwork("net1").joinNetwork("ix105")
    ebgp.addPrivatePeerings(105, [2, 3], [180], PeerRelationship.Provider)

    web.install("anycast-west").setIndexContent("B24 anycast site: ix100-west\n")
    web.install("anycast-east").setIndexContent("B24 anycast site: ix105-east\n")
    emu.addBinding(Binding("anycast-west", filter=Filter(asn=180, nodeName="host-0")))
    emu.addBinding(Binding("anycast-east", filter=Filter(asn=180, nodeName="host-1")))
    emu.addLayer(web)

    return emu


def run(
    dumpfile=None,
    hosts_per_as: int = 2,
    output=None,
    platform=Platform.AMD64,
    override: bool = True,
    render: bool = True,
):
    emu = build_emulator(hosts_per_as=hosts_per_as)
    if dumpfile is not None:
        emu.dump(dumpfile)
        return

    if render:
        emu.render()

    # selfManagedNetwork is required because AS180 intentionally has two Docker
    # networks with the same IP prefix.
    docker = Docker(selfManagedNetwork=True, platform=platform)
    # Add Internet visualization services: topology, geographic map, and traffic observation.
    # The second argument is a container name suffix that distinguishes bundle instances.
    internet_map_bundle = InternetMap(emu, ".map.seed")
    # Provide a host port pool (range excludes the stop value); InternetMap needs at least 3 ports.
    internet_map_bundle.setPorts(list(range(8081, 8089)))
    # Register the bundle with the Docker compiler to generate its containers during emu.compile().
    docker.addContainerBundle(internet_map_bundle)
    emu.compile(docker, output or str(SCRIPT_DIR / "output"), override=override)


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output).resolve()
    output_dir.parent.mkdir(parents=True, exist_ok=True)

    run(
        dumpfile=args.dumpfile,
        hosts_per_as=args.hosts_per_as,
        output=str(output_dir),
        platform=resolve_platform(args.platform),
        override=args.override,
        render=args.render,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
