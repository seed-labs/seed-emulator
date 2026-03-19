#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROLE_PREFERENCE = {"r": 0, "brd": 1, "rs": 2}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run(
    cmd: list[str],
    timeout: int | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(cmd, text=True, capture_output=True, timeout=timeout, env=env)
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        return subprocess.CompletedProcess(cmd, 124, stdout, stderr or "timeout")


def _kubectl(namespace: str, args: list[str], timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    return _run(["kubectl", "-n", namespace, *args], timeout=timeout)


def _kubectl_json(namespace: str, args: list[str], timeout: int | None = None) -> dict[str, Any]:
    result = _kubectl(namespace, args, timeout=timeout)
    if result.returncode != 0:
        return {}
    try:
        loaded = json.loads(result.stdout)
    except Exception:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _kubectl_exec(namespace: str, pod: str, command: str, timeout: int) -> subprocess.CompletedProcess[str]:
    return _kubectl(namespace, ["exec", pod, "--", "sh", "-lc", command], timeout=timeout)


def _pick_target(namespace: str) -> dict[str, str] | None:
    pods = _kubectl_json(namespace, ["get", "pods", "-o", "json"], timeout=60)
    candidates: list[dict[str, str]] = []
    for item in pods.get("items", []):
        labels = (item.get("metadata", {}) or {}).get("labels", {}) or {}
        if labels.get("seedemu.io/workload") != "seedemu":
            continue
        role = str(labels.get("seedemu.io/role", ""))
        if role not in ROLE_PREFERENCE:
            continue
        logical_name = str(labels.get("seedemu.io/name", ""))
        if not logical_name.startswith("r"):
            continue
        if str(item.get("status", {}).get("phase", "")) != "Running":
            continue
        deployment = str(labels.get("app", ""))
        if not deployment:
            continue
        candidates.append(
            {
                "pod": str(item.get("metadata", {}).get("name", "")),
                "asn": str(labels.get("seedemu.io/asn", "")),
                "role": role,
                "logical_name": logical_name,
                "deployment": deployment,
            }
        )
    if not candidates:
        return None
    candidates.sort(key=lambda item: (int(item["asn"] or 0), ROLE_PREFERENCE.get(item["role"], 99), item["pod"]))
    return candidates[0]


def _protocol_recovered(namespace: str, pod: str, timeout: int) -> tuple[bool, str]:
    result = _kubectl_exec(namespace, pod, "birdc show protocols", timeout=timeout)
    raw = "\n".join(chunk for chunk in [result.stdout, result.stderr] if chunk).strip()
    has_established = "Established" in raw
    has_ospf = bool(re.search(r"\bOSPF\b.*\bRunning\b", raw))
    return (result.returncode == 0 and (has_established or has_ospf)), raw


def _run_recovery_phase(namespace: str, artifact_dir: Path, timeout_seconds: int) -> tuple[bool, str]:
    env = os.environ.copy()
    env.setdefault("SEED_BIRD_PHASE_TIMEOUT_SECONDS", str(timeout_seconds))
    env.setdefault("SEED_SENIOR_BIRD_SETTLE_SECONDS", "10")

    start_script = Path(__file__).with_name("seed_k8s_start_bird0130.py")
    kernel_script = Path(__file__).with_name("seed_k8s_start_bird_kernel.py")

    start_result = _run(
        [sys.executable, str(start_script), namespace, str(artifact_dir)],
        timeout=timeout_seconds + 60,
        env=env,
    )
    kernel_result = _run(
        [sys.executable, str(kernel_script), namespace, str(artifact_dir)],
        timeout=timeout_seconds + 60,
        env=env,
    )

    raw = "\n".join(
        chunk
        for chunk in [
            "[start_bird0130 stdout]\n" + start_result.stdout if start_result.stdout else "",
            "[start_bird0130 stderr]\n" + start_result.stderr if start_result.stderr else "",
            "[start_bird_kernel stdout]\n" + kernel_result.stdout if kernel_result.stdout else "",
            "[start_bird_kernel stderr]\n" + kernel_result.stderr if kernel_result.stderr else "",
        ]
        if chunk
    ).strip()
    return (start_result.returncode == 0 and kernel_result.returncode == 0), raw


def main() -> int:
    parser = argparse.ArgumentParser(description="Run sampled pod-failure injection for SEED K8s namespace")
    parser.add_argument("namespace")
    parser.add_argument("artifact_dir")
    parser.add_argument("--timeout-seconds", type=int, default=600)
    parser.add_argument("--kubectl-exec-timeout", type=int, default=20)
    parser.add_argument("--recovery-mode", default=os.environ.get("SEED_FAILURE_INJECTION_RECOVERY_MODE", "phase-start"))
    args = parser.parse_args()

    artifact_dir = Path(args.artifact_dir)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    summary_path = artifact_dir / "failure_injection_summary.json"

    recovery_mode = str(args.recovery_mode or "phase-start")
    target = _pick_target(args.namespace)
    if target is None:
      summary_path.write_text(
          json.dumps(
              {
                  "generated_at": _now(),
                  "executed": False,
                  "status": "fail",
                  "failure_reason": "no_failure_injection_target",
              },
              indent=2,
          ),
          encoding="utf-8",
      )
      return 1

    old_pod = target["pod"]
    deployment = target["deployment"]
    before_ok, before_raw = _protocol_recovered(args.namespace, old_pod, args.kubectl_exec_timeout)
    recovery_raw = ""
    if not before_ok and recovery_mode == "phase-start":
        recovery_ok, recovery_raw = _run_recovery_phase(args.namespace, artifact_dir, args.timeout_seconds)
        (artifact_dir / "failure_injection_recovery.log").write_text(recovery_raw, encoding="utf-8")
        before_ok, before_raw = _protocol_recovered(args.namespace, old_pod, args.kubectl_exec_timeout)
        if not recovery_ok or not before_ok:
            summary_path.write_text(
                json.dumps(
                    {
                        "generated_at": _now(),
                        "executed": False,
                        "status": "fail",
                        "failure_reason": "target_not_protocol_healthy",
                        "target": target,
                        "recovery_mode": recovery_mode,
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            (artifact_dir / "failure_injection_before.txt").write_text("\n".join(part for part in [before_raw, recovery_raw] if part), encoding="utf-8")
            return 1
    (artifact_dir / "failure_injection_before.txt").write_text(before_raw, encoding="utf-8")

    start_ts = int(time.time())
    delete_result = _kubectl(args.namespace, ["delete", "pod", old_pod], timeout=60)
    if delete_result.returncode != 0:
        summary_path.write_text(
            json.dumps(
                {
                    "generated_at": _now(),
                    "executed": True,
                    "status": "fail",
                    "failure_reason": "pod_delete_failed",
                    "target": target,
                    "stdout": delete_result.stdout,
                    "stderr": delete_result.stderr,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return 1

    rollout = _kubectl(args.namespace, ["rollout", "status", f"deployment/{deployment}", f"--timeout={args.timeout_seconds}s"], timeout=args.timeout_seconds + 30)
    if rollout.returncode != 0:
        summary_path.write_text(
            json.dumps(
                {
                    "generated_at": _now(),
                    "executed": True,
                    "status": "fail",
                    "failure_reason": "rollout_timeout",
                    "target": target,
                    "stdout": rollout.stdout,
                    "stderr": rollout.stderr,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return 1

    deadline = time.time() + args.timeout_seconds
    new_pod = ""
    recovered = False
    protocol_raw = ""
    recovery_triggered = False
    recovery_after_delete_raw = ""
    while time.time() < deadline:
        pods = _kubectl_json(args.namespace, ["get", "pods", "-l", f"app={deployment}", "-o", "json"], timeout=30)
        items = pods.get("items", [])
        items.sort(key=lambda item: str(item.get("metadata", {}).get("creationTimestamp", "")), reverse=True)
        for item in items:
            candidate = str(item.get("metadata", {}).get("name", ""))
            if candidate and candidate != old_pod and str(item.get("status", {}).get("phase", "")) == "Running":
                new_pod = candidate
                break
        if new_pod:
            recovered, protocol_raw = _protocol_recovered(args.namespace, new_pod, args.kubectl_exec_timeout)
            if recovered:
                break
            if not recovery_triggered and recovery_mode == "phase-start" and (
                "Unable to connect to server control socket" in protocol_raw or "command terminated with exit code 1" in protocol_raw
            ):
                recovery_triggered = True
                recovery_ok, recovery_after_delete_raw = _run_recovery_phase(args.namespace, artifact_dir, args.timeout_seconds)
                (artifact_dir / "failure_injection_recovery.log").write_text(recovery_after_delete_raw, encoding="utf-8")
                if not recovery_ok:
                    protocol_raw = "\n".join(part for part in [protocol_raw, recovery_after_delete_raw] if part).strip()
                    break
        time.sleep(5)

    end_ts = int(time.time())
    after_detail = "\n".join(part for part in [protocol_raw, recovery_after_delete_raw] if part).strip()
    (artifact_dir / "failure_injection_after.txt").write_text(after_detail, encoding="utf-8")
    summary = {
        "generated_at": _now(),
        "executed": True,
        "status": "pass" if recovered else "fail",
        "injection_type": "delete_pod",
        "target": target,
        "old_pod": old_pod,
        "new_pod": new_pod,
        "before_protocol_ok": before_ok,
        "after_protocol_ok": recovered,
        "recovery_mode": recovery_mode,
        "recovery_triggered": recovery_triggered,
        "recovery_seconds": max(0, end_ts - start_ts),
        "failure_reason": "" if recovered else "recovery_check_failed",
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if recovered else 1


if __name__ == "__main__":
    raise SystemExit(main())
