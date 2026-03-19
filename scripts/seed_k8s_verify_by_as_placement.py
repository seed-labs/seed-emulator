#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List


def kubectl_json(namespace: str, resource: str) -> dict:
    out = subprocess.check_output(["kubectl", "-n", namespace, "get", resource, "-o", "json"], text=True)
    return json.loads(out)


def load_expected(path: Path) -> Dict[str, Dict[str, str]]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return {}
    return {str(key): {str(k): str(v) for k, v in value.items()} for key, value in data.items() if isinstance(value, dict)}


def main() -> int:
    if len(sys.argv) < 5:
        print("Usage: scripts/seed_k8s_verify_by_as_placement.py <namespace> <artifact_dir> <mode> <min_nodes> [expected_json]", file=sys.stderr)
        return 2

    namespace = sys.argv[1]
    artifact_dir = Path(sys.argv[2])
    mode = sys.argv[3]
    min_nodes = int(sys.argv[4])
    expected_path = Path(sys.argv[5]) if len(sys.argv) >= 6 else artifact_dir / "placement_expected.json"
    artifact_dir.mkdir(parents=True, exist_ok=True)

    pods = kubectl_json(namespace, "pods")
    nodes = kubectl_json(namespace, "../nodes") if False else None  # placeholder to keep mypy quiet
    nodes = subprocess.check_output(["kubectl", "get", "nodes", "-o", "json"], text=True)
    nodes_data = json.loads(nodes)

    rows: List[dict] = []
    by_as: Dict[str, List[str]] = {}
    unique_nodes = set()
    for item in pods.get("items", []):
        labels = (item.get("metadata", {}) or {}).get("labels", {}) or {}
        if labels.get("seedemu.io/workload") != "seedemu":
            continue
        pod_name = str(item.get("metadata", {}).get("name", ""))
        asn = str(labels.get("seedemu.io/asn", ""))
        node_name = str(item.get("spec", {}).get("nodeName", ""))
        rows.append({"pod": pod_name, "asn": asn, "node": node_name})
        if asn:
            by_as.setdefault(asn, []).append(node_name)
        if node_name:
            unique_nodes.add(node_name)

    ready_nodes = 0
    for item in nodes_data.get("items", []):
        conds = item.get("status", {}).get("conditions", []) or []
        ready = any(c.get("type") == "Ready" and c.get("status") == "True" for c in conds)
        if ready:
            ready_nodes += 1

    (artifact_dir / "placement_raw.tsv").write_text(
        "\n".join(f"{row['pod']}\t{row['asn']}\t{row['node']}" for row in rows) + ("\n" if rows else ""),
        encoding="utf-8",
    )
    (artifact_dir / "placement.tsv").write_text(
        "\n".join(f"{row['pod']}\t{row['asn']}\t{row['node']}" for row in rows) + ("\n" if rows else ""),
        encoding="utf-8",
    )

    expected = load_expected(expected_path)
    errors: List[str] = []
    failure_reason = ""
    placement_by_as_lines = ["asn\tnode\tpod_count"]
    placement_by_as_json: Dict[str, dict] = {}
    for asn in sorted(by_as, key=lambda value: int(value) if value.isdigit() else value):
        nodes_for_as = sorted({node for node in by_as[asn] if node})
        pod_count = len(by_as[asn])
        placement_by_as_lines.append(f"{asn}\t{','.join(nodes_for_as)}\t{pod_count}")
        placement_by_as_json[asn] = {"nodes": nodes_for_as, "pod_count": pod_count}
        if len(nodes_for_as) != 1:
            errors.append(f"ASN {asn} spans multiple nodes: {nodes_for_as}")
            if not failure_reason:
                failure_reason = "asn_split_across_nodes"
            continue
        expected_selector = expected.get(asn, {})
        expected_node = expected_selector.get("kubernetes.io/hostname", "")
        if expected_node and nodes_for_as[0] != expected_node:
            errors.append(f"ASN {asn} expected node {expected_node}, got {nodes_for_as[0]}")
            if not failure_reason:
                failure_reason = "as_assignment_mismatch"

    if len(unique_nodes) < min_nodes:
        errors.append(f"nodes_used={len(unique_nodes)} < required min_nodes={min_nodes}")
        if not failure_reason:
            failure_reason = "placement_check_failed"

    if not rows:
        errors.append("No seedemu workload pods found in namespace")
        if not failure_reason:
            failure_reason = "placement_check_failed"

    placement_passed = len(errors) == 0
    strict3_passed = len(unique_nodes) == 3 and placement_passed

    (artifact_dir / "placement_by_as.tsv").write_text("\n".join(placement_by_as_lines) + "\n", encoding="utf-8")
    (artifact_dir / "placement_by_as.json").write_text(json.dumps(placement_by_as_json, indent=2), encoding="utf-8")

    check = {
        "placement_mode": mode,
        "placement_passed": placement_passed,
        "strict3_passed": strict3_passed,
        "required_nodes": min_nodes,
        "cluster_ready_nodes": ready_nodes,
        "nodes_used_count": len(unique_nodes),
        "nodes_used": sorted(unique_nodes),
        "failure_reason": failure_reason,
        "errors": errors,
        "expected_path": str(expected_path),
    }
    (artifact_dir / "placement_check.json").write_text(json.dumps(check, indent=2), encoding="utf-8")

    if not placement_passed:
        print(failure_reason or "placement_check_failed")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
