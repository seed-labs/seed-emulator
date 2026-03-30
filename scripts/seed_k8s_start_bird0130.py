#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Dict

ROLE_SET = {"r", "brd", "rs"}
EXIT_BIRD_START_FAILED = 10
START_DELAY = 0.05
SYSTEM_LOAD_THRESHOLD = 10.0
LOAD_CHECK_INTERVAL = 10

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

def log(log_paths: Iterable[Path], message: str) -> None:
    stamped = f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}] {message}"
    for log_path in log_paths:
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(stamped + "\n")
    print(stamped)


def write_summary_files(artifact_dir: Path, payload: dict) -> None:
    content = json.dumps(payload, indent=2)
    for name in ("start_bird_summary.json", "bird0130_summary.json"):
        (artifact_dir / name).write_text(content, encoding="utf-8")

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

def start_birds_on_node(
    node_name: str,
    namespace: str,
    node_targets: List[PodTarget],
    exec_timeout: int,
    retries: int,
    retry_backoff: float,
    log_paths: Iterable[Path],
) -> tuple[int, list[tuple[str, str]]]:
    """Start BIRD sequentially within one Kubernetes node."""
    failures = []
    started = 0
    total = len(node_targets)
    
    for target in node_targets:
        success = False
        last_error = ""
        for attempt in range(1, retries + 1):
            result = start_bird_once(namespace, target, exec_timeout)
            if result.returncode == 0:
                success = True
                break
            last_error = (result.stderr or result.stdout).strip() or f"rc={result.returncode}"
            if retry_backoff > 0 and attempt < retries:
                time.sleep(retry_backoff)
                
        if success:
            started += 1
        else:
            failures.append((target.name, last_error))
            
        time.sleep(START_DELAY)

    log(log_paths, f"Node {node_name}: started {started}/{total} pods.")
    return started, failures

def get_node_load(namespace: str, pod_name: str, exec_timeout: int) -> float:
    """Read the host load average through a pod."""
    result = kubectl_exec(namespace, pod_name, "cat /proc/loadavg", timeout=exec_timeout)
    if result.returncode == 0:
        try:
            return float(result.stdout.split()[0])
        except (IndexError, ValueError):
            pass
    return -1.0

def wait_for_cluster_idle(
    namespace: str,
    nodes_map: Dict[str, List[PodTarget]],
    log_paths: Iterable[Path],
    exec_timeout: int,
) -> None:
    """Wait until the load-based convergence signal is quiet on every node."""
    probe_pods = {node: pods[0].name for node, pods in nodes_map.items() if pods}

    log(log_paths, f"Waiting for BGP convergence (load < {SYSTEM_LOAD_THRESHOLD}) across {len(probe_pods)} nodes.")

    while True:
        all_idle = True
        status_strs = []

        for node, probe_pod in probe_pods.items():
            load = get_node_load(namespace, probe_pod, exec_timeout)
            if load >= 0:
                symbol = "OK" if load < SYSTEM_LOAD_THRESHOLD else "BUSY"
                status_strs.append(f"{node}: {load:.2f} {symbol}")
                if load >= SYSTEM_LOAD_THRESHOLD:
                    all_idle = False
            else:
                status_strs.append(f"{node}: ERROR")
                all_idle = False

        sys.stdout.write("\r [Load Check] " + " | ".join(status_strs) + f" (Target: <{SYSTEM_LOAD_THRESHOLD}) ")
        sys.stdout.flush()

        if all_idle:
            print("")
            log(log_paths, "All cluster nodes stabilized: " + ", ".join(status_strs))
            break

        time.sleep(LOAD_CHECK_INTERVAL)

def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: scripts/seed_k8s_start_bird0130.py <namespace> <artifact_dir>", file=sys.stderr)
        return 2

    namespace = sys.argv[1]
    artifact_dir = Path(sys.argv[2])
    artifact_dir.mkdir(parents=True, exist_ok=True)

    base_exec_timeout = int(os.environ.get("SEED_KUBECTL_EXEC_TIMEOUT_SECONDS", "30"))
    exec_timeout = int(os.environ.get("SEED_BIRD_START_EXEC_TIMEOUT_SECONDS", str(max(base_exec_timeout, 45))))
    phase_timeout = int(os.environ.get("SEED_BIRD_PHASE_TIMEOUT_SECONDS", "1200"))
    retries = max(1, int(os.environ.get("SEED_BIRD_START_RETRIES", "2")))
    retry_backoff = float(os.environ.get("SEED_BIRD_START_RETRY_BACKOFF_SECONDS", "1"))

    log_paths = [artifact_dir / "start_bird.log", artifact_dir / "bird0130.log"]

    total_start_time = time.time()
    log(log_paths, "=== K8s BIRD start stage (node-aware concurrency) ===")

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
        "strategy": "node-aware-concurrency",
        "duration_seconds": 0,
    }

    if not targets:
        summary["status"] = "FAIL"
        summary["failure_reason"] = "no_router_like_pods_found"
        write_summary_files(artifact_dir, summary)
        return EXIT_BIRD_START_FAILED

    nodes_map = defaultdict(list)
    for t in targets:
        nodes_map[t.node].append(t)

    log(log_paths, f"Grouped {len(targets)} targets into {len(nodes_map)} nodes.")
    for node, pods in nodes_map.items():
        log(log_paths, f"Node {node}: {len(pods)} pods")

    all_start_failures = []
    total_started = 0

    with ThreadPoolExecutor(max_workers=len(nodes_map)) as pool:
        future_to_node = {
            pool.submit(
                start_birds_on_node,
                node, namespace, pods, exec_timeout, retries, retry_backoff, log_paths
            ): node for node, pods in nodes_map.items()
        }

        for future in as_completed(future_to_node):
            node_name = future_to_node[future]
            try:
                started, failures = future.result()
                total_started += started
                all_start_failures.extend(failures)
            except Exception as exc:
                log(log_paths, f"Node {node_name} raised an exception: {exc}")
                all_start_failures.append((f"Node_{node_name}", str(exc)))

    if all_start_failures:
        summary["status"] = "FAIL"
        summary["failure_reason"] = "bird_start_command_failed"
        summary["failures"] = [{"pod": pod, "stderr": detail} for pod, detail in all_start_failures]
        summary["duration_seconds"] = round(time.time() - total_start_time, 3)
        write_summary_files(artifact_dir, summary)
        return EXIT_BIRD_START_FAILED

    log(log_paths, "Waiting 20 seconds before the first load check.")
    time.sleep(20)
    wait_for_cluster_idle(namespace, nodes_map, log_paths, exec_timeout)

    deadline = time.time() + phase_timeout
    all_healthy = False
    while time.time() < deadline:
        pending = []
        for target in targets:
            if not bird_running(namespace, target.name, exec_timeout):
                pending.append(target.name)

        if not pending:
            log(log_paths, "All target pods respond to `birdc show status`.")
            all_healthy = True
            break
        log(log_paths, f"Waiting for BIRD readiness in {len(pending)} pods.")
        time.sleep(10)

    if not all_healthy:
        summary["status"] = "FAIL"
        summary["failure_reason"] = "bird_not_started"
        summary["duration_seconds"] = round(time.time() - total_start_time, 3)
        write_summary_files(artifact_dir, summary)
        return EXIT_BIRD_START_FAILED

    total_duration = time.time() - total_start_time
    summary["duration_seconds"] = round(total_duration, 3)
    summary["started"] = total_started
    write_summary_files(artifact_dir, summary)
    log(log_paths, f"BIRD start stage completed in {total_duration:.2f}s.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
