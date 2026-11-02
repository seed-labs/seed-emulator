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


MANUAL_MPLS = {
    "e1": {
        "ifaces": ["net_e1_r1"],
        "routes": [
            "ip route replace 10.152.0.0/24 encap mpls 200 via inet 10.2.101.12 dev net_e1_r1",
            "ip route replace 10.153.0.0/24 encap mpls 210 via inet 10.2.101.12 dev net_e1_r1",
            "ip -f mpls route replace 302 via inet 10.101.0.151 dev ix101",
            "ip -f mpls route replace 402 via inet 10.101.0.151 dev ix101",
        ],
    },
    "e2": {
        "ifaces": ["net_e2_r2"],
        "routes": [
            "ip route replace 10.151.0.0/24 encap mpls 300 via inet 10.2.102.12 dev net_e2_r2",
            "ip route replace 10.153.0.0/24 encap mpls 310 via inet 10.2.102.12 dev net_e2_r2",
            "ip -f mpls route replace 202 via inet 10.102.0.152 dev ix102",
            "ip -f mpls route replace 412 via inet 10.102.0.152 dev ix102",
        ],
    },
    "e3": {
        "ifaces": ["net_e3_r3"],
        "routes": [
            "ip route replace 10.151.0.0/24 encap mpls 400 via inet 10.2.103.12 dev net_e3_r3",
            "ip route replace 10.152.0.0/24 encap mpls 410 via inet 10.2.103.12 dev net_e3_r3",
            "ip -f mpls route replace 212 via inet 10.103.0.153 dev ix103",
            "ip -f mpls route replace 312 via inet 10.103.0.153 dev ix103",
        ],
    },
    "r1": {
        "ifaces": ["net_e1_r1", "net12", "net31"],
        "routes": [
            "ip -f mpls route replace 200 as 201 via inet 10.2.12.12 dev net12",
            "ip -f mpls route replace 210 as 211 via inet 10.2.31.13 dev net31",
            "ip -f mpls route replace 301 as 302 via inet 10.2.101.11 dev net_e1_r1",
            "ip -f mpls route replace 401 as 402 via inet 10.2.101.11 dev net_e1_r1",
        ],
    },
    "r2": {
        "ifaces": ["net_e2_r2", "net12", "net23"],
        "routes": [
            "ip -f mpls route replace 201 as 202 via inet 10.2.102.11 dev net_e2_r2",
            "ip -f mpls route replace 300 as 301 via inet 10.2.12.11 dev net12",
            "ip -f mpls route replace 310 as 311 via inet 10.2.23.13 dev net23",
            "ip -f mpls route replace 411 as 412 via inet 10.2.102.11 dev net_e2_r2",
        ],
    },
    "r3": {
        "ifaces": ["net_e3_r3", "net23", "net31"],
        "routes": [
            "ip -f mpls route replace 211 as 212 via inet 10.2.103.11 dev net_e3_r3",
            "ip -f mpls route replace 311 as 312 via inet 10.2.103.11 dev net_e3_r3",
            "ip -f mpls route replace 400 as 401 via inet 10.2.31.11 dev net31",
            "ip -f mpls route replace 410 as 411 via inet 10.2.23.12 dev net23",
        ],
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the A02b manual MPLS example.")
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


def manual_mpls_script(router_name: str) -> str:
    config = MANUAL_MPLS[router_name]
    lines = [
        "#!/bin/bash",
        "set -e",
        "mount -o remount rw /proc/sys 2> /dev/null || true",
        "test -d /proc/sys/net/mpls",
        "echo 1048575 > /proc/sys/net/mpls/platform_labels",
        "sleep 5",
    ]
    for iface in config["ifaces"]:
        lines.append('echo 1 > "/proc/sys/net/mpls/conf/{}/input"'.format(iface))
    lines.extend(config["routes"])
    lines.append("ip -f mpls route show > /manual_mpls_table.txt")
    lines.append("ip route show > /manual_ip_routes.txt")
    return "\n".join(lines) + "\n"


def install_manual_mpls(router, router_name: str) -> None:
    router.setPrivileged(True)
    router.setFile("/manual_mpls_setup.sh", manual_mpls_script(router_name))
    router.appendStartCommand("chmod +x /manual_mpls_setup.sh", isPostConfigCommand=True)
    router.appendStartCommand("/manual_mpls_setup.sh", isPostConfigCommand=True)


def build_emulator() -> Emulator:
    emu = Emulator()

    base = Base()
    routing = Routing()
    ebgp = Ebgp()
    web = WebService()

    base.createInternetExchange(101)
    base.createInternetExchange(102)
    base.createInternetExchange(103)

    as2 = base.createAutonomousSystem(2)
    as2.createNetwork("net_e1_r1", prefix="10.2.101.0/24")
    as2.createNetwork("net_e2_r2", prefix="10.2.102.0/24")
    as2.createNetwork("net_e3_r3", prefix="10.2.103.0/24")
    as2.createNetwork("net12", prefix="10.2.12.0/24")
    as2.createNetwork("net23", prefix="10.2.23.0/24")
    as2.createNetwork("net31", prefix="10.2.31.0/24")

    e1 = as2.createRouter("e1")
    e1.joinNetwork("ix101", "10.101.0.2").joinNetwork("net_e1_r1", "10.2.101.11")

    e2 = as2.createRouter("e2")
    e2.joinNetwork("ix102", "10.102.0.2").joinNetwork("net_e2_r2", "10.2.102.11")

    e3 = as2.createRouter("e3")
    e3.joinNetwork("ix103", "10.103.0.2").joinNetwork("net_e3_r3", "10.2.103.11")

    r1 = as2.createRouter("r1")
    r1.joinNetwork("net_e1_r1", "10.2.101.12").joinNetwork("net12", "10.2.12.11").joinNetwork("net31", "10.2.31.11")

    r2 = as2.createRouter("r2")
    r2.joinNetwork("net_e2_r2", "10.2.102.12").joinNetwork("net12", "10.2.12.12").joinNetwork("net23", "10.2.23.12")

    r3 = as2.createRouter("r3")
    r3.joinNetwork("net_e3_r3", "10.2.103.12").joinNetwork("net23", "10.2.23.13").joinNetwork("net31", "10.2.31.13")

    for router, router_name in ((e1, "e1"), (e2, "e2"), (e3, "e3"), (r1, "r1"), (r2, "r2"), (r3, "r3")):
        install_manual_mpls(router, router_name)

    for asn, ix in ((151, 101), (152, 102), (153, 103)):
        current_as = base.createAutonomousSystem(asn)
        current_as.createNetwork("net0")
        current_as.createRouter("router0").joinNetwork("net0").joinNetwork("ix{}".format(ix), "10.{}.0.{}".format(ix, asn))
        current_as.createHost("web").joinNetwork("net0")
        web.install("web{}".format(asn))
        emu.addBinding(Binding("web{}".format(asn), filter=Filter(nodeName="web", asn=asn)))
        ebgp.addPrivatePeering(ix, 2, asn, abRelationship=PeerRelationship.Provider)

    emu.addLayer(base)
    emu.addLayer(routing)
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