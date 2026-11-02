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

from seedemu.core import Emulator, Binding, Filter
from seedemu.layers import Base, Ebgp, PeerRelationship
from seedemu.services import WebService
from seedemu.compiler import Docker, Platform
from examples.basic.A01_transit_as import transit_as
from seedemu.containerBundle import InternetMap


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the A05 component-reuse example.")
    parser.add_argument("legacy_platform", nargs="?", choices=["amd", "arm"])
    parser.add_argument("--platform", choices=["amd", "arm"])
    parser.add_argument("--output", default=str(SCRIPT_DIR / "output"))
    parser.add_argument("--dumpfile")
    parser.add_argument("--component-file", default=str(SCRIPT_DIR / "base_component.bin"))
    parser.add_argument("--override", dest="override", action="store_true", default=True)
    parser.add_argument("--no-override", dest="override", action="store_false")
    parser.add_argument("--skip-render", dest="render", action="store_false", default=True)
    args = parser.parse_args()
    args.platform = args.platform or args.legacy_platform or "amd"
    return args


def resolve_platform(name: str) -> Platform:
    return Platform.AMD64 if name == "amd" else Platform.ARM64


def build_emulator(component_file: str | Path = SCRIPT_DIR / "base_component.bin") -> Emulator:
    ###############################################################################
    # Load the pre-built component from example 01-transit-as
    component_path = Path(component_file).resolve()
    component_path.parent.mkdir(parents=True, exist_ok=True)
    transit_as.run(dumpfile=str(component_path))

    emu = Emulator()
    emu.load(str(component_path))

    ###############################################################################
    # Demonstrating how to get the layers of the component.
    # To make changes to any existing layer, we need to get the layer reference

    base: Base = emu.getLayer("Base")
    ebgp: Ebgp = emu.getLayer("Ebgp")

    web: WebService = WebService()

    ###############################################################################
    # Add a new host to AS-151, which is from the pre-built component

    as151 = base.getAutonomousSystem(151)
    as151.createHost("web-2").joinNetwork("net0")
    web.install("web151-2")
    emu.addBinding(Binding("web151-2", filter=Filter(nodeName="web-2", asn=151)))

    ###############################################################################
    # Add a new autonomous system (AS-154)
    # This requires making changes to the base and ebgp layers.

    as154 = base.createAutonomousSystem(154)
    as154.createNetwork("net0")

    as154.createRouter("router0").joinNetwork("net0").joinNetwork("ix100")
    as154.createRouter("router1").joinNetwork("net0").joinNetwork("ix101")

    as154.createHost("web").joinNetwork("net0")
    web.install("web154")
    emu.addBinding(Binding("web154", filter=Filter(nodeName="web", asn=154)))

    # Peer with AS-151 and AS-152
    ebgp.addPrivatePeering(100, 151, 154, abRelationship=PeerRelationship.Provider)
    ebgp.addPrivatePeering(101, 152, 154, abRelationship=PeerRelationship.Peer)

    ###############################################################################
    # Add a new internet exchange (IX-102) and peer AS-154 and AS-152 there.

    base.createInternetExchange(102)

    as152 = base.getAutonomousSystem(152)
    as152.createRouter("router1").joinNetwork("net0").joinNetwork("ix102")

    as154.createRouter("router2").joinNetwork("net0").joinNetwork("ix102")

    ebgp.addPrivatePeering(102, 152, 154, abRelationship=PeerRelationship.Peer)
    emu.addLayer(web)
    return emu


def run(
    dumpfile=None,
    output=None,
    platform=Platform.AMD64,
    override=True,
    render=True,
    component_file: str | Path = SCRIPT_DIR / "base_component.bin",
):
    emu = build_emulator(component_file)
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
        component_file=args.component_file,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())