#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

ROLE_SET = {"r", "brd", "rs"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _derive_duration_fields(
    summary: dict[str, Any],
    timing: dict[str, Any],
    runner_summary: dict[str, Any] | None = None,
) -> dict[str, int]:
    runner_summary = runner_summary or {}
    validation_duration = int(summary.get("validation_duration_seconds", summary.get("duration_seconds", 0)) or 0)
    build_duration = int(timing.get("build_duration_seconds", summary.get("build_duration_seconds", 0)) or 0)
    up_duration = int(timing.get("up_duration_seconds", summary.get("up_duration_seconds", 0)) or 0)
    phase_duration = int(
        timing.get("phase_start_duration_seconds", summary.get("phase_start_duration_seconds", 0)) or 0
    )
    pipeline_duration = max(
        int(summary.get("pipeline_duration_seconds", 0) or 0),
        int(runner_summary.get("duration_seconds", 0) or 0),
        build_duration + up_duration + phase_duration + validation_duration,
        validation_duration,
    )
    return {
        "validation_duration_seconds": validation_duration,
        "build_duration_seconds": build_duration,
        "up_duration_seconds": up_duration,
        "phase_start_duration_seconds": phase_duration,
        "pipeline_duration_seconds": pipeline_duration,
    }


def _run(cmd: list[str], timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        return subprocess.CompletedProcess(cmd, 124, stdout, stderr or "timeout")


def _kubectl(namespace: str, args: list[str], timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    cmd = ["kubectl"]
    if namespace:
        cmd.extend(["-n", namespace])
    cmd.extend(args)
    return _run(cmd, timeout=timeout)


def _kubectl_json(namespace: str, args: list[str], timeout: int | None = None) -> dict[str, Any]:
    result = _kubectl(namespace, args, timeout=timeout)
    if result.returncode != 0:
        return {}
    try:
        loaded = json.loads(result.stdout)
    except Exception:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _kubectl_exec(namespace: str, pod: str, command: str, timeout: int = 20) -> subprocess.CompletedProcess[str]:
    return _kubectl(namespace, ["exec", pod, "--", "sh", "-lc", command], timeout=timeout)


def _seedemu_pods(namespace: str) -> list[dict[str, Any]]:
    pods = _kubectl_json(namespace, ["get", "pods", "-o", "json"], timeout=60)
    rows: list[dict[str, Any]] = []
    for item in pods.get("items", []):
        metadata = item.get("metadata", {}) or {}
        labels = metadata.get("labels", {}) or {}
        if labels.get("seedemu.io/workload") != "seedemu":
            continue
        rows.append(
            {
                "pod": str(metadata.get("name", "")),
                "asn": str(labels.get("seedemu.io/asn", "")),
                "role": str(labels.get("seedemu.io/role", "")),
                "logical_name": str(labels.get("seedemu.io/name", "")),
                "node": str((item.get("spec", {}) or {}).get("nodeName", "")),
                "phase": str((item.get("status", {}) or {}).get("phase", "")),
                "annotations": metadata.get("annotations", {}) or {},
                "labels": labels,
            }
        )
    rows.sort(key=lambda item: (int(item["asn"]) if item["asn"].isdigit() else 0, item["logical_name"], item["pod"]))
    return rows


def _load_network_status(value: Any) -> list[dict[str, Any]]:
    if not value:
        return []
    try:
        loaded = json.loads(str(value))
    except Exception:
        return []
    if isinstance(loaded, dict):
        loaded = [loaded]
    if not isinstance(loaded, list):
        return []
    return [item for item in loaded if isinstance(item, dict)]


def _normalize_network_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        result: list[str] = []
        for item in value:
            if isinstance(item, dict):
                name = item.get("name")
                if name:
                    result.append(str(name))
            elif item:
                result.append(str(item))
        return result
    text = str(value).strip()
    if not text:
        return []
    if text.startswith("["):
        try:
            loaded = json.loads(text)
        except Exception:
            loaded = None
        if isinstance(loaded, list):
            return _normalize_network_list(loaded)
    return [chunk.strip() for chunk in text.split(",") if chunk.strip()]


def _split_columns(line: str) -> list[str]:
    return [chunk for chunk in re.split(r"\s{2,}", line.strip()) if chunk]


def _parse_top_table(raw: str) -> list[dict[str, str]]:
    lines = [line.rstrip() for line in raw.splitlines() if line.strip()]
    if len(lines) < 2:
        return []
    headers = _split_columns(lines[0])
    rows: list[dict[str, str]] = []
    for line in lines[1:]:
        cols = _split_columns(line)
        if not cols:
            continue
        rows.append({headers[index]: cols[index] if index < len(cols) else "" for index in range(len(headers))})
    return rows


def _write_convergence_timeline(artifact_dir: Path, profile_id: str) -> None:
    summary = _load_json(artifact_dir / "summary.json", {})
    timing = _load_json(artifact_dir / "timing.json", {})
    runner_summary = _load_json(artifact_dir.parent / "runner_summary.json", {})
    stage_timeline = _load_json(artifact_dir / "stage_timeline.json", [])
    durations = _derive_duration_fields(
        summary if isinstance(summary, dict) else {},
        timing if isinstance(timing, dict) else {},
        runner_summary if isinstance(runner_summary, dict) else {},
    )
    result = {
        "generated_at": _now(),
        "profile_id": profile_id,
        "namespace": summary.get("namespace", ""),
        "duration_seconds": durations["pipeline_duration_seconds"],
        "validation_duration_seconds": durations["validation_duration_seconds"],
        "build_duration_seconds": durations["build_duration_seconds"],
        "up_duration_seconds": durations["up_duration_seconds"],
        "phase_start_duration_seconds": durations["phase_start_duration_seconds"],
        "pipeline_duration_seconds": durations["pipeline_duration_seconds"],
        "stage_events": stage_timeline if isinstance(stage_timeline, list) else [],
    }
    (artifact_dir / "convergence_timeline.json").write_text(json.dumps(result, indent=2), encoding="utf-8")


def _write_protocol_health(artifact_dir: Path) -> None:
    existing = _load_json(artifact_dir / "protocol_health.json", {})
    if existing:
        return
    bgp = _load_json(artifact_dir / "bgp_health_summary.json", {})
    protocol = {
        "generated_at": _now(),
        "namespace": bgp.get("namespace", ""),
        "passed": bool(bgp.get("passed", False)),
        "failure_reason": str(bgp.get("failure_reason", "") or ""),
        "families": {
            "ibgp": {
                "total": int(bgp.get("ibgp_total", 0) or 0),
                "healthy": int(bgp.get("ibgp_established", 0) or 0),
                "failed": int(bgp.get("ibgp_failed", 0) or 0),
            },
            "ebgp": {
                "total": int(bgp.get("ebgp_total", 0) or 0),
                "healthy": int(bgp.get("ebgp_established", 0) or 0),
                "failed": int(bgp.get("ebgp_failed", 0) or 0),
            },
            "ospf": {
                "total": int(bgp.get("ospf_total", 0) or 0),
                "healthy": int(bgp.get("ospf_running", 0) or 0),
                "failed": int(bgp.get("ospf_failed", 0) or 0),
            },
        },
        "exec_failed_pods": bgp.get("exec_failed_pods", []),
    }
    (artifact_dir / "protocol_health.json").write_text(json.dumps(protocol, indent=2), encoding="utf-8")


def _write_placement_by_as(namespace: str, artifact_dir: Path) -> None:
    pods = _seedemu_pods(namespace)
    if (artifact_dir / "placement_by_as.tsv").exists() and (artifact_dir / "placement_by_as.json").exists():
        return

    rows = ["asn\tnode\tpod_count\tpods"]
    payload: dict[str, dict[str, Any]] = {}
    by_as: dict[str, dict[str, Any]] = {}
    for item in pods:
        asn = item["asn"]
        bucket = by_as.setdefault(asn, {"nodes": set(), "pods": []})
        if item["node"]:
            bucket["nodes"].add(item["node"])
        bucket["pods"].append(item["pod"])

    for asn in sorted(by_as, key=lambda value: int(value) if value.isdigit() else value):
        nodes = sorted(by_as[asn]["nodes"])
        pods_for_as = sorted(by_as[asn]["pods"])
        payload[asn] = {"nodes": nodes, "pods": pods_for_as, "pod_count": len(pods_for_as)}
        rows.append(f"{asn}\t{','.join(nodes)}\t{len(pods_for_as)}\t{','.join(pods_for_as)}")

    (artifact_dir / "placement_by_as.tsv").write_text("\n".join(rows) + "\n", encoding="utf-8")
    (artifact_dir / "placement_by_as.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    if not (artifact_dir / "placement.tsv").exists():
        raw_rows = ["pod\tasn\tnode"]
        raw_rows.extend(f"{item['pod']}\t{item['asn']}\t{item['node']}" for item in pods)
        (artifact_dir / "placement.tsv").write_text("\n".join(raw_rows) + "\n", encoding="utf-8")


def _write_network_attachment_matrix(namespace: str, artifact_dir: Path) -> None:
    pods = _seedemu_pods(namespace)
    rows = [
        "pod\tasn\trole\tlogical_name\tnode\tphase\trequested_networks\treported_networks\tinterfaces\tips"
    ]
    payload: list[dict[str, Any]] = []
    for item in pods:
        annotations = item.get("annotations", {}) or {}
        requested = _normalize_network_list(annotations.get("k8s.v1.cni.cncf.io/networks"))
        network_status = _load_network_status(annotations.get("k8s.v1.cni.cncf.io/network-status"))
        reported = [str(entry.get("name", "")) for entry in network_status if entry.get("name")]
        interfaces = [str(entry.get("interface", "")) for entry in network_status if entry.get("interface")]
        ips: list[str] = []
        for entry in network_status:
            entry_ips = entry.get("ips", [])
            if isinstance(entry_ips, list):
                ips.extend(str(ip) for ip in entry_ips if ip)
        payload.append(
            {
                "pod": item["pod"],
                "asn": item["asn"],
                "role": item["role"],
                "logical_name": item["logical_name"],
                "node": item["node"],
                "phase": item["phase"],
                "requested_networks": requested,
                "reported_networks": reported,
                "interfaces": interfaces,
                "ips": ips,
            }
        )
        rows.append(
            "\t".join(
                [
                    item["pod"],
                    item["asn"],
                    item["role"],
                    item["logical_name"],
                    item["node"],
                    item["phase"],
                    ",".join(requested),
                    ",".join(reported),
                    ",".join(interfaces),
                    ",".join(ips),
                ]
            )
        )

    (artifact_dir / "network_attachment_matrix.tsv").write_text("\n".join(rows) + "\n", encoding="utf-8")
    (artifact_dir / "network_attachment_matrix.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_relationship_graph(namespace: str, artifact_dir: Path) -> None:
    pods = _seedemu_pods(namespace)
    pods_by_as: dict[str, list[str]] = {}
    for item in pods:
        pods_by_as.setdefault(item["asn"], []).append(item["pod"])

    relationship_limit = max(1, int(os.environ.get("SEED_RELATIONSHIP_SAMPLE_LIMIT", "64")))
    router_like = [item for item in pods if item["role"] in ROLE_SET and item["phase"] == "Running"]
    sampled = router_like[:relationship_limit]

    node_items = _kubectl_json("", ["get", "nodes", "-o", "json"], timeout=30).get("items", [])
    nodes = [
        {
            "name": str((item.get("metadata", {}) or {}).get("name", "")),
            "os_image": str(((item.get("status", {}) or {}).get("nodeInfo", {}) or {}).get("osImage", "")),
        }
        for item in node_items
        if isinstance(item, dict)
    ]

    edges: list[dict[str, Any]] = []
    for item in sampled:
        result = _kubectl_exec(namespace, item["pod"], "cat /etc/bird/bird.conf", timeout=10)
        if result.returncode != 0:
            continue
        for neighbor in _parse_bgp_neighbors(result.stdout):
            candidate_pods = list(pods_by_as.get(neighbor["target_asn"], []))
            if neighbor["target_asn"] == item["asn"]:
                candidate_pods = [pod for pod in candidate_pods if pod != item["pod"]]
            edges.append(
                {
                    "source_pod": item["pod"],
                    "source_asn": item["asn"],
                    "source_role": item["role"],
                    "source_node": item["node"],
                    "protocol": neighbor["protocol"],
                    "family": neighbor["family"],
                    "target_asn": neighbor["target_asn"],
                    "target_ip": neighbor["target_ip"],
                    "candidate_target_pods": candidate_pods,
                }
            )

    attachment_rows = _load_json(artifact_dir / "network_attachment_matrix.json", [])
    graph = {
        "generated_at": _now(),
        "namespace": namespace,
        "sampling": {
            "router_like_pods_total": len(router_like),
            "router_like_pods_sampled": len(sampled),
            "sample_limit": relationship_limit,
        },
        "nodes": nodes,
        "pods": [
            {
                "pod": item["pod"],
                "asn": item["asn"],
                "role": item["role"],
                "logical_name": item["logical_name"],
                "node": item["node"],
                "phase": item["phase"],
            }
            for item in pods
        ],
        "asns": [
            {
                "asn": asn,
                "pods": sorted(pods_by_as.get(asn, [])),
                "nodes": sorted({item["node"] for item in pods if item["asn"] == asn and item["node"]}),
            }
            for asn in sorted(pods_by_as, key=lambda value: int(value) if value.isdigit() else value)
        ],
        "network_attachments": attachment_rows if isinstance(attachment_rows, list) else [],
        "protocol_adjacencies": edges,
    }
    (artifact_dir / "relationship_graph.json").write_text(json.dumps(graph, indent=2), encoding="utf-8")


def _pick_router_targets(namespace: str, limit: int) -> list[dict[str, str]]:
    pods = _kubectl_json(namespace, ["get", "pods", "-o", "json"], timeout=60)
    by_as: dict[str, dict[str, str]] = {}
    for item in pods.get("items", []):
        labels = (item.get("metadata", {}) or {}).get("labels", {}) or {}
        if labels.get("seedemu.io/workload") != "seedemu":
            continue
        role = str(labels.get("seedemu.io/role", ""))
        if role not in ROLE_SET:
            continue
        logical_name = str(labels.get("seedemu.io/name", ""))
        if not logical_name.startswith("r"):
            continue
        if str(item.get("status", {}).get("phase", "")) != "Running":
            continue
        asn = str(labels.get("seedemu.io/asn", ""))
        candidate = {
            "pod": str(item.get("metadata", {}).get("name", "")),
            "asn": asn,
            "role": role,
            "logical_name": logical_name,
        }
        current = by_as.get(asn)
        if current is None:
            by_as[asn] = candidate
            continue
        rank = {"r": 0, "brd": 1, "rs": 2}
        if rank.get(candidate["role"], 99) < rank.get(current["role"], 99):
            by_as[asn] = candidate
    ordered = [by_as[key] for key in sorted(by_as, key=lambda value: int(value) if value.isdigit() else value)]
    return ordered[:limit]


def _parse_bgp_neighbors(raw: str) -> list[dict[str, str]]:
    blocks: list[tuple[str, str]] = []
    current_name = ""
    current_lines: list[str] = []
    depth = 0
    for raw_line in raw.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not current_name:
            match = re.match(r"^protocol\s+bgp\s+(\S+)\s*\{", stripped)
            if match:
                current_name = match.group(1)
                current_lines = [line]
                depth = line.count("{") - line.count("}")
            continue
        current_lines.append(line)
        depth += line.count("{") - line.count("}")
        if depth <= 0:
            blocks.append((current_name, "\n".join(current_lines)))
            current_name = ""
            current_lines = []
            depth = 0

    neighbors: list[dict[str, str]] = []
    for proto_name, block in blocks:
        family = "unknown"
        if proto_name.startswith("Ibgp_"):
            family = "ibgp"
        elif proto_name.startswith("Ebgp_"):
            family = "ebgp"
        match = re.search(r"neighbor\s+([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)\s+as\s+([0-9]+);", block)
        if not match:
            continue
        neighbors.append(
            {
                "protocol": proto_name,
                "family": family,
                "target_ip": match.group(1),
                "target_asn": match.group(2),
            }
        )
    return neighbors


def _parse_ping_success(raw: str, target_ip: str) -> bool:
    return bool(re.search(rf"bytes from {re.escape(target_ip)}", raw)) or ", 0% packet loss" in raw


def _write_connectivity_matrix(namespace: str, artifact_dir: Path, profile_id: str, sample_limit: int, timeout: int) -> None:
    rows = ["source_pod\tsource_as\trelation\ttarget_ip\tstatus\tdetail\tevidence"]
    summary = {
        "generated_at": _now(),
        "profile_id": profile_id,
        "namespace": namespace,
        "checks_run": 0,
        "checks_passed": 0,
        "checks_failed": 0,
        "failure_reason": "",
    }

    ping_log = artifact_dir / "ping_150_to_151.txt"
    if ping_log.exists():
        raw = ping_log.read_text(encoding="utf-8", errors="ignore")
        passed = _parse_ping_success(raw, "10.151.0.71")
        rows.append(
            "\t".join(
                [
                    "host_0(as150)",
                    "150",
                    "host_to_host",
                    "10.151.0.71",
                    "pass" if passed else "fail",
                    "mini_known_path",
                    "ping_150_to_151.txt",
                ]
            )
        )
        summary["checks_run"] += 1
        summary["checks_passed" if passed else "checks_failed"] += 1

    selected = _pick_router_targets(namespace, sample_limit)
    for item in selected:
        conf_result = _kubectl_exec(namespace, item["pod"], "cat /etc/bird/bird.conf /etc/bird/conf/*.conf 2>/dev/null || true", timeout=timeout)
        neighbors = _parse_bgp_neighbors(conf_result.stdout)
        seen_relations: set[str] = set()
        for neighbor in neighbors:
            relation = neighbor["family"]
            if relation in seen_relations:
                continue
            seen_relations.add(relation)
            ping_result = _kubectl_exec(namespace, item["pod"], f"ping -c 1 -W 2 {neighbor['target_ip']}", timeout=timeout)
            combined = "\n".join(part for part in [ping_result.stdout, ping_result.stderr] if part)
            passed = ping_result.returncode == 0 or _parse_ping_success(combined, neighbor["target_ip"])
            rows.append(
                "\t".join(
                    [
                        item["pod"],
                        item["asn"],
                        relation,
                        neighbor["target_ip"],
                        "pass" if passed else "fail",
                        neighbor["protocol"],
                        f"{item['pod']}->{neighbor['target_ip']}",
                    ]
                )
            )
            summary["checks_run"] += 1
            summary["checks_passed" if passed else "checks_failed"] += 1

    if summary["checks_run"] == 0:
        summary["failure_reason"] = "no_connectivity_checks_generated"
    elif summary["checks_failed"] > 0:
        summary["failure_reason"] = "connectivity_check_failed"

    summary["passed"] = summary["checks_run"] > 0 and summary["checks_failed"] == 0
    (artifact_dir / "connectivity_matrix.tsv").write_text("\n".join(rows) + "\n", encoding="utf-8")
    (artifact_dir / "connectivity_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")


def _write_failure_injection_summary(artifact_dir: Path) -> None:
    path = artifact_dir / "failure_injection_summary.json"
    if path.exists():
        return

    recovery = _load_json(artifact_dir / "recovery_check.json", {})
    if recovery:
        summary = {
            "generated_at": _now(),
            "executed": True,
            "status": "pass" if str(recovery.get("status", "")) == "recovered" else "fail",
            "injection_type": "delete_pod",
            "target": recovery.get("deployment", ""),
            "old_pod": recovery.get("old_pod", ""),
            "new_pod": recovery.get("new_pod", ""),
            "recovery_seconds": recovery.get("recovery_seconds", 0),
            "failure_reason": "" if str(recovery.get("status", "")) == "recovered" else "recovery_check_failed",
        }
    else:
        summary = {
            "generated_at": _now(),
            "executed": False,
            "status": "not_run",
            "injection_type": "",
            "failure_reason": "failure_injection_not_run",
        }
    path.write_text(json.dumps(summary, indent=2), encoding="utf-8")


def _write_resource_summary(namespace: str, artifact_dir: Path) -> None:
    nodes_json = _kubectl_json("", ["get", "nodes", "-o", "json"], timeout=30)
    pods_json = _kubectl_json(namespace, ["get", "pods", "-o", "json"], timeout=30)
    top_nodes = _parse_top_table(_kubectl("", ["top", "nodes"], timeout=30).stdout)
    top_pods = _parse_top_table(_kubectl(namespace, ["top", "pods"], timeout=30).stdout)
    top_nodes_by_name = {row.get("NAME", ""): row for row in top_nodes}
    top_pods_by_name = {row.get("NAME", ""): row for row in top_pods}

    total_restarts = 0
    running_pods = 0
    sample_pods: list[dict[str, Any]] = []
    for item in pods_json.get("items", []):
        metadata = item.get("metadata", {}) or {}
        status = item.get("status", {}) or {}
        name = str(metadata.get("name", ""))
        if str(status.get("phase", "")) == "Running":
            running_pods += 1
        total_restarts += sum(int(container.get("restartCount", 0)) for container in status.get("containerStatuses", []) or [])
        if len(sample_pods) < 10:
            top = top_pods_by_name.get(name, {})
            sample_pods.append(
                {
                    "name": name,
                    "node": str(item.get("spec", {}).get("nodeName", "")),
                    "cpu_used": top.get("CPU(cores)", ""),
                    "memory_used": top.get("MEMORY(bytes)", ""),
                    "phase": str(status.get("phase", "")),
                }
            )

    ready_nodes = 0
    node_samples: list[dict[str, Any]] = []
    for item in nodes_json.get("items", []):
        metadata = item.get("metadata", {}) or {}
        status = item.get("status", {}) or {}
        name = str(metadata.get("name", ""))
        ready = any(
            condition.get("type") == "Ready" and condition.get("status") == "True"
            for condition in status.get("conditions", []) or []
        )
        if ready:
            ready_nodes += 1
        top = top_nodes_by_name.get(name, {})
        node_samples.append(
            {
                "name": name,
                "ready": ready,
                "os_image": str((status.get("nodeInfo", {}) or {}).get("osImage", "")),
                "cpu_used": top.get("CPU(cores)", ""),
                "cpu_percent": top.get("CPU(%)", ""),
                "memory_used": top.get("MEMORY(bytes)", ""),
                "memory_percent": top.get("MEMORY(%)", ""),
            }
        )

    resource_summary = {
        "generated_at": _now(),
        "namespace": namespace,
        "top_available": bool(top_nodes) and bool(top_pods),
        "nodes_total": len(nodes_json.get("items", [])),
        "nodes_ready": ready_nodes,
        "pods_total": len(pods_json.get("items", [])),
        "pods_running": running_pods,
        "total_restarts": total_restarts,
        "node_samples": node_samples,
        "pod_samples": sample_pods,
    }
    (artifact_dir / "resource_summary.json").write_text(json.dumps(resource_summary, indent=2), encoding="utf-8")


def materialize(namespace: str, artifact_dir: Path, profile_id: str, sample_limit: int, timeout: int) -> int:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    _write_convergence_timeline(artifact_dir, profile_id)
    _write_protocol_health(artifact_dir)
    _write_placement_by_as(namespace, artifact_dir)
    _write_network_attachment_matrix(namespace, artifact_dir)
    _write_relationship_graph(namespace, artifact_dir)
    _write_failure_injection_summary(artifact_dir)
    _write_resource_summary(namespace, artifact_dir)
    _write_connectivity_matrix(namespace, artifact_dir, profile_id, sample_limit, timeout)
    return 0


def required_files_for_profile(profile_file: Path, profile_id: str) -> list[str]:
    if not profile_file.exists():
        return []
    loaded = yaml.safe_load(profile_file.read_text(encoding="utf-8")) or {}
    profiles = loaded.get("profiles", {}) if isinstance(loaded, dict) else {}
    profile = profiles.get(profile_id, {}) if isinstance(profiles, dict) else {}
    required = profile.get("validation_required_files", []) if isinstance(profile, dict) else []
    return [str(item) for item in required if isinstance(item, str)]


def assert_contract(artifact_dir: Path, required_files: list[str]) -> int:
    missing = [item for item in required_files if not (artifact_dir / item).exists()]
    status = {
        "generated_at": _now(),
        "artifact_dir": str(artifact_dir),
        "required_files": required_files,
        "missing_files": missing,
        "passed": len(missing) == 0,
    }
    (artifact_dir / "artifact_contract.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
    if missing:
        print("artifact_contract_failed")
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Materialize and assert SEED K8s validation artifact contract")
    subparsers = parser.add_subparsers(dest="cmd", required=True)

    materialize_parser = subparsers.add_parser("materialize")
    materialize_parser.add_argument("namespace")
    materialize_parser.add_argument("artifact_dir")
    materialize_parser.add_argument("profile_id")
    materialize_parser.add_argument("--sample-limit", type=int, default=3)
    materialize_parser.add_argument("--kubectl-timeout", type=int, default=20)

    assert_parser = subparsers.add_parser("assert")
    assert_parser.add_argument("artifact_dir")
    assert_parser.add_argument("--required", nargs="*", default=[])
    assert_parser.add_argument("--profile-file", default="")
    assert_parser.add_argument("--profile-id", default="")

    args = parser.parse_args()
    if args.cmd == "materialize":
        return materialize(args.namespace, Path(args.artifact_dir), args.profile_id, args.sample_limit, args.kubectl_timeout)

    required = list(args.required)
    if not required and args.profile_file and args.profile_id:
        required = required_files_for_profile(Path(args.profile_file), args.profile_id)
    return assert_contract(Path(args.artifact_dir), required)


if __name__ == "__main__":
    raise SystemExit(main())
