#!/usr/bin/env python3
# encoding: utf-8

from __future__ import annotations

import argparse
from pathlib import Path
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from seedemu.compiler import Docker, Platform
from seedemu.core import Binding, Emulator, Filter
from seedemu.layers import Base, Ebgp, Routing
from seedemu.services import WebService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a small SEED Emulator topology for ExampleRunner."
    )
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
    web = WebService()

    base.createInternetExchange(100)

    for asn in [150, 151, 152]:
        current_as = base.createAutonomousSystem(asn)
        current_as.createNetwork("net0")
        current_as.createRouter("router0").joinNetwork("net0").joinNetwork("ix100")
        current_as.createHost("web").joinNetwork("net0")

        vnode = "web{}".format(asn)
        web.install(vnode)
        emu.addBinding(Binding(vnode, filter=Filter(nodeName="web", asn=asn)))
        ebgp.addRsPeer(100, asn)

    emu.addLayer(base)
    emu.addLayer(routing)
    emu.addLayer(ebgp)
    emu.addLayer(web)
    return emu


def main() -> int:
    args = parse_args()
    emu = build_emulator()

    if args.dumpfile:
        emu.dump(args.dumpfile)
        print("Saved sample emulator to {}".format(args.dumpfile))
        return 0

    if args.render:
        emu.render()

    output_dir = Path(args.output).resolve()
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    emu.compile(Docker(platform=resolve_platform(args.platform)), str(output_dir), override=args.override)
    print("Generated sample SEED Emulator Docker output in {}".format(output_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
