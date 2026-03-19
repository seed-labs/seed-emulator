#!/usr/bin/env python3
from __future__ import annotations

import ast
import json
import os
import pickle
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple


def load_topology(path: Path) -> dict:
    data = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = ast.literal_eval(value.strip())
    return data


def load_assignment(path: Path) -> dict:
    with path.open("rb") as handle:
        data = pickle.load(handle)
    if not isinstance(data, dict):
        raise ValueError("assignment.pkl must contain a dict")
    return data


def ready_nodes(nodes_json: Path, pod_reserve: int) -> List[dict]:
    data = json.loads(nodes_json.read_text(encoding="utf-8"))
    nodes = []
    for item in data.get("items", []):
        conds = item.get("status", {}).get("conditions", []) or []
        ready = any(c.get("type") == "Ready" and c.get("status") == "True" for c in conds)
        if not ready:
            continue
        if item.get("spec", {}).get("unschedulable"):
            continue
        allocatable_pods = int(str(item.get("status", {}).get("allocatable", {}).get("pods", "110")))
        nodes.append({
            "name": str(item.get("metadata", {}).get("name", "")),
            "allocatable_pods": allocatable_pods,
            "effective_capacity": max(1, allocatable_pods - pod_reserve),
            "assigned_pods": 0,
            "assigned_asns": [],
        })
    nodes.sort(key=lambda item: item["name"])
    return nodes


def compute_as_pod_counts(topo: dict, assignment: dict) -> Dict[str, int]:
    counts: Dict[str, int] = {}

    for ixp_name in topo.get("ixps", []):
        counts[str(int(assignment[ixp_name]["asn"]))] = 1

    connected: Dict[int, Set[int]] = {}
    for transit_key in topo.get("transit_asns", []):
        asn = int(assignment[transit_key]["asn"])
        connected[asn] = set()

    for ix_a, ix_b, transit_key, _ in topo.get("ix_ix_transit_edges", []):
        transit_asn = int(assignment[transit_key]["asn"])
        connected.setdefault(transit_asn, set()).add(int(assignment[ix_a]["asn"]))
        connected.setdefault(transit_asn, set()).add(int(assignment[ix_b]["asn"]))

    for transit_key in topo.get("transit_asns", []):
        asn = int(assignment[transit_key]["asn"])
        counts[str(asn)] = len(connected.get(asn, set()))

    for stub_key in topo.get("stub_asns", []):
        counts[str(int(assignment[stub_key]["asn"]))] = 1

    return counts


def assign(counts: Dict[str, int], nodes: List[dict]) -> Tuple[Dict[str, dict], dict]:
    if not nodes:
        raise ValueError("No Ready schedulable Kubernetes nodes found")

    mapping: Dict[str, dict] = {}
    as_items = sorted(counts.items(), key=lambda item: (-item[1], int(item[0]) if item[0].isdigit() else item[0]))
    for asn, pod_count in as_items:
        candidate = sorted(nodes, key=lambda item: (-item["effective_capacity"] + item["assigned_pods"], item["assigned_pods"], item["name"]))[0]
        remaining = candidate["effective_capacity"] - candidate["assigned_pods"]
        if pod_count > remaining:
            raise ValueError(
                f"ASN {asn} needs {pod_count} pods, but best remaining node {candidate['name']} only has {remaining} pod slots left"
            )
        candidate["assigned_pods"] += pod_count
        candidate["assigned_asns"].append(asn)
        mapping[asn] = {"kubernetes.io/hostname": candidate["name"]}

    plan = {
        "as_pod_counts": counts,
        "nodes": nodes,
        "assignments": {asn: selector["kubernetes.io/hostname"] for asn, selector in mapping.items()},
    }
    return mapping, plan


def main() -> int:
    if len(sys.argv) != 6:
        print(
            "Usage: scripts/seed_k8s_plan_real_topology_by_as.py <topology_file> <assignment_file> <nodes_json> <mapping_json> <plan_json>",
            file=sys.stderr,
        )
        return 2

    topology_file = Path(os.path.expanduser(sys.argv[1]))
    assignment_file = Path(os.path.expanduser(sys.argv[2]))
    nodes_json = Path(sys.argv[3])
    mapping_json = Path(sys.argv[4])
    plan_json = Path(sys.argv[5])
    pod_reserve = int(os.environ.get("SEED_NODE_POD_RESERVE", "20"))

    topo = load_topology(topology_file)
    assignment = load_assignment(assignment_file)
    counts = compute_as_pod_counts(topo, assignment)
    nodes = ready_nodes(nodes_json, pod_reserve)
    mapping, plan = assign(counts, nodes)

    mapping_json.parent.mkdir(parents=True, exist_ok=True)
    mapping_json.write_text(json.dumps(mapping, indent=2), encoding="utf-8")
    plan_json.write_text(json.dumps(plan, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
