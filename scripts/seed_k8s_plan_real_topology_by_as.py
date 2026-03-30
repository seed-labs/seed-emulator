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


def _parse_int(value: object, default: int = 0) -> int:
    text = str(value or "").strip()
    if not text:
        return default
    if text.lower().endswith("k"):
        return int(float(text[:-1]) * 1000)
    return int(text)


def current_pod_usage(
    pods_json: Path | None,
    *,
    excluded_namespaces: Set[str] | None = None,
) -> Dict[str, int]:
    if pods_json is None or not pods_json.exists():
        return {}

    data = json.loads(pods_json.read_text(encoding="utf-8"))
    usage: Dict[str, int] = {}
    excluded = excluded_namespaces or set()
    for item in data.get("items", []):
        metadata = item.get("metadata", {}) or {}
        namespace = str(metadata.get("namespace", "") or "")
        if namespace in excluded:
            continue
        node_name = str(item.get("spec", {}).get("nodeName", "") or "")
        if not node_name:
            continue
        usage[node_name] = usage.get(node_name, 0) + 1
    return usage


def ready_nodes(nodes_json: Path, pod_reserve: int, pods_json: Path | None = None) -> List[dict]:
    data = json.loads(nodes_json.read_text(encoding="utf-8"))
    excluded_namespaces = {
        value.strip()
        for value in (
            os.environ.get("SEED_EXCLUDED_NAMESPACES")
            or os.environ.get("SEED_NAMESPACE")
            or ""
        ).split(",")
        if value.strip()
    }
    usage = current_pod_usage(pods_json, excluded_namespaces=excluded_namespaces)
    nodes = []
    for item in data.get("items", []):
        conds = item.get("status", {}).get("conditions", []) or []
        ready = any(c.get("type") == "Ready" and c.get("status") == "True" for c in conds)
        if not ready:
            continue
        if item.get("spec", {}).get("unschedulable"):
            continue
        labels = item.get("metadata", {}).get("labels", {}) or {}
        node_name = str(item.get("metadata", {}).get("name", ""))
        allocatable_pods = _parse_int(item.get("status", {}).get("allocatable", {}).get("pods", "110"), 110)
        current_pods = usage.get(node_name, 0)
        effective_capacity = max(0, allocatable_pods - current_pods - pod_reserve)
        nodes.append({
            "name": node_name,
            "allocatable_pods": allocatable_pods,
            "current_pods": current_pods,
            "pod_reserve": pod_reserve,
            "effective_capacity": effective_capacity,
            "assigned_pods": 0,
            "assigned_asns": [],
            "is_control_plane": (
                "node-role.kubernetes.io/control-plane" in labels
                or "node-role.kubernetes.io/master" in labels
            ),
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
        feasible = [
            item
            for item in nodes
            if pod_count <= (item["effective_capacity"] - item["assigned_pods"])
        ]
        if not feasible:
            candidate = sorted(
                nodes,
                key=lambda item: (
                    -(item["effective_capacity"] - item["assigned_pods"]),
                    item.get("is_control_plane", False),
                    item["assigned_pods"],
                    item["name"],
                ),
            )[0]
            remaining = candidate["effective_capacity"] - candidate["assigned_pods"]
            raise ValueError(
                f"ASN {asn} needs {pod_count} pods, but best remaining node {candidate['name']} only has {remaining} pod slots left"
            )

        preferred_pool = feasible
        if pod_count > 1:
            worker_feasible = [item for item in feasible if not item.get("is_control_plane", False)]
            if worker_feasible:
                preferred_pool = worker_feasible

        candidate = sorted(
            preferred_pool,
            key=lambda item: (
                -(item["effective_capacity"] - item["assigned_pods"]),
                item["assigned_pods"],
                item["name"],
            ),
        )[0]
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
    pods_json_env = os.environ.get("SEED_CURRENT_PODS_JSON_PATH", "").strip()
    pods_json = Path(pods_json_env) if pods_json_env else None
    pod_reserve = int(os.environ.get("SEED_NODE_POD_RESERVE", "5"))

    topo = load_topology(topology_file)
    assignment = load_assignment(assignment_file)
    counts = compute_as_pod_counts(topo, assignment)
    nodes = ready_nodes(nodes_json, pod_reserve, pods_json)
    mapping, plan = assign(counts, nodes)

    mapping_json.parent.mkdir(parents=True, exist_ok=True)
    mapping_json.write_text(json.dumps(mapping, indent=2), encoding="utf-8")
    plan_json.write_text(json.dumps(plan, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
