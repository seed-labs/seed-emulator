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
from seedemu.layers import Base, Ebgp, Ibgp, Ospf, PeerRelationship, Routing
from seedemu.services import WebService
from seedemu.containerBundle import InternetMap


AKAMAI_ASN = 20940
AKAMAI_EXAMPLE_PREFIXES = ["23.192.228.0/24"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the A03a out-to-real-world example.")
    parser.add_argument("legacy_platform", nargs="?", choices=["amd", "arm"])
    parser.add_argument("--platform", choices=["amd", "arm"])
    parser.add_argument("--output", default=str(SCRIPT_DIR / "output"))
    parser.add_argument("--dumpfile")
    parser.add_argument(
        "--live-prefixes",
        action="store_true",
        help="Fetch live prefixes for AS20940 instead of using deterministic example.com-related prefixes.",
    )
    parser.add_argument("--override", dest="override", action="store_true", default=True)
    parser.add_argument("--no-override", dest="override", action="store_false")
    parser.add_argument("--skip-render", dest="render", action="store_false", default=True)
    args = parser.parse_args()
    args.platform = args.platform or args.legacy_platform or "amd"
    return args


def resolve_platform(name: str) -> Platform:
    return Platform.AMD64 if name == "amd" else Platform.ARM64


def build_emulator(use_live_prefixes=False) -> Emulator:
    emu = Emulator()
    base = Base()
    ebgp = Ebgp()
    web = WebService()

    base.createInternetExchange(100)
    base.createInternetExchange(101)

    as2 = base.createAutonomousSystem(2)
    as2.createNetwork("net0")
    as2.createNetwork("net1")
    as2.createNetwork("net2")
    as2.createRouter("r1").joinNetwork("ix100").joinNetwork("net0")
    as2.createRouter("r2").joinNetwork("net0").joinNetwork("net1")
    as2.createRouter("r3").joinNetwork("net1").joinNetwork("net2")
    as2.createRouter("r4").joinNetwork("net2").joinNetwork("ix101")

    as151 = base.createAutonomousSystem(151)
    as151.createNetwork("net0")
    as151.createRouter("router0").joinNetwork("net0").joinNetwork("ix100")
    as151.createHost("web").joinNetwork("net0")
    web.install("web151")
    emu.addBinding(Binding("web151", filter=Filter(asn=151, nodeName="web")))

    as152 = base.createAutonomousSystem(152)
    as152.createNetwork("net0")
    as152.createRouter("router0").joinNetwork("net0").joinNetwork("ix101")
    as152.createHost("web").joinNetwork("net0")
    web.install("web152")
    emu.addBinding(Binding("web152", filter=Filter(asn=152, nodeName="web")))

    as20940 = base.createAutonomousSystem(AKAMAI_ASN)
    prefixes = None if use_live_prefixes else AKAMAI_EXAMPLE_PREFIXES
    as20940.createRealWorldRouter("rw", prefixes=prefixes).joinNetwork("ix101", "10.101.0.209")

    ebgp.addPrivatePeering(100, 2, 151, abRelationship=PeerRelationship.Provider)
    ebgp.addPrivatePeering(101, 2, 152, abRelationship=PeerRelationship.Provider)
    ebgp.addPrivatePeering(101, 2, AKAMAI_ASN, abRelationship=PeerRelationship.Unfiltered)

    emu.addLayer(base)
    emu.addLayer(Routing())
    emu.addLayer(ebgp)
    emu.addLayer(Ibgp())
    emu.addLayer(Ospf())
    emu.addLayer(web)
    return emu


def run(
    dumpfile=None,
    output=None,
    platform=Platform.AMD64,
    override=True,
    render=True,
    use_live_prefixes=False,
):
    emu = build_emulator(use_live_prefixes=use_live_prefixes)
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
        use_live_prefixes=args.live_prefixes,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())