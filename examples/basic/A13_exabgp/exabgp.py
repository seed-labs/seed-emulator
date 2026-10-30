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
from seedemu.layers import Base, Routing
from seedemu.services import ExaBgpService
from seedemu.containerBundle import InternetMap


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build an ExaBGP service speaker example.")
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
    emu = Emulator()

    base = Base()
    routing = Routing()
    exabgp = ExaBgpService()

    base.createInternetExchange(100)

    as2 = base.createAutonomousSystem(2)
    as2.createNetwork("net0")
    as2.createRouter("router0").joinNetwork("net0").joinNetwork("ix100")

    as180 = base.createAutonomousSystem(180)
    as180.createHost("exabgp").joinNetwork("ix100", address="10.100.0.180")

    exabgp_speaker = exabgp.install("as180_exabgp").setLocalAsn(180)
    # Prefer IX-based peering: the service resolves the AS2 router on IX100 automatically.
    exabgp_speaker.addPeer(ix=100, peer_asn=2, router_relationship="customer")
    # Use router-based peering when multiple AS2 routers share IX100 and one must be selected explicitly.
    # exabgp_speaker.addPeerByRouter("router0", router_asn=2, router_relationship="customer")
    exabgp_speaker.addAnnouncement("198.51.100.0/24")
    emu.addBinding(Binding("as180_exabgp", filter=Filter(asn=180, nodeName="exabgp")))

    emu.addLayer(base)
    emu.addLayer(routing)
    emu.addLayer(exabgp)
    return emu


def main() -> int:
    args = parse_args()
    emu = build_emulator()

    if args.dumpfile:
        emu.dump(args.dumpfile)
        print("Saved A13 emulator to {}".format(args.dumpfile))
        return 0

    if args.render:
        emu.render()

    output_dir = Path(args.output).resolve()
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    docker = Docker(platform=resolve_platform(args.platform))
    # Add Internet visualization services: topology, geographic map, and traffic observation.
    # The second argument is a container name suffix that distinguishes bundle instances.
    internet_map_bundle = InternetMap(emu, ".map.seed")
    # Provide a host port pool (range excludes the stop value); InternetMap needs at least 3 ports.
    internet_map_bundle.setPorts(list(range(8081, 8089)))
    # Register the bundle with the Docker compiler to generate its containers during emu.compile().
    docker.addContainerBundle(internet_map_bundle)
    emu.compile(docker, str(output_dir), override=args.override)
    print("Generated A13 Docker output in {}".format(output_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())