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
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from seedemu.compiler import Docker, Platform
from seedemu.core import Binding, Emulator, Filter, Action
from seedemu.layers import Base
from seedemu.services import CAService, CAServer, WebService, WebServer, RootCAStore
import base_internet
from seedemu.containerBundle import InternetMap


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the B25 PKI example.")
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
    base_internet.run(dumpfile=str(base_component))

    emu = Emulator()
    emu.load(str(base_component))

    base: Base = emu.getLayer("Base")

    # Create physical nodes for CA servers.
    as150 = base.getAutonomousSystem(150)
    as150.createHost("ca1").joinNetwork("net0").addHostName("seedCA.net")
    as150.createHost("ca2").joinNetwork("net0").addHostName("seedCA.com")

    # Create physical nodes for HTTPS web servers.
    as151 = base.getAutonomousSystem(151)
    as151.createHost("web1").joinNetwork("net0", address="10.151.0.7").addHostName("example32.com")
    as151.createHost("web2").joinNetwork("net0", address="10.151.0.8").addHostName("bank32.com")

    # Create and configure CA server virtual nodes.
    ca_store_1 = RootCAStore(caDomain="seedCA.net")
    ca_store_2 = RootCAStore(caDomain="seedCA.com")
    ca = CAService()

    ca_server_1: CAServer = ca.install("ca1-vnode")
    ca_server_1.setCAStore(ca_store_1)
    ca_server_1.setCertDuration("2160h")
    ca_server_1.installCACert()

    ca_server_2: CAServer = ca.install("ca2-vnode")
    ca_server_2.setCAStore(ca_store_2)
    ca_server_2.setCertDuration("2160h")
    ca_server_2.installCACert()

    # Create and configure HTTPS web server virtual nodes.
    web = WebService()

    web_server_1: WebServer = web.install("web1-vnode")
    web_server_1.setServerNames(["example32.com"])
    web_server_1.setCAServer(ca_server_1).enableHTTPS()
    web_server_1.setIndexContent("<h1>Web server at example32.com</h1>")

    web_server_2: WebServer = web.install("web2-vnode")
    web_server_2.setServerNames(["bank32.com"])
    web_server_2.setCAServer(ca_server_2).enableHTTPS()
    web_server_2.setIndexContent("<h1>Web server at bank32.com</h1>")

    # Bind virtual nodes to physical nodes.
    emu.addBinding(Binding("ca1-vnode", filter=Filter(nodeName="ca1"), action=Action.FIRST))
    emu.addBinding(Binding("ca2-vnode", filter=Filter(nodeName="ca2"), action=Action.FIRST))
    emu.addBinding(Binding("web1-vnode", filter=Filter(nodeName="web1"), action=Action.FIRST))
    emu.addBinding(Binding("web2-vnode", filter=Filter(nodeName="web2"), action=Action.FIRST))

    emu.addLayer(ca)
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