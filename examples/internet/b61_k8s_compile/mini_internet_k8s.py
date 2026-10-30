#!/usr/bin/env python3
"""Compile a small SeedEMU Internet topology to native Kubernetes manifests.

Outputs are written to ./output by default:
- k8s.kube-ovn.yaml: Kubernetes namespace, Kube-OVN Vpc/Subnet,
  NetworkAttachmentDefinitions, Deployments.
- images.yaml: image build contexts consumed by the generated running/ stage.
- per-node Docker build contexts and optional base_images/ contexts.
Default CNI is kube-ovn. Use --cni-type macvlan for macvlan manifests.
"""

from __future__ import annotations
import argparse
import sys
from pathlib import Path
import os

SCRIPT_DIR = Path(__file__).resolve().parent


def findRepoRoot(start: Path) -> Path:
    """Find the SeedEMU source tree that contains this example."""
    for candidate in (start, *start.parents):
        if (candidate / "seedemu").is_dir() and (candidate / "setup.py").is_file():
            return candidate
    raise RuntimeError(f"Cannot find SeedEMU repository root above {start}")


REPO_ROOT = findRepoRoot(SCRIPT_DIR)
sys.path = [path for path in sys.path if path != str(REPO_ROOT)]
sys.path.insert(0, str(REPO_ROOT))

from seedemu.core import Emulator
from seedemu.layers import Base, Routing, Ebgp, Ibgp, Ospf, PeerRelationship
from seedemu.utilities import Makers
from seedemu.compiler import Platform

from seedemu.compiler import KubernetesCompiler


HOSTS_PER_AS = 2
OUTPUT_DIR = Path("./output")


def parse_args() -> argparse.Namespace:
    """Parse compile options for the B61 native Kubernetes example."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help="Output directory for Kubernetes manifests and Docker build contexts.",
    )
    parser.add_argument(
        "--platform",
        choices=("amd64", "arm64"),
        default="amd64",
        help="Target platform for Docker build contexts.",
    )
    parser.add_argument(
        "--cni-type",
        choices=("kube-ovn", "ovn", "macvlan"),
        default="kube-ovn",
        help="Secondary CNI backend for SeedEMU links. Defaults to kube-ovn.",
    )
    return parser.parse_args()


def build_mini_internet(hosts_per_as: int) -> Emulator:
    emu = Emulator()
    ebgp = Ebgp()
    base = Base()

    ix100 = base.createInternetExchange(100)
    ix101 = base.createInternetExchange(101)
    ix102 = base.createInternetExchange(102)
    ix103 = base.createInternetExchange(103)
    ix104 = base.createInternetExchange(104)
    ix105 = base.createInternetExchange(105)

    ix100.getPeeringLan().setDisplayName("NYC-100")
    ix101.getPeeringLan().setDisplayName("San Jose-101")
    ix102.getPeeringLan().setDisplayName("Chicago-102")
    ix103.getPeeringLan().setDisplayName("Miami-103")
    ix104.getPeeringLan().setDisplayName("Boston-104")
    ix105.getPeeringLan().setDisplayName("Houston-105")

    Makers.makeTransitAs(base, 2, [100, 101, 102, 105], [(100, 101), (101, 102), (100, 105)])
    Makers.makeTransitAs(base, 3, [100, 103, 104, 105], [(100, 103), (100, 105), (103, 105), (103, 104)])
    Makers.makeTransitAs(base, 4, [100, 102, 104], [(100, 104), (102, 104)])
    Makers.makeTransitAs(base, 11, [102, 105], [(102, 105)])
    Makers.makeTransitAs(base, 12, [101, 104], [(101, 104)])

    for asn, ix in [
        (150, 100), (151, 100), (152, 101), (153, 101), (154, 102),
        (160, 103), (161, 103), (162, 103), (163, 104), (164, 104),
        (170, 105), (171, 105),
    ]:
        Makers.makeStubAsWithHosts(emu, base, asn, ix, hosts_per_as)

    ebgp.addRsPeers(100, [2, 3, 4])
    ebgp.addRsPeers(102, [2, 4])
    ebgp.addRsPeers(104, [3, 4])
    ebgp.addRsPeers(105, [2, 3])

    ebgp.addPrivatePeerings(100, [2], [150, 151], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(100, [3], [150], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(101, [2], [12], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(101, [12], [152, 153], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(102, [2, 4], [11, 154], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(102, [11], [154], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(103, [3], [160, 161, 162], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(104, [3, 4], [12], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(104, [4], [163], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(104, [12], [164], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(105, [3], [11, 170], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(105, [11], [171], PeerRelationship.Provider)

    emu.addLayer(base)
    emu.addLayer(Routing())
    emu.addLayer(ebgp)
    emu.addLayer(Ibgp())
    emu.addLayer(Ospf())
    emu.render()
    return emu


def main() -> int:
    args = parse_args()

    os.chdir(SCRIPT_DIR)
    output_dir = args.output_dir.expanduser()
    if not output_dir.is_absolute():
        output_dir = (SCRIPT_DIR / output_dir).resolve()
    platform = Platform.AMD64 if args.platform == "amd64" else Platform.ARM64

    compiler = KubernetesCompiler(platform=platform, cni_type=args.cni_type)

    emu = build_mini_internet(hosts_per_as=HOSTS_PER_AS)
    emu.compile(compiler, str(output_dir), override=True)

    print("=" * 72)
    print("Native Kubernetes baseline compilation complete.")
    print("=" * 72)
    print("Config file: not used")
    print(f"Output directory: {output_dir}")
    print("Image registry prefix: seedemu")
    print("Namespace: seedemu")
    print(f"CNI type: {args.cni_type}")
    print("Runtime workflow: seedemu.k8sTools")
    print("Inventory required for compile: no")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
