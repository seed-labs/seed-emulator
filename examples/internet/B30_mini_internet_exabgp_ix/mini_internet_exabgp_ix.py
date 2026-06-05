#!/usr/bin/env python3

import argparse
import os
from pathlib import Path
import sys
from typing import Optional

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from seedemu.compiler import Docker, Platform
from seedemu.core import Binding, Emulator, Filter
from seedemu.services import ExaBgpService
from examples.internet.B00_mini_internet import mini_internet


EXABGP_ASN = 180
EXABGP_NODE = "exabgp"
EXABGP_VNODE = "as180_exabgp"
EXABGP_IX = 100
EXABGP_IX_ADDRESS = "10.100.0.180"
EXABGP_ANNOUNCEMENT = "203.0.113.0/24"
EXABGP_EXTRA_ANNOUNCEMENT = "203.0.114.0/24"
EXABGP_CONTAINER_PORT = 5000
EXABGP_HOST_PORT_ENV = "SEED_B30_EXABGP_PORT"
EXABGP_DEFAULT_HOST_PORT = 5106


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build mini_internet with an AS180 ExaBGP IX control-plane speaker"
    )
    parser.add_argument("platform", nargs="?", default="amd", choices=["amd", "arm"])
    return parser.parse_args()


def resolve_platform(name: str) -> Platform:
    return Platform.AMD64 if name == "amd" else Platform.ARM64


def get_dashboard_host_port() -> int:
    value = os.environ.get(EXABGP_HOST_PORT_ENV, str(EXABGP_DEFAULT_HOST_PORT))
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{EXABGP_HOST_PORT_ENV} must be an integer, got {value!r}") from exc


def add_exabgp_ix_speaker(emu: Emulator):
    base = emu.getLayer("Base")

    as180 = base.createAutonomousSystem(EXABGP_ASN)
    speaker = as180.createHost(EXABGP_NODE)
    speaker.joinNetwork(f"ix{EXABGP_IX}", address=EXABGP_IX_ADDRESS)
    speaker.addPort(get_dashboard_host_port(), EXABGP_CONTAINER_PORT, "tcp")
    speaker.setDisplayName("AS180 ExaBGP IX Control Plane")
    return speaker


def build_emulator() -> Emulator:
    base_bin = SCRIPT_DIR / "base_internet.bin"
    mini_internet.run(dumpfile=str(base_bin), hosts_per_as=0)

    emu = Emulator()
    emu.load(str(base_bin))

    add_exabgp_ix_speaker(emu)
    exabgp = ExaBgpService()
    exabgp.install(EXABGP_VNODE) \
        .setLocalAsn(EXABGP_ASN) \
        .addPeer("r100", router_asn=2, router_relationship="customer") \
        .addPeer("r100", router_asn=3, router_relationship="customer") \
        .addAnnouncement(EXABGP_ANNOUNCEMENT) \
        .addAnnouncement(EXABGP_EXTRA_ANNOUNCEMENT)
    emu.addBinding(Binding(EXABGP_VNODE, filter=Filter(asn=EXABGP_ASN, nodeName=EXABGP_NODE)))
    emu.addLayer(exabgp)

    return emu


def run(dumpfile: Optional[str] = None) -> None:
    emu = build_emulator()

    if dumpfile is not None:
        emu.dump(dumpfile)
        return

    args = parse_args()
    output_dir = SCRIPT_DIR / "output"

    emu.render()
    emu.compile(
        Docker(platform=resolve_platform(args.platform)),
        str(output_dir),
        override=True,
    )

    print(f"Generated Docker output in: {output_dir}")
    print(
        "ExaBGP dashboard will be published on host port "
        f"{get_dashboard_host_port()} when the compose project is started."
    )


if __name__ == "__main__":
    run()
