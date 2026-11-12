#!/usr/bin/env python3
"""Managed partition script template for K8sTools.py up --partition SCRIPT.py.

Read topology, ASN membership and remaining node budgets from --input JSON;
write a complete workload-to-node mapping to --output JSON. Run locally with
the same Python environment as k8sTools; no Kubernetes calls or cluster writes.
Copy this script and replace createPartition to implement another algorithm.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path


def createPartition(value: dict) -> dict:
    """Assign value's whole ASN groups using its remainingCapacity budgets."""
    if value.get("schemaVersion") != 1:
        raise ValueError("Expected partition input schemaVersion=1")
    remaining = {name: dict(budget) for name, budget in value["remainingCapacity"].items()}
    groups = defaultdict(list)
    assigned = defaultdict(int)
    for workload in value["workloads"]:
        groups[workload["asn"]].append(workload)
    mapping = {}
    for asn, members in sorted(groups.items(), key=lambda item: (
        -sum(member["replicas"] for member in item[1]), int(item[0]),
    )):
        demand = {
            "podSlots": sum(member["replicas"] for member in members),
            "cpuMillis": sum(member["replicas"] * member["cpuMillis"] for member in members),
            "memoryBytes": sum(member["replicas"] * member["memoryBytes"] for member in members),
        }
        candidates = [name for name, budget in remaining.items()
                      if all(demand[key] <= budget[key] for key in demand)]
        if not candidates:
            raise ValueError(f"ASN {asn} does not fit any remaining node budget")
        target = min(candidates, key=lambda name: (
            -remaining[name]["podSlots"], assigned[name], name,
        ))
        for key in demand:
            remaining[target][key] -= demand[key]
        assigned[target] += demand['podSlots']
        mapping.update({member["name"]: target for member in members})
    return {"mapping": mapping, "details": {"algorithm": "example whole-AS placement"}}


def main() -> int:
    """Read explicit CLI input/output paths and write only the partition result."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    value = json.loads(args.input.read_text(encoding="utf-8"))
    args.output.write_text(json.dumps(createPartition(value), indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
