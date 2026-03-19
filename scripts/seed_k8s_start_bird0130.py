#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List

ROLE_SET = {"r", "brd", "rs"}
EXIT_BIRD_START_FAILED = 10


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


def log(log_path: Path, message: str) -> None:
    stamped = f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}] {message}"
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(stamped + "\n")
    print(stamped)


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
                name=str(item["metadata"]["name"]),
                asn=str(labels.get("seedemu.io/asn", "")),
                role=role,
                node=str(item.get("spec", {}).get("nodeName", "")),
            )
        )
    targets.sort(key=lambda pod: (int(pod.asn or 0), pod.name))
    return targets


def bird_running(namespace: str, pod: str, exec_timeout: int) -> bool:
    check_cmd = (
        "pgrep -x bird >/dev/null 2>&1 && "
        "timeout 5 birdc show status >/dev/null 2>&1"
    )
    result = kubectl_exec(namespace, pod, check_cmd, timeout=exec_timeout)
    return result.returncode == 0


def write_status(path: Path, namespace: str, targets: Iterable[PodTarget], exec_timeout: int, parallelism: int) -> None:
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


def start_bird_once(namespace: str, target: PodTarget, exec_timeout: int) -> subprocess.CompletedProcess[str]:
    cleanup = (
        "rm -f /run/bird/bird.ctl /run/bird/bird.pid /var/run/bird.ctl /var/run/bird.pid "
        "/run/bird/*.ctl /run/bird/*.pid /var/run/bird/*.ctl /var/run/bird/*.pid 2>/dev/null || true"
    )
    shell_cmd = f"""
if pgrep -x bird >/dev/null 2>&1; then
    exit 0
fi
{cleanup}
bird >/tmp/seedemu-bird.log 2>&1 || (bird -d >/tmp/seedemu-bird.log 2>&1 & sleep 1)
"""
    return kubectl_exec(namespace, target.name, shell_cmd, timeout=exec_timeout)


def start_target(
    namespace: str,
    target: PodTarget,
    exec_timeout: int,
    retries: int,
    retry_backoff: float,
) -> tuple[bool, str]:
    last_error = ""
    for attempt in range(1, retries + 1):
        result = start_bird_once(namespace, target, exec_timeout)
        if result.returncode == 0:
            return True, ""
        last_error = (result.stderr or result.stdout).strip() or f"bird start failed with rc={result.returncode}"
        if retry_backoff > 0 and attempt < retries:
            time.sleep(retry_backoff)
    return False, last_error


def start_all_birds(
    namespace: str,
    targets: List[PodTarget],
    exec_timeout: int,
    start_delay: float,
    retries: int,
    retry_backoff: float,
    parallelism: int,
    log_path: Path,
) -> list[tuple[str, str]]:
    failures: list[tuple[str, str]] = []
    started = 0
    with ThreadPoolExecutor(max_workers=max(1, parallelism)) as pool:
        future_map = {}
        for target in targets:
            future_map[pool.submit(start_target, namespace, target, exec_timeout, retries, retry_backoff)] = target
            if start_delay > 0:
                time.sleep(start_delay)
        for future in as_completed(future_map):
            target = future_map[future]
            ok, detail = future.result()
            if ok:
                started += 1
            else:
                failures.append((target.name, detail))
    for pod_name, detail in failures:
        log(log_path, f"start_bird0130: failed on {pod_name}: {detail}")
    log(log_path, f"start_bird0130: triggered bird start on {started} pods")
    return failures


def pending_birds(namespace: str, targets: List[PodTarget], exec_timeout: int, parallelism: int) -> list[str]:
    with ThreadPoolExecutor(max_workers=max(1, parallelism)) as pool:
        future_map = {pool.submit(bird_running, namespace, target.name, exec_timeout): target for target in targets}
        pending = []
        for future in as_completed(future_map):
            target = future_map[future]
            if not future.result():
                pending.append(target.name)
    pending.sort()
    return pending


def wait_for_all_bird(
    namespace: str,
    targets: List[PodTarget],
    exec_timeout: int,
    timeout_seconds: int,
    parallelism: int,
    log_path: Path,
) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        pending = pending_birds(namespace, targets, exec_timeout, parallelism)
        if not pending:
            log(log_path, "start_bird0130: all target pods respond to birdc show status")
            return True
        log(log_path, f"start_bird0130: waiting for bird in {len(pending)} pods")
        time.sleep(5)
    return False


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: scripts/seed_k8s_start_bird0130.py <namespace> <artifact_dir>", file=sys.stderr)
        return 2

    namespace = sys.argv[1]
    artifact_dir = Path(sys.argv[2])
    artifact_dir.mkdir(parents=True, exist_ok=True)

    base_exec_timeout = int(os.environ.get("SEED_KUBECTL_EXEC_TIMEOUT_SECONDS", "20"))
    exec_timeout = int(os.environ.get("SEED_BIRD_START_EXEC_TIMEOUT_SECONDS", str(max(base_exec_timeout, 45))))
    phase_timeout = int(os.environ.get("SEED_BIRD_PHASE_TIMEOUT_SECONDS", "600"))
    start_delay = float(os.environ.get("SEED_BIRD_START_DELAY_SECONDS", "0.02"))
    retries = max(1, int(os.environ.get("SEED_BIRD_START_RETRIES", "2")))
    retry_backoff = float(os.environ.get("SEED_BIRD_START_RETRY_BACKOFF_SECONDS", "1"))
    start_parallelism = max(1, int(os.environ.get("SEED_BIRD_START_PARALLELISM", "12")))
    status_parallelism = max(1, int(os.environ.get("SEED_BIRD_STATUS_PARALLELISM", str(start_parallelism))))

    log_path = artifact_dir / "bird0130.log"
    targets = ensure_targets(namespace)
    (artifact_dir / "bird0130_targets.json").write_text(
        json.dumps([asdict(target) for target in targets], indent=2),
        encoding="utf-8",
    )

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "namespace": namespace,
        "targets": len(targets),
        "status": "PASS",
        "failure_reason": "",
        "start_retries": retries,
        "start_parallelism": start_parallelism,
        "status_parallelism": status_parallelism,
    }

    if not targets:
        summary["status"] = "FAIL"
        summary["failure_reason"] = "no_router_like_pods_found"
        (artifact_dir / "bird0130_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return EXIT_BIRD_START_FAILED

    start_failures = start_all_birds(
        namespace,
        targets,
        exec_timeout,
        start_delay,
        retries,
        retry_backoff,
        start_parallelism,
        log_path,
    )
    if start_failures:
        summary["status"] = "FAIL"
        summary["failure_reason"] = "bird_start_command_failed"
        summary["failures"] = [{"pod": pod, "stderr": detail} for pod, detail in start_failures]
        write_status(artifact_dir / "bird0130_status.tsv", namespace, targets, exec_timeout, status_parallelism)
        (artifact_dir / "bird0130_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return EXIT_BIRD_START_FAILED

    if not wait_for_all_bird(namespace, targets, exec_timeout, phase_timeout, status_parallelism, log_path):
        summary["status"] = "FAIL"
        summary["failure_reason"] = "bird_not_started"
        write_status(artifact_dir / "bird0130_status.tsv", namespace, targets, exec_timeout, status_parallelism)
        (artifact_dir / "bird0130_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return EXIT_BIRD_START_FAILED

    write_status(artifact_dir / "bird0130_status.tsv", namespace, targets, exec_timeout, status_parallelism)
    (artifact_dir / "bird0130_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
