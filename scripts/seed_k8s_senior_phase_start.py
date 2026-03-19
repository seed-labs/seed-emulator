#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List

EXIT_BIRD_START_FAILED = 10
EXIT_IBGP_PHASE_FAILED = 20
EXIT_EBGP_PHASE_FAILED = 30
EXIT_KERNEL_SWITCH_FAILED = 41

ROLE_SET = {"r", "brd", "rs"}


@dataclass
class PodTarget:
    name: str
    asn: str
    role: str
    node: str


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
    result = kubectl_exec(
        namespace,
        pod,
        "pgrep -x bird >/dev/null 2>&1 && timeout 5 birdc show status >/dev/null 2>&1",
        timeout=exec_timeout,
    )
    return result.returncode == 0


def write_bird_status(path: Path, namespace: str, targets: List[PodTarget], exec_timeout: int, parallelism: int) -> None:
    lines = ["pod\tasn\trole\tnode\tbird_running"]
    with ThreadPoolExecutor(max_workers=max(1, parallelism)) as pool:
        future_map = {pool.submit(bird_running, namespace, target.name, exec_timeout): target for target in targets}
        results = {}
        for future in as_completed(future_map):
            target = future_map[future]
            results[target.name] = bool(future.result())
    for target in targets:
        lines.append(
            f"{target.name}\t{target.asn}\t{target.role}\t{target.node}\t"
            f"{'true' if results.get(target.name, False) else 'false'}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def fetch_protocol_sample(namespace: str, target: PodTarget, exec_timeout: int) -> str:
    result = kubectl_exec(namespace, target.name, "timeout 8 birdc show protocols", timeout=exec_timeout)
    chunks = [f"=== {target.name} as{target.asn} role={target.role} node={target.node} rc={result.returncode} ==="]
    if result.stdout:
        chunks.append(result.stdout.rstrip())
    if result.stderr:
        chunks.append(f"[stderr]\n{result.stderr.rstrip()}")
    chunks.append("")
    return "\n".join(chunks)


def write_protocol_sample(
    path: Path,
    namespace: str,
    targets: List[PodTarget],
    exec_timeout: int,
    parallelism: int,
    limit: int = 12,
) -> None:
    selected = targets[:limit]
    chunks = [""] * len(selected)
    with ThreadPoolExecutor(max_workers=max(1, parallelism)) as pool:
        future_map = {pool.submit(fetch_protocol_sample, namespace, target, exec_timeout): idx for idx, target in enumerate(selected)}
        for future in as_completed(future_map):
            chunks[future_map[future]] = future.result()
    path.write_text("\n".join(chunks), encoding="utf-8")


def log(log_path: Path, message: str) -> None:
    stamped = f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}] {message}"
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(stamped + "\n")
    print(stamped)


def child_log(log_path: Path, prefix: str, result: subprocess.CompletedProcess[str]) -> None:
    if result.stdout:
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(f"[{prefix} stdout]\n{result.stdout.rstrip()}\n")
    if result.stderr:
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(f"[{prefix} stderr]\n{result.stderr.rstrip()}\n")


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: scripts/seed_k8s_senior_phase_start.py <namespace> <artifact_dir>", file=sys.stderr)
        return 2

    namespace = sys.argv[1]
    artifact_dir = Path(sys.argv[2])
    artifact_dir.mkdir(parents=True, exist_ok=True)

    exec_timeout = int(os.environ.get("SEED_KUBECTL_EXEC_TIMEOUT_SECONDS", "20"))
    settle_seconds = int(os.environ.get("SEED_SENIOR_BIRD_SETTLE_SECONDS", "60"))
    status_parallelism = max(1, int(os.environ.get("SEED_PHASE_STATUS_PARALLELISM", "12")))
    protocol_parallelism = max(1, int(os.environ.get("SEED_PHASE_PROTOCOL_PARALLELISM", "6")))
    log_path = artifact_dir / "phased_startup.log"

    targets = ensure_targets(namespace)
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "namespace": namespace,
        "bird_autostart": False,
        "bgp_startup_mode": "senior_pair",
        "phase_start_driver": "seed_k8s_senior_phase_start.py",
        "start_bird_driver": "seed_k8s_start_bird0130.py",
        "kernel_driver": "seed_k8s_start_bird_kernel.py",
        "targets": len(targets),
        "status": "PASS",
        "failure_reason": "",
        "status_parallelism": status_parallelism,
        "protocol_parallelism": protocol_parallelism,
    }

    if not targets:
        summary["status"] = "FAIL"
        summary["failure_reason"] = "no_router_like_pods_found"
        (artifact_dir / "phased_startup_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return EXIT_BIRD_START_FAILED

    write_bird_status(artifact_dir / "bird_before_phase.txt", namespace, targets, exec_timeout, status_parallelism)

    start_script = Path(__file__).with_name("seed_k8s_start_bird0130.py")
    kernel_script = Path(__file__).with_name("seed_k8s_start_bird_kernel.py")

    result = run([sys.executable, str(start_script), namespace, str(artifact_dir)], timeout=None)
    child_log(log_path, "start_bird0130", result)
    if result.returncode != 0:
        summary["status"] = "FAIL"
        summary["failure_reason"] = "bird_not_started"
        (artifact_dir / "phased_startup_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return EXIT_BIRD_START_FAILED
    log(log_path, f"senior phase-start: start_bird0130 finished, settle {settle_seconds}s")

    if settle_seconds > 0:
        time.sleep(settle_seconds)

    result = run([sys.executable, str(kernel_script), namespace, str(artifact_dir)], timeout=None)
    child_log(log_path, "start_bird_kernel", result)
    if result.returncode != 0:
        summary["status"] = "FAIL"
        summary["failure_reason"] = "kernel_switch_failed"
        (artifact_dir / "phased_startup_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return EXIT_KERNEL_SWITCH_FAILED

    write_protocol_sample(
        artifact_dir / "bird_after_phase.txt",
        namespace,
        targets,
        exec_timeout,
        protocol_parallelism,
    )
    (artifact_dir / "phased_startup_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
