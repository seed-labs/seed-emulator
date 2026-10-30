#!/usr/bin/env python3
# encoding: utf-8

from __future__ import annotations

import argparse
from pathlib import Path

from seedemu.core import Emulator
from seedemu.mergers import DEFAULT_MERGERS
from seedemu.layers import Base, Routing, Ebgp
from seedemu.compiler import Docker, Platform
from seedemu.containerBundle import InternetMap


SCRIPT_DIR = Path(__file__).resolve().parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the A06 merge-emulation example.")
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
    ###############################################################################
    # Create Emulation A
    # We can also load this emulation for a pre-built component

    emu_a = Emulator()
    base_a = Base()
    ebgp_a = Ebgp()
    routing_a = Routing()

    base_a.createInternetExchange(100)

    as150 = base_a.createAutonomousSystem(150)
    as150.createNetwork("net0")
    as150.createHost("host0").joinNetwork("net0")
    as150.createRouter("router0").joinNetwork("net0").joinNetwork("ix100")

    ebgp_a.addRsPeer(100, 150)

    emu_a.addLayer(base_a)
    emu_a.addLayer(routing_a)
    emu_a.addLayer(ebgp_a)

    ###############################################################################
    # Create Emulation B
    # We can also load this emulation for a pre-built component

    base_b = Base()
    ebgp_b = Ebgp()
    routing_b = Routing()

    as151 = base_b.createAutonomousSystem(151)
    as151.createNetwork("net0")
    as151.createHost("host0").joinNetwork("net0")
    as151.createRouter("router0").joinNetwork("net0").joinNetwork("ix100")

    ebgp_b.addRsPeer(100, 151)

    emu_b = Emulator()
    emu_b.addLayer(base_b)
    emu_b.addLayer(routing_b)
    emu_b.addLayer(ebgp_b)

    ###############################################################################
    # Merge these two emulations

    return emu_a.merge(emu_b, DEFAULT_MERGERS)


def run(
    dumpfile=None,
    output=None,
    platform=Platform.AMD64,
    override=True,
    render=True,
):
    emu_merged = build_emulator()
    if dumpfile is not None:
        emu_merged.dump(dumpfile)
        return

    if render:
        emu_merged.render()

    output_dir = Path(output or SCRIPT_DIR / "output").resolve()
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    docker = Docker(platform=platform)
    # Add Internet visualization services: topology, geographic map, and traffic observation.
    # The second argument is a container name suffix that distinguishes bundle instances.
    internet_map_bundle = InternetMap(emu_merged, ".map.seed")
    # Provide a host port pool (range excludes the stop value); InternetMap needs at least 3 ports.
    internet_map_bundle.setPorts(list(range(8081, 8089)))
    # Register the bundle with the Docker compiler to generate its containers during emu.compile().
    docker.addContainerBundle(internet_map_bundle)
    emu_merged.compile(docker, str(output_dir), override=override)


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

