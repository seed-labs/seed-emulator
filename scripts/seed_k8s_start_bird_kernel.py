#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import random
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List

EXIT_KERNEL_SWITCH_FAILED = 41


@dataclass
class RouterTarget:
    name: str
    asn: str
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


def router_targets(namespace: str) -> List[RouterTarget]:
    result = kubectl(namespace, ["get", "pods", "-o", "json"], timeout=60)
    result.check_returncode()
    data = json.loads(result.stdout)
    targets: List[RouterTarget] = []
    for item in data.get("items", []):
        labels = (item.get("metadata", {}) or {}).get("labels", {}) or {}
        if labels.get("seedemu.io/workload") != "seedemu":
            continue
        if str(item.get("status", {}).get("phase", "")) != "Running":
            continue
        name_label = str(labels.get("seedemu.io/name", ""))
        if not name_label.startswith("r"):
            continue
        targets.append(
            RouterTarget(
                name=str(item["metadata"]["name"]),
                asn=str(labels.get("seedemu.io/asn", "")),
                node=str(item.get("spec", {}).get("nodeName", "")),
            )
        )
    targets.sort(key=lambda pod: (int(pod.asn or 0), pod.name))
    return targets


def kernel_config(export_mode: str) -> str:
    scan_base = int(os.environ.get("SEED_KERNEL_SCAN_BASE_SECONDS", "6000"))
    scan_jitter = int(os.environ.get("SEED_KERNEL_SCAN_JITTER_SECONDS", "120"))
    interval = scan_base + random.randint(0, max(scan_jitter, 0))
    if export_mode == "device_ospf_only":
        return f'''protocol kernel {{
    merge paths on;
    persist;
    scan time {interval};
    ipv4 {{
        import none;
        export filter {{
            if source = RTS_DEVICE then accept;
            if source = RTS_OSPF then accept;
            reject;
        }};
    }};
}}
'''
    return f'''protocol kernel {{
    merge paths on;
    persist;
    scan time {interval};
    ipv4 {{
        import none;
        export all;
    }};
}}
'''


def expected_marker(export_mode: str) -> str:
    if export_mode == "device_ospf_only":
        return "if source = RTS_OSPF then accept;"
    return "export all;"


def kernel_conf_matches(namespace: str, pod: str, marker: str, exec_timeout: int) -> bool:
    result = kubectl_exec(namespace, pod, "cat /etc/bird/conf/kernel.conf", timeout=exec_timeout)
    return result.returncode == 0 and marker in result.stdout


def bird_healthy(namespace: str, pod: str, exec_timeout: int, birdc_timeout: int) -> bool:
    result = kubectl_exec(
        namespace,
        pod,
        f"pgrep -x bird >/dev/null 2>&1 && timeout {birdc_timeout} birdc show status >/dev/null 2>&1",
        timeout=exec_timeout,
    )
    return result.returncode == 0


def write_kernel_conf(namespace: str, pod: str, content: str, exec_timeout: int, birdc_timeout: int) -> subprocess.CompletedProcess[str]:
    payload = content.replace("'", "'\"'\"'")
    write_cmd = (
        "cat <<'EOF' > /etc/bird/conf/kernel.conf\n"
        f"{payload}"
        "EOF\n"
    )
    write_result = kubectl_exec(namespace, pod, write_cmd, timeout=exec_timeout)
    if write_result.returncode != 0:
        return write_result
    reload_cmd = (
        f"timeout {birdc_timeout} birdc configure >/dev/null 2>&1 && "
        f"timeout {birdc_timeout} birdc 'reload kernel' >/dev/null 2>&1 || true"
    )
    return kubectl_exec(namespace, pod, reload_cmd, timeout=exec_timeout)


def sample_kernel_conf(namespace: str, pod: str, exec_timeout: int) -> str:
    result = kubectl_exec(namespace, pod, "cat /etc/bird/conf/kernel.conf", timeout=exec_timeout)
    return result.stdout if result.returncode == 0 else result.stderr


def apply_kernel_conf(
    namespace: str,
    target: RouterTarget,
    export_mode: str,
    exec_timeout: int,
    birdc_timeout: int,
    retries: int,
    retry_backoff: float,
) -> tuple[bool, str]:
    marker = expected_marker(export_mode)
    last_error = ""
    for attempt in range(1, retries + 1):
        config = kernel_config(export_mode)
        result = write_kernel_conf(namespace, target.name, config, exec_timeout, birdc_timeout)
        if result.returncode == 0:
            return True, ""
        last_error = (result.stderr or result.stdout).strip() or f"kernel update failed with rc={result.returncode}"
        if kernel_conf_matches(namespace, target.name, marker, exec_timeout) and bird_healthy(namespace, target.name, exec_timeout, birdc_timeout):
            return True, "timeout_but_config_applied"
        if retry_backoff > 0 and attempt < retries:
            time.sleep(retry_backoff)
    return False, last_error


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: scripts/seed_k8s_start_bird_kernel.py <namespace> <artifact_dir>", file=sys.stderr)
        return 2

    namespace = sys.argv[1]
    artifact_dir = Path(sys.argv[2])
    artifact_dir.mkdir(parents=True, exist_ok=True)

    base_exec_timeout = int(os.environ.get("SEED_KUBECTL_EXEC_TIMEOUT_SECONDS", "20"))
    exec_timeout = int(os.environ.get("SEED_KERNEL_EXEC_TIMEOUT_SECONDS", str(max(base_exec_timeout, 45))))
    birdc_timeout = int(os.environ.get("SEED_KERNEL_BIRDC_TIMEOUT_SECONDS", "10"))
    export_mode = os.environ.get("SEED_KERNEL_EXPORT_MODE", "all").strip().lower() or "all"
    interval_seconds = float(os.environ.get("SEED_KERNEL_SWITCH_INTERVAL_SECONDS", "0.05"))
    retries = max(1, int(os.environ.get("SEED_KERNEL_SWITCH_RETRIES", "3")))
    retry_backoff = float(os.environ.get("SEED_KERNEL_SWITCH_RETRY_BACKOFF_SECONDS", "2"))
    parallelism = max(1, int(os.environ.get("SEED_KERNEL_SWITCH_PARALLELISM", "8")))
    log_path = artifact_dir / "bird_kernel.log"

    targets = router_targets(namespace)
    (artifact_dir / "bird_kernel_targets.json").write_text(
        json.dumps([asdict(target) for target in targets], indent=2),
        encoding="utf-8",
    )

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "namespace": namespace,
        "targets": len(targets),
        "kernel_export_mode": export_mode,
        "status": "PASS",
        "failure_reason": "",
        "retries": retries,
        "parallelism": parallelism,
    }

    if not targets:
        summary["status"] = "FAIL"
        summary["failure_reason"] = "no_router_pods_found"
        (artifact_dir / "bird_kernel_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return EXIT_KERNEL_SWITCH_FAILED

    processed = 0
    failures: list[dict[str, str]] = []
    with ThreadPoolExecutor(max_workers=parallelism) as pool:
        future_map = {}
        for target in targets:
            future_map[pool.submit(apply_kernel_conf, namespace, target, export_mode, exec_timeout, birdc_timeout, retries, retry_backoff)] = target
            if interval_seconds > 0:
                time.sleep(interval_seconds)
        for future in as_completed(future_map):
            target = future_map[future]
            ok, detail = future.result()
            if ok:
                processed += 1
                suffix = "" if not detail else f" ({detail})"
                log(log_path, f"kernel switch: updated {target.name} on {target.node}{suffix}")
            else:
                failures.append({"pod": target.name, "stderr": detail})
                log(log_path, f"kernel switch: failed on {target.name}: {detail}")

    summary["processed"] = processed
    summary["failures"] = failures
    if failures:
        summary["status"] = "FAIL"
        summary["failure_reason"] = "kernel_switch_failed"

    if targets:
        (artifact_dir / "bird_kernel_sample.conf").write_text(
            sample_kernel_conf(namespace, targets[0].name, exec_timeout),
            encoding="utf-8",
        )
    (artifact_dir / "bird_kernel_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if not failures else EXIT_KERNEL_SWITCH_FAILED


if __name__ == "__main__":
    raise SystemExit(main())
