"""Crash-safe execution journal, snapshots and deterministic recovery."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import time
from typing import Any, Callable, Dict, Mapping, Optional, Tuple

from generator.faults.models import CompiledFaultPlan
from generator.faults.drivers import get_driver


Runner = Callable[[str, int], Tuple[int, str]]


def shell_runner(command: str, timeout: int) -> Tuple[int, str]:
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.returncode, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return 124, "command timed out"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class FaultJournal:
    """Atomic durable journal. No secret or full configuration content is stored."""

    def __init__(self, root: Path, execution_id: str):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / f"{execution_id}.json"

    def write(self, value: Mapping[str, Any]) -> None:
        temporary = self.path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self.path)

    def load(self) -> Dict[str, Any]:
        return json.loads(self.path.read_text(encoding="utf-8"))


@dataclass
class FaultExecutor:
    """Execute a compiled plan while persisting every recoverable transition."""

    journal_root: Path
    runner: Runner = shell_runner

    def inject(self, plan: CompiledFaultPlan, execution_id: str) -> Path:
        journal = FaultJournal(self.journal_root, execution_id)
        if journal.path.is_file():
            previous = journal.load()
            if previous.get("status") != "recovered":
                self.recover(plan, execution_id)
        state: Dict[str, Any] = {
            "schema_version": 1, "execution_id": execution_id,
            "plan_fingerprint": plan.plan_fingerprint, "status": "injecting",
            "created_at": _now(), "updated_at": _now(), "actions": [],
        }
        journal.write(state)
        execution_started = time.monotonic()
        try:
            for action in sorted(plan.actions, key=lambda x: x.inject_order):
                delay = action.at_seconds - (time.monotonic() - execution_started)
                if delay > 0:
                    time.sleep(delay)
                code, snapshot = self.runner(action.snapshot_command, 30)
                if code != 0:
                    raise RuntimeError(f"snapshot failed for {action.action_id}: {snapshot[:500]}")
                entry = {
                    "action_id": action.action_id, "status": "snapshotted",
                    "snapshot": snapshot[:4000], "snapshot_exit": code,
                }
                state["actions"].append(entry)
                state["updated_at"] = _now()
                journal.write(state)
                entry["status"] = "inject_started"
                state["updated_at"] = _now()
                journal.write(state)
                code, output = get_driver(action.driver).inject(action, self.runner)
                if code != 0:
                    raise RuntimeError(f"injection failed for {action.action_id}: {output[:500]}")
                entry["status"] = "injected"
                state["updated_at"] = _now()
                journal.write(state)
                code, output = get_driver(action.driver).verify_active(
                    action, self.runner
                )
                from generator.templates import evaluate_verifier
                if code != 0 or not evaluate_verifier(
                    action.active_verifier_kind, action.active_verifier_value, output
                ):
                    raise RuntimeError(f"activation check failed for {action.action_id}: {output[:500]}")
                entry["status"] = "active"
                state["updated_at"] = _now()
                journal.write(state)
            state["status"] = "active"
            state["updated_at"] = _now()
            journal.write(state)
            return journal.path
        except Exception:
            state["status"] = "injection_failed"
            state["updated_at"] = _now()
            journal.write(state)
            self.recover(plan, execution_id)
            raise

    def recover(self, plan: CompiledFaultPlan, execution_id: str) -> Path:
        journal = FaultJournal(self.journal_root, execution_id)
        state = journal.load()
        if state.get("plan_fingerprint") != plan.plan_fingerprint:
            raise ValueError("journal does not belong to this compiled plan")
        known = {item["action_id"]: item for item in state.get("actions", [])}
        state["status"] = "recovering"
        journal.write(state)
        failures = []
        for action in sorted(plan.actions, key=lambda x: x.cleanup_order):
            entry = known.get(action.action_id)
            if not entry or entry.get("status") not in {
                "inject_started", "injected", "active", "recovery_failed"
            }:
                continue
            code, output = get_driver(action.driver).recover(action, self.runner)
            entry["cleanup_exit"] = code
            entry["cleanup_output"] = output[:1000]
            entry["status"] = "recovered" if code == 0 else "recovery_failed"
            state["updated_at"] = _now()
            journal.write(state)
            if code != 0:
                failures.append(action.action_id)
                continue
            active_code, active_output = get_driver(action.driver).verify_recovered(
                action, self.runner
            )
            from generator.templates import evaluate_verifier
            still_active = evaluate_verifier(
                action.active_verifier_kind,
                action.active_verifier_value,
                active_output,
            )
            entry["recovery_check_exit"] = active_code
            entry["recovery_verified"] = not still_active
            if still_active:
                entry["status"] = "recovery_failed"
                failures.append(action.action_id)
            state["updated_at"] = _now()
            journal.write(state)
        state["status"] = "recovery_failed" if failures else "recovered"
        state["updated_at"] = _now()
        journal.write(state)
        if failures:
            raise RuntimeError(f"recovery failed for actions={failures}")
        return journal.path

    def recover_incomplete(
        self, plans: Mapping[str, CompiledFaultPlan]
    ) -> Tuple[Path, ...]:
        recovered = []
        for path in sorted(self.journal_root.glob("*.json")):
            value = json.loads(path.read_text(encoding="utf-8"))
            if value.get("status") in {"recovered"}:
                continue
            fingerprint = str(value.get("plan_fingerprint", ""))
            plan = plans.get(fingerprint)
            if plan is None:
                continue
            recovered.append(self.recover(plan, str(value["execution_id"])))
        return tuple(recovered)
