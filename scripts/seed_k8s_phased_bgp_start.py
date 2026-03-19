#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List

ROLE_SET = {"r", "brd", "rs"}
EXIT_BIRD_START_FAILED = 10
EXIT_IBGP_PHASE_FAILED = 20
EXIT_EBGP_PHASE_FAILED = 30
EXIT_NO_TARGETS = 40


@dataclass
class PodTarget:
    name: str
    asn: str
    role: str
    node: str


def run(cmd: List[str], *, timeout: int | None = None, check: bool = False) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(cmd, text=True, capture_output=True, timeout=timeout, check=check)
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        detail = stderr or f"command timed out after {timeout} seconds"
        return subprocess.CompletedProcess(cmd, 124, stdout, detail)


def kubectl(namespace: str, args: List[str], *, timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    return run(["kubectl", "-n", namespace, *args], timeout=timeout)


def kubectl_exec(namespace: str, pod: str, shell_cmd: str, *, timeout: int) -> subprocess.CompletedProcess[str]:
    return kubectl(namespace, ["exec", pod, "--", "sh", "-lc", shell_cmd], timeout=timeout)


def ensure_targets(namespace: str) -> List[PodTarget]:
    result = kubectl(namespace, ["get", "pods", "-o", "json"], timeout=60)
    result.check_returncode()
    data = json.loads(result.stdout)
    targets: List[PodTarget] = []
    for item in data.get("items", []):
        labels = (item.get("metadata", {}) or {}).get("labels", {}) or {}
        role = str(labels.get("seedemu.io/role", ""))
        if labels.get("seedemu.io/workload") != "seedemu":
            continue
        if role not in ROLE_SET:
            continue
        if str(item.get("status", {}).get("phase", "")) != "Running":
            continue
        targets.append(
            PodTarget(
                name=str(item["metadata"]["name"]),
                asn=str(labels.get("seedemu.io/asn", "")),
                role=role,
                node=str(item.get("spec", {}).get("nodeName", "")),
            )
        )
    targets.sort(key=lambda pod: (int(pod.asn or 0), pod.name))
    return targets


def bird_running(namespace: str, pod: str, exec_timeout: int) -> bool:
    result = kubectl_exec(namespace, pod, "birdc show status >/dev/null 2>&1", timeout=exec_timeout)
    return result.returncode == 0


def write_bird_status(path: Path, namespace: str, targets: List[PodTarget], exec_timeout: int) -> None:
    lines = ["pod\tasn\trole\tnode\tbird_running"]
    for target in targets:
        lines.append(
            f"{target.name}\t{target.asn}\t{target.role}\t{target.node}\t"
            f"{'true' if bird_running(namespace, target.name, exec_timeout) else 'false'}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_protocol_sample(path: Path, namespace: str, targets: List[PodTarget], exec_timeout: int, limit: int = 12) -> None:
    chunks: List[str] = []
    for target in targets[:limit]:
        result = kubectl_exec(namespace, target.name, "birdc show protocols", timeout=exec_timeout)
        chunks.append(f"=== {target.name} as{target.asn} role={target.role} node={target.node} rc={result.returncode} ===")
        if result.stdout:
            chunks.append(result.stdout.rstrip())
        if result.stderr:
            chunks.append(f"[stderr]\n{result.stderr.rstrip()}")
        chunks.append("")
    path.write_text("\n".join(chunks), encoding="utf-8")


def log(log_path: Path, message: str) -> None:
    stamped = f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}] {message}"
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(stamped + "\n")
    print(stamped)


def start_bird(namespace: str, targets: List[PodTarget], exec_timeout: int, log_path: Path) -> None:
    for target in targets:
        cmd = "pgrep -x bird >/dev/null 2>&1 || (bird -d >/tmp/seedemu-bird.log 2>&1 &)"
        kubectl_exec(namespace, target.name, cmd, timeout=exec_timeout)
    log(log_path, f"Phase 1: triggered bird start on {len(targets)} pods")


def wait_for_all_bird(namespace: str, targets: List[PodTarget], exec_timeout: int, timeout_seconds: int, log_path: Path) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        pending = [target.name for target in targets if not bird_running(namespace, target.name, exec_timeout)]
        if not pending:
            log(log_path, "Phase 1: all target pods respond to birdc show status")
            return True
        log(log_path, f"Phase 1: waiting for bird in {len(pending)} pods")
        time.sleep(5)
    return False


def broadcast_enable(namespace: str, targets: List[PodTarget], pattern: str, exec_timeout: int, log_path: Path) -> None:
    for target in targets:
        kubectl_exec(namespace, target.name, f"birdc 'enable {pattern}' >/dev/null 2>&1 || true", timeout=exec_timeout)
    log(log_path, f"Broadcasted birdc enable {pattern} to {len(targets)} pods")


def count_protocol_prefix(namespace: str, targets: List[PodTarget], prefix: str, exec_timeout: int) -> int:
    count = 0
    for target in targets:
        result = kubectl_exec(namespace, target.name, "birdc show protocols", timeout=exec_timeout)
        if result.returncode != 0:
            continue
        for line in result.stdout.splitlines():
            stripped = line.strip()
            if stripped.startswith(prefix):
                count += 1
    return count


def wait_for_protocol_visibility(namespace: str, targets: List[PodTarget], prefix: str, exec_timeout: int, timeout_seconds: int, log_path: Path) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        found = count_protocol_prefix(namespace, targets, prefix, exec_timeout)
        if found > 0:
            log(log_path, f"Phase check: found {found} protocol entries with prefix {prefix}")
            return True
        log(log_path, f"Phase check: still waiting for prefix {prefix}")
        time.sleep(5)
    return False


def patch_kernel_export(namespace: str, targets: List[PodTarget], exec_timeout: int, log_path: Path) -> None:
    enable_runtime_export = os.environ.get("SEED_K8S_RUNTIME_EXPORT_BGP_TO_KERNEL", "true").strip().lower()
    if enable_runtime_export not in {"1", "true", "yes", "on"}:
        log(log_path, "Runtime kernel-export patch disabled by SEED_K8S_RUNTIME_EXPORT_BGP_TO_KERNEL")
        return

    patched = 0
    patch_cmd = (
        "if [ -f /etc/bird/conf/kernel.conf ] && ! grep -q 'RTS_BGP' /etc/bird/conf/kernel.conf; then "
        "sed -i '/if source = RTS_OSPF then accept;/a\\            if source = RTS_BGP then accept;' /etc/bird/conf/kernel.conf && "
        "birdc configure >/dev/null 2>&1; "
        "fi"
    )
    for target in targets:
        result = kubectl_exec(namespace, target.name, patch_cmd, timeout=exec_timeout)
        if result.returncode == 0:
            patched += 1
    log(log_path, f"Runtime kernel-export patch applied on {patched} pods")
    time.sleep(3)


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: scripts/seed_k8s_phased_bgp_start.py <namespace> <artifact_dir>", file=sys.stderr)
        return 2

    namespace = sys.argv[1]
    artifact_dir = Path(sys.argv[2])
    artifact_dir.mkdir(parents=True, exist_ok=True)

    exec_timeout = int(os.environ.get("SEED_KUBECTL_EXEC_TIMEOUT_SECONDS", "20"))
    phase_timeout = int(os.environ.get("SEED_BGP_PHASE_TIMEOUT_SECONDS", "300"))
    startup_mode = os.environ.get("SEED_BGP_STARTUP_MODE", "phased").strip().lower() or "phased"

    log_path = artifact_dir / "phased_startup.log"
    targets = ensure_targets(namespace)
    (artifact_dir / "phase_targets.json").write_text(
        json.dumps([target.__dict__ for target in targets], indent=2),
        encoding="utf-8",
    )

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "namespace": namespace,
        "bird_autostart": False,
        "bgp_startup_mode": startup_mode,
        "targets": len(targets),
        "status": "PASS",
        "failure_reason": "",
    }

    if not targets:
        summary["status"] = "FAIL"
        summary["failure_reason"] = "no_router_like_pods_found"
        (artifact_dir / "phased_startup_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return EXIT_NO_TARGETS

    write_bird_status(artifact_dir / "bird_before_phase.txt", namespace, targets, exec_timeout)

    if startup_mode != "phased":
        log(log_path, f"SEED_BGP_STARTUP_MODE={startup_mode}; skip phased startup helper")
        write_protocol_sample(artifact_dir / "bird_after_phase.txt", namespace, targets, exec_timeout)
        (artifact_dir / "phased_startup_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return 0

    start_bird(namespace, targets, exec_timeout, log_path)
    if not wait_for_all_bird(namespace, targets, exec_timeout, phase_timeout, log_path):
        summary["status"] = "FAIL"
        summary["failure_reason"] = "bird_not_started"
        write_bird_status(artifact_dir / "bird_after_phase.txt", namespace, targets, exec_timeout)
        (artifact_dir / "phased_startup_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return EXIT_BIRD_START_FAILED

    broadcast_enable(namespace, targets, "Ibgp*", exec_timeout, log_path)
    if not wait_for_protocol_visibility(namespace, targets, "Ibgp", exec_timeout, phase_timeout, log_path):
        summary["status"] = "FAIL"
        summary["failure_reason"] = "ibgp_phase_failed"
        write_protocol_sample(artifact_dir / "bird_after_phase.txt", namespace, targets, exec_timeout)
        (artifact_dir / "phased_startup_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return EXIT_IBGP_PHASE_FAILED

    broadcast_enable(namespace, targets, "Ebgp*", exec_timeout, log_path)
    if not wait_for_protocol_visibility(namespace, targets, "Ebgp", exec_timeout, phase_timeout, log_path):
        summary["status"] = "FAIL"
        summary["failure_reason"] = "ebgp_phase_failed"
        write_protocol_sample(artifact_dir / "bird_after_phase.txt", namespace, targets, exec_timeout)
        (artifact_dir / "phased_startup_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return EXIT_EBGP_PHASE_FAILED

    patch_kernel_export(namespace, targets, exec_timeout, log_path)
    write_protocol_sample(artifact_dir / "bird_after_phase.txt", namespace, targets, exec_timeout)
    (artifact_dir / "phased_startup_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
