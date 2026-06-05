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
from seedemu.layers import Base, Ebgp, Mpls, PeerRelationship, Routing
from seedemu.services import WebService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the A02 transit AS MPLS example.")
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
    ebgp = Ebgp()
    mpls = Mpls()
    web = WebService()

    base.createInternetExchange(100)
    base.createInternetExchange(101)

    ###############################################################################
    # Create and set up the transit AS (AS2)

    as2 = base.createAutonomousSystem(2)

    # Create 3 internal networks
    as2.createNetwork("net0")
    as2.createNetwork("net1")
    as2.createNetwork("net2")

    # Create four routers and link them in a linear structure:
    # ix100 <--> r1 <--> r2 <--> r3 <--> r4 <--> ix101
    # r1 and r4 are BGP routers because they are connected to Internet exchanges.
    as2.createRouter("r1").joinNetwork("net0").joinNetwork("ix100")
    as2.createRouter("r2").joinNetwork("net0").joinNetwork("net1")
    as2.createRouter("r3").joinNetwork("net1").joinNetwork("net2")
    as2.createRouter("r4").joinNetwork("net2").joinNetwork("ix101")

    # Enable MPLS in the transit AS.
    mpls.enableOn(2)

    ###############################################################################
    # Create and set up the stub AS (AS151)

    as151 = base.createAutonomousSystem(151)
    as151.createNetwork("net0")
    as151.createRouter("router0").joinNetwork("net0").joinNetwork("ix100")
    as151.createHost("web").joinNetwork("net0")
    web.install("web151")
    emu.addBinding(Binding("web151", filter=Filter(nodeName="web", asn=151)))

    ###############################################################################
    # Create and set up the stub AS (AS152)

    as152 = base.createAutonomousSystem(152)
    as152.createNetwork("net0")
    as152.createRouter("router0").joinNetwork("net0").joinNetwork("ix101")
    as152.createHost("web").joinNetwork("net0")
    web.install("web152")
    emu.addBinding(Binding("web152", filter=Filter(nodeName="web", asn=152)))

    ###############################################################################
    # Make AS2 the Internet service provider for AS151 and AS152.

    ebgp.addPrivatePeering(100, 2, 151, abRelationship=PeerRelationship.Provider)
    ebgp.addPrivatePeering(101, 2, 152, abRelationship=PeerRelationship.Provider)

    emu.addLayer(base)
    emu.addLayer(routing)
    emu.addLayer(ebgp)
    emu.addLayer(mpls)
    emu.addLayer(web)
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
        ###############################################################################
        # Save the emulation if needed. This must happen before rendering.
        emu.dump(dumpfile)
        ###############################################################################
        return

    ###############################################################################
    # Render the emulation.
    if render:
        emu.render()

    ###############################################################################
    # Generate the Docker files.
    output_dir = Path(output or SCRIPT_DIR / "output").resolve()
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    emu.compile(Docker(platform=platform), str(output_dir), override=override)


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
