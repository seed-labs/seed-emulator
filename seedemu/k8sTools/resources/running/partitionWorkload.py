#!/usr/bin/env python3
"""Apply a placement algorithm to a compiled SeedEMU Kubernetes manifest.

Inputs are a compiler manifest and kubeconfig. The script reads Ready node and
active Pod state through kubectl, writes a source snapshot plus partition
evidence beside the manifest, and updates workload Pod specs with nodeName.
It is run by ``seedemu.k8sTools`` immediately before image build/deployment.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

# The running resource is copied to a temporary directory. Prefer the source
# checkout before importing so an unrelated installed ``seedemu`` is not
# cached after a partial import; installed distributions still work when no
# checkout is present.
for candidate in Path(__file__).resolve().parents:
    if (candidate / "seedemu" / "k8sTools" / "partition.py").is_file():
        sys.path.insert(0, str(candidate))
        break
from seedemu.k8sTools.partition import partitionManifest


def parseArgs(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse placement CLI arguments."""
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--kubeconfig", type=Path, required=True)
    parser.add_argument(
        "--partition",
        dest="algorithm", default="nodeByAs", metavar="NAME_OR_SCRIPT.py",
        help="built-in placement name or Python script accepting --input/--output JSON",
    )
    parser.add_argument("--pod-reserve", type=int, default=0)
    parser.add_argument("--max-nodes-per-worker", type=int, default=900)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run placement and print a compact evidence summary."""
    args = parseArgs(argv)
    if args.pod_reserve < 0:
        raise SystemExit("--pod-reserve must be nonnegative")
    result = partitionManifest(
        args.manifest,
        args.kubeconfig,
        algorithm=args.algorithm,
        podReserve=args.pod_reserve,
        maxNodesPerWorker=args.max_nodes_per_worker,
    )
    print(
        f"[k8s_partition] algorithm={result['algorithm']} "
        f"workloads={len(result['workloads'])} nodes={len(result['nodes'])} "
        f"binding={result['placementBinding']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
