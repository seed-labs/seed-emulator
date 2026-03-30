#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List

ROLE_SET = {"r", "brd", "rs"}


@dataclass(frozen=True)
class PodTarget:
    name: str
    asn: str
    role: str
    node: str
    logical_name: str


@dataclass(frozen=True)
class ProtocolState:
    name: str
    family: str
    healthy: bool
    raw_line: str


def run(cmd: List[str], *, timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        detail = stderr or f"command timed out after {timeout} seconds"
        return subprocess.CompletedProcess(cmd, 124, stdout, detail)


def kubectl(namespace: str, args: List[str], *, timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    return run(["kubectl", "-n", namespace, *args], timeout=timeout)


def ensure_targets(namespace: str) -> List[PodTarget]:
    result = kubectl(namespace, ["get", "pods", "-o", "json"], timeout=60)
    result.check_returncode()
    data = json.loads(result.stdout)
    targets: List[PodTarget] = []
    for item in data.get("items", []):
        labels = (item.get("metadata", {}) or {}).get("labels", {}) or {}
        if labels.get("seedemu.io/workload") != "seedemu":
            continue
        role = str(labels.get("seedemu.io/role", ""))
        if role not in ROLE_SET:
            continue
        if str(item.get("status", {}).get("phase", "")) != "Running":
            continue
        targets.append(
            PodTarget(
                name=str(item.get("metadata", {}).get("name", "")),
                asn=str(labels.get("seedemu.io/asn", "")),
                role=role,
                node=str(item.get("spec", {}).get("nodeName", "")),
                logical_name=str(labels.get("seedemu.io/name", "")),
            )
        )
    targets.sort(key=lambda pod: (int(pod.asn or 0), pod.logical_name, pod.name))
    return targets


def parse_bird_protocols(raw: str) -> List[ProtocolState]:
    rows: List[ProtocolState] = []
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(("BIRD ", "Name ", "Access restricted", "Error from server")):
            continue
        if ".go:" in stripped and stripped.startswith(("I0", "W0", "E0")):
            continue
        parts = stripped.split()
        if len(parts) < 2:
            continue
        proto_name = parts[0]
        proto_type = parts[1]
        if proto_type == "BGP" and proto_name.startswith("Ibgp_"):
            family = "ibgp"
            healthy = "Established" in stripped
        elif proto_type == "BGP" and proto_name.startswith("Ebgp_"):
            family = "ebgp"
            healthy = "Established" in stripped
        elif proto_type == "OSPF":
            family = "ospf"
            healthy = "Running" in stripped or "Alone" in stripped
        else:
            continue
        rows.append(
            ProtocolState(
                name=proto_name,
                family=family,
                healthy=healthy,
                raw_line=stripped,
            )
        )
    return rows


def ospf_row_is_healthy(row: ProtocolState, *, ibgp_total: int) -> bool:
    if row.family != "ospf":
        return row.healthy
    if "Running" in row.raw_line:
        return True
    if "Alone" in row.raw_line:
        return ibgp_total == 0
    return False


def fetch_protocols(namespace: str, target: PodTarget, timeout_seconds: int) -> dict:
    result = kubectl(namespace, ["exec", target.name, "--", "sh", "-lc", "birdc show protocols"], timeout=timeout_seconds)
    raw = "\n".join(chunk for chunk in [result.stdout, result.stderr] if chunk)
    rows = parse_bird_protocols(raw)

    ibgp_rows = [row for row in rows if row.family == "ibgp"]
    ebgp_rows = [row for row in rows if row.family == "ebgp"]
    ospf_rows = [row for row in rows if row.family == "ospf"]
    ibgp_established = sum(1 for row in ibgp_rows if row.healthy)
    ebgp_established = sum(1 for row in ebgp_rows if row.healthy)
    ospf_running = sum(1 for row in ospf_rows if ospf_row_is_healthy(row, ibgp_total=len(ibgp_rows)))
    failures = [row.raw_line for row in ibgp_rows if not row.healthy]
    failures.extend(row.raw_line for row in ebgp_rows if not row.healthy)
    failures.extend(
        row.raw_line for row in ospf_rows if not ospf_row_is_healthy(row, ibgp_total=len(ibgp_rows))
    )

    return {
        "pod": target.name,
        "logical_name": target.logical_name,
        "asn": target.asn,
        "role": target.role,
        "node": target.node,
        "exec_rc": result.returncode,
        "exec_failed": result.returncode != 0,
        "raw_output": raw,
        "ibgp_total": len(ibgp_rows),
        "ibgp_established": ibgp_established,
        "ibgp_failed": len(ibgp_rows) - ibgp_established,
        "ebgp_total": len(ebgp_rows),
        "ebgp_established": ebgp_established,
        "ebgp_failed": len(ebgp_rows) - ebgp_established,
        "ospf_total": len(ospf_rows),
        "ospf_running": ospf_running,
        "ospf_failed": len(ospf_rows) - ospf_running,
        "protocol_failures": failures,
    }


def ratio(established: int, total: int) -> float:
    if total <= 0:
        return 1.0
    return established / total


def summarize(namespace: str, results: Iterable[dict]) -> dict:
    ordered = list(results)
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "namespace": namespace,
        "pods_checked": len(ordered),
        "ibgp_total": sum(item["ibgp_total"] for item in ordered),
        "ibgp_established": sum(item["ibgp_established"] for item in ordered),
        "ibgp_failed": sum(item["ibgp_failed"] for item in ordered),
        "ebgp_total": sum(item["ebgp_total"] for item in ordered),
        "ebgp_established": sum(item["ebgp_established"] for item in ordered),
        "ebgp_failed": sum(item["ebgp_failed"] for item in ordered),
        "ospf_total": sum(item["ospf_total"] for item in ordered),
        "ospf_running": sum(item["ospf_running"] for item in ordered),
        "ospf_failed": sum(item["ospf_failed"] for item in ordered),
        "exec_failed_pods": [item["pod"] for item in ordered if item["exec_failed"]],
        "pods_with_ibgp_failures": [
            item["pod"] for item in ordered if item["ibgp_total"] > 0 and item["ibgp_failed"] > 0
        ],
        "pods_with_ebgp_failures": [
            item["pod"] for item in ordered if item["ebgp_total"] > 0 and item["ebgp_failed"] > 0
        ],
        "pods_with_ospf_failures": [
            item["pod"] for item in ordered if item["ospf_total"] > 0 and item["ospf_failed"] > 0
        ],
    }
    summary["ibgp_established_ratio"] = ratio(summary["ibgp_established"], summary["ibgp_total"])
    summary["ebgp_established_ratio"] = ratio(summary["ebgp_established"], summary["ebgp_total"])
    summary["ospf_running_ratio"] = ratio(summary["ospf_running"], summary["ospf_total"])
    return summary


def determine_failure_reason(summary: dict) -> str:
    if summary["pods_checked"] == 0:
        return "no_router_like_pods_found"
    if summary["ibgp_total"] == 0 and summary["ebgp_total"] == 0:
        return "no_bgp_protocols_found"
    if summary["ibgp_failed"] > 0:
        return "ibgp_incomplete"
    if summary["ebgp_failed"] > 0:
        return "ebgp_incomplete"
    if summary.get("ospf_failed", 0) > 0:
        return "ospf_incomplete"
    if summary["exec_failed_pods"]:
        return "kubectl_exec_failed"
    return ""


def write_outputs(artifact_dir: Path, ordered: List[dict], summary: dict, sample_limit: int) -> None:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    (artifact_dir / "bgp_health_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    header = "pod\tlogical_name\tasn\trole\tnode\tibgp_established\tibgp_total\tebgp_established\tebgp_total\tospf_running\tospf_total\texec_rc"
    rows = [header]
    by_as_rows = ["asn\tpods\tibgp_established\tibgp_total\tebgp_established\tebgp_total\tospf_running\tospf_total"]
    grouped: dict[str, dict[str, int]] = {}
    for item in ordered:
        rows.append(
            "\t".join(
                [
                    item["pod"],
                    item["logical_name"],
                    item["asn"],
                    item["role"],
                    item["node"],
                    str(item["ibgp_established"]),
                    str(item["ibgp_total"]),
                    str(item["ebgp_established"]),
                    str(item["ebgp_total"]),
                    str(item["ospf_running"]),
                    str(item["ospf_total"]),
                    str(item["exec_rc"]),
                ]
            )
        )
        bucket = grouped.setdefault(
            item["asn"],
            {
                "pods": 0,
                "ibgp_established": 0,
                "ibgp_total": 0,
                "ebgp_established": 0,
                "ebgp_total": 0,
                "ospf_running": 0,
                "ospf_total": 0,
            },
        )
        bucket["pods"] += 1
        bucket["ibgp_established"] += item["ibgp_established"]
        bucket["ibgp_total"] += item["ibgp_total"]
        bucket["ebgp_established"] += item["ebgp_established"]
        bucket["ebgp_total"] += item["ebgp_total"]
        bucket["ospf_running"] += item["ospf_running"]
        bucket["ospf_total"] += item["ospf_total"]

    for asn in sorted(grouped, key=lambda value: int(value) if value.isdigit() else value):
        bucket = grouped[asn]
        by_as_rows.append(
            "\t".join(
                [
                    asn,
                    str(bucket["pods"]),
                    str(bucket["ibgp_established"]),
                    str(bucket["ibgp_total"]),
                    str(bucket["ebgp_established"]),
                    str(bucket["ebgp_total"]),
                    str(bucket["ospf_running"]),
                    str(bucket["ospf_total"]),
                ]
            )
        )

    (artifact_dir / "bgp_health_by_pod.tsv").write_text("\n".join(rows) + "\n", encoding="utf-8")
    (artifact_dir / "bgp_health_by_as.tsv").write_text("\n".join(by_as_rows) + "\n", encoding="utf-8")
    (artifact_dir / "protocol_health_by_pod.tsv").write_text("\n".join(rows) + "\n", encoding="utf-8")

    protocol_summary = {
        "generated_at": summary["generated_at"],
        "namespace": summary["namespace"],
        "passed": summary.get("passed", False),
        "failure_reason": summary.get("failure_reason", ""),
        "families": {
            "ibgp": {
                "total": summary["ibgp_total"],
                "healthy": summary["ibgp_established"],
                "failed": summary["ibgp_failed"],
            },
            "ebgp": {
                "total": summary["ebgp_total"],
                "healthy": summary["ebgp_established"],
                "failed": summary["ebgp_failed"],
            },
            "ospf": {
                "total": summary["ospf_total"],
                "healthy": summary["ospf_running"],
                "failed": summary["ospf_failed"],
            },
        },
        "exec_failed_pods": summary["exec_failed_pods"],
    }
    (artifact_dir / "protocol_health.json").write_text(json.dumps(protocol_summary, indent=2), encoding="utf-8")

    failure_chunks: List[str] = []
    sample_chunks: List[str] = []
    for item in ordered:
        if sample_limit > 0 and len(sample_chunks) < sample_limit:
            sample_chunks.append(
                "\n".join(
                    [
                        f"=== {item['pod']} as{item['asn']} role={item['role']} node={item['node']} rc={item['exec_rc']} ===",
                        item["raw_output"].rstrip(),
                        "",
                    ]
                )
            )
        if item["exec_failed"] or item["protocol_failures"]:
            failure_chunks.append(
                "\n".join(
                    [
                        f"=== {item['pod']} as{item['asn']} role={item['role']} node={item['node']} rc={item['exec_rc']} ===",
                        *(item["protocol_failures"] or []),
                        "",
                    ]
                )
            )

    (artifact_dir / "bgp_health_failures.txt").write_text("".join(failure_chunks), encoding="utf-8")
    bird_sample = sample_chunks[0] if sample_chunks else ""
    (artifact_dir / "bird_sample.txt").write_text(bird_sample, encoding="utf-8")
    (artifact_dir / "bgp_health_samples.txt").write_text("".join(sample_chunks), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect evidence-first BGP health for a SEED K8s namespace.")
    parser.add_argument("namespace")
    parser.add_argument("artifact_dir")
    parser.add_argument("--parallelism", type=int, default=8)
    parser.add_argument("--kubectl-timeout", type=int, default=30)
    parser.add_argument("--sample-limit", type=int, default=12)
    args = parser.parse_args()

    artifact_dir = Path(args.artifact_dir)
    try:
        targets = ensure_targets(args.namespace)
    except subprocess.CalledProcessError as exc:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        summary = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "namespace": args.namespace,
            "pods_checked": 0,
            "failure_reason": "kubectl_exec_failed",
            "stderr": exc.stderr,
            "stdout": exc.stdout,
        }
        (artifact_dir / "bgp_health_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print("kubectl_exec_failed")
        return 1

    raw_results: List[dict] = []
    with ThreadPoolExecutor(max_workers=max(1, args.parallelism)) as pool:
        future_map = {
            pool.submit(fetch_protocols, args.namespace, target, args.kubectl_timeout): target for target in targets
        }
        completed_raw: dict[str, dict] = {}
        for future in as_completed(future_map):
            result = future.result()
            completed_raw[result["pod"]] = result
        for target in targets:
            raw_results.append(completed_raw[target.name])

    summary = summarize(args.namespace, raw_results)
    failure_reason = determine_failure_reason(summary)
    summary["failure_reason"] = failure_reason
    summary["passed"] = failure_reason == ""

    write_outputs(artifact_dir, raw_results, summary, args.sample_limit)

    if failure_reason:
        print(failure_reason)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
