"""File-backed distributed scheduling, cache, quarantine and CI scale policy."""

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
from typing import Any, Dict, Mapping, Tuple
import uuid


ID_PATTERN = re.compile(r"^[a-z][a-z0-9_.-]{2,95}$")
RESOURCE_RANK = {"small": 1, "medium": 2, "large": 3, "xlarge": 4}


def _now(): return datetime.now(timezone.utc).isoformat()


def _fingerprint(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _atomic(path: Path, value: Mapping[str, Any], mode=0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    try:
        os.fchmod(descriptor, mode)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True); handle.write("\n")
            handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        try: os.unlink(temporary)
        except FileNotFoundError: pass
        raise


class _StateLock:
    def __init__(self, path: Path, timeout: float = 15.0):
        self.path, self.timeout, self.token = path, timeout, str(uuid.uuid4())

    def __enter__(self):
        deadline = time.monotonic() + self.timeout
        while True:
            try:
                descriptor = os.open(
                    self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600
                )
                os.write(descriptor, self.token.encode("ascii")); os.close(descriptor)
                return self
            except FileExistsError:
                try:
                    if time.time() - self.path.stat().st_mtime > 3600:
                        self.path.unlink(); continue
                except FileNotFoundError:
                    continue
                if time.monotonic() >= deadline:
                    raise TimeoutError("scheduler state lock is busy")
                time.sleep(0.05)

    def __exit__(self, *_args):
        try:
            if self.path.read_text(encoding="ascii") == self.token:
                self.path.unlink()
        except FileNotFoundError:
            pass


@dataclass(frozen=True)
class ProductionJob:
    job_id: str
    request_fingerprint: str
    job_kind: str
    resource_class: str
    scale: int
    payload: Dict[str, Any]
    max_attempts: int = 3
    schema_version: int = 1

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ProductionJob":
        data = dict(value)
        if set(data) != set(cls.__dataclass_fields__) or int(data["schema_version"]) != 1:
            raise ValueError("invalid ProductionJob schema")
        job = cls(
            job_id=str(data["job_id"]), request_fingerprint=str(data["request_fingerprint"]),
            job_kind=str(data["job_kind"]), resource_class=str(data["resource_class"]),
            scale=int(data["scale"]), payload=dict(data["payload"]),
            max_attempts=int(data["max_attempts"]),
        )
        if not ID_PATTERN.fullmatch(job.job_id) or not ID_PATTERN.fullmatch(job.job_kind):
            raise ValueError("invalid production job identity")
        if not re.fullmatch(r"[0-9a-f]{64}", job.request_fingerprint):
            raise ValueError("invalid production job request fingerprint")
        if job.resource_class not in RESOURCE_RANK or not 1 <= job.scale <= 10000:
            raise ValueError("invalid production job resource request")
        if not 1 <= job.max_attempts <= 20:
            raise ValueError("invalid production job retry budget")
        return job

    def to_dict(self): return asdict(self)


class DistributedScheduler:
    """Lease-based queue suitable for workers on a shared durable volume."""

    def __init__(self, state_path: Path):
        self.path = state_path.resolve(); self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock_path = self.path.with_suffix(self.path.suffix + ".lock")

    def load(self):
        if not self.path.exists(): return {"schema_version": 1, "jobs": {}, "quarantine": {}}
        value = json.loads(self.path.read_text(encoding="utf-8"))
        if value.get("schema_version") != 1: raise ValueError("invalid scheduler state")
        return value

    def enqueue(self, job: ProductionJob) -> None:
        ProductionJob.from_dict(job.to_dict())
        with _StateLock(self.lock_path):
            state = self.load(); fingerprint = _fingerprint(job.to_dict())
            current = state["jobs"].get(job.job_id)
            if current and current["job_fingerprint"] != fingerprint:
                raise ValueError("job id is immutable")
            if current: return
            state["jobs"][job.job_id] = {
                "definition": job.to_dict(), "job_fingerprint": fingerprint,
                "status": "pending", "attempts": 0, "lease": None,
                "result": None, "error": "", "created_at": _now(),
            }
            _atomic(self.path, state)

    def recover_expired(self) -> Tuple[str, ...]:
        recovered, now = [], datetime.now(timezone.utc)
        with _StateLock(self.lock_path):
            state = self.load()
            for job_id, item in state["jobs"].items():
                lease = item.get("lease") or {}
                if item["status"] == "running" and lease.get("expires_at") and datetime.fromisoformat(lease["expires_at"]) <= now:
                    item.update({"status": "pending", "lease": None, "error": "expired lease recovered"})
                    recovered.append(job_id)
            if recovered: _atomic(self.path, state)
        return tuple(sorted(recovered))

    def claim(
        self, *, worker_id: str, resource_class: str, max_scale: int,
        lease_seconds: int = 900,
    ) -> Dict[str, Any] | None:
        if not ID_PATTERN.fullmatch(worker_id) or resource_class not in RESOURCE_RANK:
            raise ValueError("invalid scheduler worker")
        if not 1 <= max_scale <= 10000 or not 10 <= lease_seconds <= 86400:
            raise ValueError("invalid scheduler worker capacity")
        self.recover_expired()
        with _StateLock(self.lock_path):
            state = self.load(); candidates = []
            for job_id, item in state["jobs"].items():
                job = ProductionJob.from_dict(item["definition"])
                if (
                    item["status"] in {"pending", "failed"}
                    and item["attempts"] < job.max_attempts
                    and RESOURCE_RANK[job.resource_class] <= RESOURCE_RANK[resource_class]
                    and job.scale <= max_scale
                    and job.request_fingerprint not in state["quarantine"]
                ):
                    candidates.append((job.scale, job_id, job, item))
            if not candidates: return None
            _scale, job_id, job, item = sorted(candidates)[0]
            lease_id = str(uuid.uuid4())
            item["status"] = "running"; item["attempts"] += 1
            item["lease"] = {
                "lease_id": lease_id, "worker_id": worker_id, "acquired_at": _now(),
                "expires_at": (datetime.now(timezone.utc) + timedelta(seconds=lease_seconds)).isoformat(),
            }
            _atomic(self.path, state)
        return {"job": job.to_dict(), "lease_id": lease_id}

    def complete(self, job_id: str, lease_id: str, result: Mapping[str, Any]) -> None:
        with _StateLock(self.lock_path):
            state = self.load(); item = state["jobs"].get(job_id)
            if not item or (item.get("lease") or {}).get("lease_id") != lease_id:
                raise ValueError("scheduler lease does not match")
            payload = dict(result)
            item.update({
                "status": "complete", "lease": None, "error": "",
                "result": payload, "result_fingerprint": _fingerprint(payload),
                "completed_at": _now(),
            })
            _atomic(self.path, state)

    def fail(self, job_id: str, lease_id: str, error: str, *, quarantine=False) -> None:
        with _StateLock(self.lock_path):
            state = self.load(); item = state["jobs"].get(job_id)
            if not item or (item.get("lease") or {}).get("lease_id") != lease_id:
                raise ValueError("scheduler lease does not match")
            job = ProductionJob.from_dict(item["definition"])
            item.update({"status": "failed", "lease": None, "error": str(error)[:2000]})
            if quarantine:
                state["quarantine"][job.request_fingerprint] = {
                    "job_id": job_id, "reason": str(error)[:2000], "created_at": _now(),
                }
            _atomic(self.path, state)


class BuildCache:
    """Content-addressed JSON cache; entries are immutable and checksummed."""

    def __init__(self, root: Path): self.root = root.resolve(); self.root.mkdir(parents=True, exist_ok=True)

    def put(self, namespace: str, inputs: Mapping[str, Any], value: Mapping[str, Any]) -> str:
        if not ID_PATTERN.fullmatch(namespace): raise ValueError("invalid cache namespace")
        key = _fingerprint({"namespace": namespace, "inputs": dict(inputs)})
        path = self.root / namespace / f"{key}.json"
        envelope = {"schema_version": 1, "key": key, "inputs": dict(inputs), "value": dict(value)}
        envelope["entry_fingerprint"] = _fingerprint(envelope)
        if path.exists():
            if json.loads(path.read_text(encoding="utf-8")) != envelope:
                raise ValueError("cache key collision")
        else: _atomic(path, envelope, 0o644)
        return key

    def get(self, namespace: str, key: str) -> Dict[str, Any] | None:
        path = self.root / namespace / f"{key}.json"
        if not path.exists(): return None
        value = json.loads(path.read_text(encoding="utf-8")); supplied = value.pop("entry_fingerprint", "")
        if supplied != _fingerprint(value): raise ValueError("cache entry fingerprint mismatch")
        value["entry_fingerprint"] = supplied
        return value


def continuous_validation_matrix() -> Dict[str, Any]:
    rows = []
    for scale in (5, 20, 100, 1000, 10000):
        if scale == 5:
            execution_mode, schedule = "real_full", "per_commit"
        elif scale == 20:
            execution_mode, schedule = "plan_full", "per_commit"
        elif scale == 100:
            execution_mode, schedule = "real_full", "nightly"
        else:
            execution_mode, schedule = "plan_performance_sampled", "weekly"
        rows.append({
            "scale": scale,
            "execution_mode": execution_mode,
            "schedule": schedule,
            "required_checks": [
                "contract", "plan", "resource_budget", "safety", "quality",
                *( ["docker_lifecycle"] if scale in {5, 100} else (
                    ["sampling", "performance"] if scale >= 1000
                    else ["selector_full_resolution"]
                )),
            ],
        })
    value = {"schema_version": 1, "rows": rows}
    value["matrix_fingerprint"] = _fingerprint(value)
    return value
