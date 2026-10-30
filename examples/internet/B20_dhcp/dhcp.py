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

from seedemu.compiler import Docker, Platform
from seedemu.core import Binding, Emulator, Filter
from seedemu.layers import Base
from seedemu.services import DHCPService
from examples.internet.B00_mini_internet import mini_internet
from seedemu.containerBundle import InternetMap


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the B20 DHCP example.")
    parser.add_argument("legacy_platform", nargs="?", choices=["amd", "arm"])
    parser.add_argument("--platform", choices=["amd", "arm"])
    parser.add_argument("--output", default=str(SCRIPT_DIR / "output"))
    parser.add_argument("--dumpfile")
    parser.add_argument("--override", dest="override", action="store_true", default=True)
    parser.add_argument("--no-override", dest="override", action="store_false")
    parser.add_argument("--skip-render", dest="render", action="store_false", default=True)
    args = parser.parse_args()
    args.platform = args.platform or args.legacy_platform or "amd"
    return args


def resolve_platform(name: str) -> Platform:
    return Platform.AMD64 if name == "amd" else Platform.ARM64


def build_emulator() -> Emulator:
    base_component = SCRIPT_DIR / "base_internet.bin"
    mini_internet.run(dumpfile=str(base_component))

    emu = Emulator()
    emu.load(str(base_component))

    base: Base = emu.getLayer("Base")

    # Create DHCP servers as virtual nodes.
    dhcp = DHCPService()

    # Default DHCP range: x.x.x.101 - x.x.x.120.
    # Custom AS151 DHCP range: x.x.x.125 - x.x.x.140.
    dhcp.install("dhcp-01").setIpRange(125, 140)
    dhcp.install("dhcp-02")

    emu.getVirtualNode("dhcp-01").setDisplayName("DHCP Server 1")
    emu.getVirtualNode("dhcp-02").setDisplayName("DHCP Server 2")

    # Create hosts in AS151 and AS161 to run the DHCP servers.
    as151 = base.getAutonomousSystem(151)
    as151.createHost("dhcp-server-01").joinNetwork("net0")

    as161 = base.getAutonomousSystem(161)
    as161.createHost("dhcp-server-02").joinNetwork("net0")

    emu.addBinding(Binding("dhcp-01", filter=Filter(asn=151, nodeName="dhcp-server-01")))
    emu.addBinding(Binding("dhcp-02", filter=Filter(asn=161, nodeName="dhcp-server-02")))

    # Create DHCP clients. They use DHCP instead of static addresses.
    as151.createHost("dhcp-client-01").joinNetwork("net0", address="dhcp")
    as151.createHost("dhcp-client-02").joinNetwork("net0", address="dhcp")

    as161.createHost("dhcp-client-03").joinNetwork("net0", address="dhcp")
    as161.createHost("dhcp-client-04").joinNetwork("net0", address="dhcp")

    emu.addLayer(dhcp)
    return emu


def run(
    dumpfile=None,
    output=None,
    platform=Platform.AMD64,
    override=True,
    render=True,
):
    emu = build_emulator()
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
        output=str(Path(args.output).resolve()),
        platform=resolve_platform(args.platform),
        override=args.override,
        render=args.render,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())