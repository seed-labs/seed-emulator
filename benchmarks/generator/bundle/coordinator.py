"""Crash-resumable DAG coordinator for collaborating benchmark agents."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import time
from typing import Any, Callable, Dict, Mapping, Sequence, Tuple
import uuid

from generator.bundle.artifacts import AgentArtifact, ArtifactStore, canonical_sha256


TASK_SCHEMA_VERSION = 1
ID_PATTERN = re.compile(r"^[a-z][a-z0-9_.-]{2,95}$")
TaskHandler = Callable[["AgentTask", Tuple[AgentArtifact, ...]], AgentArtifact]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class AgentTask:
    task_id: str
    agent_role: str
    output_artifact_id: str
    output_artifact_type: str
    dependencies: Tuple[str, ...] = ()
    input_artifacts: Tuple[str, ...] = ()
    parameters: Dict[str, Any] = None
    max_attempts: int = 3
    timeout_seconds: int = 300
    schema_version: int = TASK_SCHEMA_VERSION

    def __post_init__(self):
        if self.parameters is None:
            object.__setattr__(self, "parameters", {})

    def to_dict(self):
        value = asdict(self)
        value["dependencies"] = list(self.dependencies)
        value["input_artifacts"] = list(self.input_artifacts)
        return value

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "AgentTask":
        data = dict(value)
        required = {
            "schema_version", "task_id", "agent_role", "output_artifact_id",
            "output_artifact_type", "dependencies", "input_artifacts",
            "parameters", "max_attempts", "timeout_seconds",
        }
        if set(data) != required or data["schema_version"] != TASK_SCHEMA_VERSION:
            raise ValueError("invalid AgentTask schema")
        for key in ("task_id", "agent_role", "output_artifact_id"):
            if not ID_PATTERN.fullmatch(str(data[key])):
                raise ValueError(f"invalid task field={key}")
        attempts, timeout = int(data["max_attempts"]), int(data["timeout_seconds"])
        if not 1 <= attempts <= 20 or not 1 <= timeout <= 86400:
            raise ValueError("invalid task execution budget")
        return cls(
            task_id=str(data["task_id"]), agent_role=str(data["agent_role"]),
            output_artifact_id=str(data["output_artifact_id"]),
            output_artifact_type=str(data["output_artifact_type"]),
            dependencies=tuple(str(x) for x in data["dependencies"]),
            input_artifacts=tuple(str(x) for x in data["input_artifacts"]),
            parameters=dict(data["parameters"]), max_attempts=attempts,
            timeout_seconds=timeout,
        )


def validate_dag(tasks: Sequence[AgentTask]) -> None:
    ids = [item.task_id for item in tasks]
    if not ids or len(ids) != len(set(ids)):
        raise ValueError("tasks must be non-empty and unique")
    outputs = [item.output_artifact_id for item in tasks]
    if len(outputs) != len(set(outputs)):
        raise ValueError("task output artifacts must be unique")
    known = set(ids)
    for task in tasks:
        if set(task.dependencies) - known or task.task_id in task.dependencies:
            raise ValueError(f"task {task.task_id} has invalid dependencies")
    visiting, visited = set(), set()
    by_id = {item.task_id: item for item in tasks}

    def visit(task_id: str):
        if task_id in visiting:
            raise ValueError("agent task graph contains a cycle")
        if task_id in visited:
            return
        visiting.add(task_id)
        for dependency in by_id[task_id].dependencies:
            visit(dependency)
        visiting.remove(task_id)
        visited.add(task_id)

    for task_id in ids:
        visit(task_id)


class _StateLock:
    def __init__(self, path: Path, *, timeout: float = 10.0):
        self.path, self.timeout = path, timeout
        self.token = str(uuid.uuid4())

    def __enter__(self):
        deadline = time.monotonic() + self.timeout
        while True:
            try:
                descriptor = os.open(
                    self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600
                )
                os.write(descriptor, self.token.encode("ascii"))
                os.close(descriptor)
                return self
            except FileExistsError:
                try:
                    age = time.time() - self.path.stat().st_mtime
                    if age > 3600:
                        self.path.unlink()
                        continue
                except FileNotFoundError:
                    continue
                if time.monotonic() >= deadline:
                    raise TimeoutError("coordinator state lock is busy")
                time.sleep(0.05)

    def __exit__(self, *_args):
        try:
            if self.path.read_text(encoding="ascii") == self.token:
                self.path.unlink()
        except FileNotFoundError:
            pass


class BenchmarkCoordinator:
    """Persist state before and after every task transition."""

    def __init__(self, state_path: Path, artifact_store: ArtifactStore):
        self.state_path = state_path.resolve()
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.lock_path = self.state_path.with_suffix(self.state_path.suffix + ".lock")
        self.artifact_store = artifact_store

    def _atomic_write(self, value: Mapping[str, Any]) -> None:
        descriptor, temporary = tempfile.mkstemp(
            prefix=f".{self.state_path.name}.", suffix=".tmp",
            dir=self.state_path.parent, text=True,
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.state_path)
        except Exception:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass
            raise

    def initialize(self, tasks: Sequence[AgentTask], *, force: bool = False):
        validate_dag(tasks)
        definition_fingerprint = canonical_sha256(
            {"tasks": [item.to_dict() for item in tasks]}
        )
        with _StateLock(self.lock_path):
            if self.state_path.exists() and not force:
                state = self.load()
                if state["definition_fingerprint"] != definition_fingerprint:
                    raise ValueError("coordinator task definition has changed")
                return state
            state = {
                "schema_version": 1,
                "definition_fingerprint": definition_fingerprint,
                "created_at": _now(), "updated_at": _now(),
                "tasks": {
                    item.task_id: {
                        "definition": item.to_dict(), "status": "pending",
                        "attempts": 0, "lease": None, "input_fingerprint": "",
                        "output_fingerprint": "", "error": "",
                    }
                    for item in tasks
                },
            }
            self._atomic_write(state)
            return state

    def load(self):
        state = json.loads(self.state_path.read_text(encoding="utf-8"))
        if state.get("schema_version") != 1:
            raise ValueError("unsupported coordinator state")
        return state

    def ready_tasks(self) -> Tuple[str, ...]:
        state = self.load()
        return self._ready_from_state(state)

    @staticmethod
    def _ready_from_state(state) -> Tuple[str, ...]:
        complete = {
            task_id for task_id, item in state["tasks"].items()
            if item["status"] == "complete"
        }
        return tuple(sorted(
            task_id for task_id, item in state["tasks"].items()
            if item["status"] in {"pending", "failed"}
            and set(item["definition"]["dependencies"]) <= complete
            and item["attempts"] < item["definition"]["max_attempts"]
        ))

    def claim_next(
        self, *, worker_id: str, agent_role: str | None = None,
    ) -> Dict[str, Any] | None:
        """Lease one ready task for an external Agent process."""
        if not ID_PATTERN.fullmatch(worker_id):
            raise ValueError("invalid coordinator worker_id")
        with _StateLock(self.lock_path):
            state = self.load()
            ready = self._ready_from_state(state)
            if agent_role is not None:
                if not ID_PATTERN.fullmatch(agent_role):
                    raise ValueError("invalid coordinator agent_role")
                ready = tuple(
                    task_id for task_id in ready
                    if state["tasks"][task_id]["definition"]["agent_role"]
                    == agent_role
                )
            if not ready:
                return None
            task_id = ready[0]
            item = state["tasks"][task_id]
            task = AgentTask.from_dict(item["definition"])
            lease_id = str(uuid.uuid4())
            item["status"] = "running"
            item["attempts"] += 1
            item["lease"] = {
                "lease_id": lease_id, "worker_id": worker_id,
                "acquired_at": _now(),
                "expires_at": (
                    datetime.now(timezone.utc)
                    + timedelta(seconds=task.timeout_seconds)
                ).isoformat(),
            }
            state["updated_at"] = _now()
            self._atomic_write(state)
        inputs = tuple(self.artifact_store.load(x) for x in task.input_artifacts)
        return {
            "task": task.to_dict(), "lease_id": lease_id,
            "input_artifacts": [item.to_dict() for item in inputs],
        }

    def complete_claim(
        self, task_id: str, lease_id: str, artifact: AgentArtifact,
    ) -> Path:
        """Validate an external Agent result before publishing it."""
        with _StateLock(self.lock_path):
            state = self.load()
            item = state["tasks"].get(task_id)
            if item is None or item.get("status") != "running":
                raise ValueError("task is not currently leased")
            lease = item.get("lease") or {}
            if lease.get("lease_id") != lease_id:
                raise ValueError("task lease does not match")
            if datetime.fromisoformat(lease["expires_at"]) <= datetime.now(timezone.utc):
                raise ValueError("task lease has expired")
            task = AgentTask.from_dict(item["definition"])
            inputs = tuple(
                self.artifact_store.load(x) for x in task.input_artifacts
            )
            if artifact.artifact_id != task.output_artifact_id:
                raise ValueError("agent produced an unexpected artifact id")
            if artifact.artifact_type != task.output_artifact_type:
                raise ValueError("agent produced an unexpected artifact type")
            expected_inputs = tuple(x.artifact_fingerprint for x in inputs)
            if artifact.input_fingerprints != expected_inputs:
                raise ValueError("agent artifact does not attest its exact inputs")
            path = self.artifact_store.write(artifact)
            stored = self.artifact_store.load(artifact.artifact_id)
            item.update({
                "status": "complete", "lease": None, "error": "",
                "input_fingerprint": canonical_sha256({
                    "task": task.to_dict(), "inputs": list(expected_inputs),
                }),
                "output_fingerprint": stored.artifact_fingerprint,
                "completed_at": _now(),
            })
            state["updated_at"] = _now()
            self._atomic_write(state)
            return path

    def fail_claim(self, task_id: str, lease_id: str, error: str) -> None:
        with _StateLock(self.lock_path):
            state = self.load()
            item = state["tasks"].get(task_id)
            if item is None or (item.get("lease") or {}).get("lease_id") != lease_id:
                raise ValueError("task lease does not match")
            item.update({
                "status": "failed", "lease": None,
                "error": str(error)[:2000],
            })
            state["updated_at"] = _now()
            self._atomic_write(state)

    def run(
        self, handlers: Mapping[str, TaskHandler], *, worker_id: str,
    ) -> Dict[str, Any]:
        if not ID_PATTERN.fullmatch(worker_id):
            raise ValueError("invalid coordinator worker_id")
        while True:
            ready = self.ready_tasks()
            if not ready:
                break
            self._run_one(ready[0], handlers, worker_id)
        state = self.load()
        failed = [key for key, item in state["tasks"].items() if item["status"] == "failed"]
        blocked = [key for key, item in state["tasks"].items() if item["status"] == "pending"]
        state["result"] = "complete" if not failed and not blocked else "incomplete"
        self._atomic_write(state)
        return state

    def _run_one(
        self, task_id: str, handlers: Mapping[str, TaskHandler], worker_id: str,
    ) -> None:
        with _StateLock(self.lock_path):
            state = self.load()
            item = state["tasks"][task_id]
            task = AgentTask.from_dict(item["definition"])
            if item["status"] == "complete":
                return
            lease_id = str(uuid.uuid4())
            item["status"] = "running"
            item["attempts"] += 1
            item["lease"] = {
                "lease_id": lease_id, "worker_id": worker_id,
                "acquired_at": _now(),
                "expires_at": (
                    datetime.now(timezone.utc) + timedelta(seconds=task.timeout_seconds)
                ).isoformat(),
            }
            state["updated_at"] = _now()
            self._atomic_write(state)
        try:
            inputs = tuple(self.artifact_store.load(x) for x in task.input_artifacts)
            input_fingerprint = canonical_sha256({
                "task": task.to_dict(),
                "inputs": [item.artifact_fingerprint for item in inputs],
            })
            handler = handlers.get(task.agent_role)
            if handler is None:
                raise ValueError(f"no handler registered for agent_role={task.agent_role}")
            artifact = handler(task, inputs)
            if artifact.artifact_id != task.output_artifact_id:
                raise ValueError("agent produced an unexpected artifact id")
            if artifact.artifact_type != task.output_artifact_type:
                raise ValueError("agent produced an unexpected artifact type")
            expected_inputs = tuple(item.artifact_fingerprint for item in inputs)
            if artifact.input_fingerprints != expected_inputs:
                raise ValueError("agent artifact does not attest its exact inputs")
            self.artifact_store.write(artifact)
            stored = self.artifact_store.load(artifact.artifact_id)
            with _StateLock(self.lock_path):
                state = self.load()
                item = state["tasks"][task_id]
                if (item.get("lease") or {}).get("lease_id") != lease_id:
                    raise RuntimeError("coordinator lease changed while task was running")
                item.update({
                    "status": "complete", "lease": None, "error": "",
                    "input_fingerprint": input_fingerprint,
                    "output_fingerprint": stored.artifact_fingerprint,
                    "completed_at": _now(),
                })
                state["updated_at"] = _now()
                self._atomic_write(state)
        except Exception as exc:
            with _StateLock(self.lock_path):
                state = self.load()
                item = state["tasks"][task_id]
                item.update({"status": "failed", "lease": None, "error": str(exc)[:2000]})
                state["updated_at"] = _now()
                self._atomic_write(state)
            raise

    def recover_expired_leases(self) -> Tuple[str, ...]:
        recovered = []
        now = datetime.now(timezone.utc)
        with _StateLock(self.lock_path):
            state = self.load()
            for task_id, item in state["tasks"].items():
                lease = item.get("lease") or {}
                if item["status"] != "running" or not lease.get("expires_at"):
                    continue
                if datetime.fromisoformat(lease["expires_at"]) <= now:
                    item["status"] = "pending"
                    item["lease"] = None
                    item["error"] = "expired lease recovered"
                    recovered.append(task_id)
            if recovered:
                state["updated_at"] = _now()
                self._atomic_write(state)
        return tuple(recovered)
