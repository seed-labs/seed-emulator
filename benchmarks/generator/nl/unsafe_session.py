"""Plan-only sessions and explicitly approved execution for unsafe NL scenarios."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import tempfile
import time
from typing import Any, Dict, Mapping, Sequence

from generator.nl.audit import atomic_json, canonical_sha256, nl_contract_sha256, signed_record
from generator.nl.provider import LLMProvider, ProviderResponse
from generator.nl.security import inspect_natural_language
from generator.nl.unsafe_models import (
    UNSAFE_PLAN_OUTPUT_SCHEMA,
    UnsafeScenarioPlan,
    validate_unsafe_provider_output,
)
from generator.nl.unsafe_policy import (
    ALLOWED_CAPABILITIES,
    UnsafePolicyResult,
    compile_unsafe_policy,
    policy_snapshot,
)
from generator.nl.unsafe_provider import UNSAFE_PROMPT_VERSION, build_unsafe_messages


UNSAFE_SESSION_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_.-]{2,95}$")
SNAP_DOCKER_WRAPPER = Path("/snap/bin/docker")
SNAP_DOCKER_BINARY = Path("/snap/docker/current/bin/docker")
MAX_CAPTURE_BYTES = 4 * 1024 * 1024


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _read(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _unsafe_session_id(text: str, seed: str) -> str:
    stamp = _utcnow().strftime("%Y%m%dT%H%M%SZ")
    suffix = hashlib.sha256(f"{text}\0{seed}".encode("utf-8")).hexdigest()[:12]
    return f"unsafe_{stamp}_{suffix}"


def _session_label(session: Path) -> str:
    return f"unsafe_{hashlib.sha256(str(session).encode('utf-8')).hexdigest()[:20]}"


def _atomic_text(path: Path, content: str, mode: int) -> None:
    destination = path.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{destination.name}.", dir=destination.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, destination)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def _cache_key(
    *, text: str, seed: str, provider: LLMProvider, policy_fingerprint: str,
) -> str:
    return canonical_sha256({
        "text": " ".join(text.split()),
        "seed": seed,
        "provider": provider.provider_id,
        "model": provider.model_id,
        "prompt_version": UNSAFE_PROMPT_VERSION,
        "schema": UNSAFE_PLAN_OUTPUT_SCHEMA,
        "policy": policy_fingerprint,
    })


def _materialize_bundle(
    destination: Path, plan: UnsafeScenarioPlan, policy: UnsafePolicyResult,
) -> Path:
    destination.mkdir(parents=True, exist_ok=False)
    root = destination.resolve()
    for item in plan.files:
        path = (root / item.path).resolve()
        path.relative_to(root)
        _atomic_text(path, item.content, int(item.mode, 8))
    compose_path = root / "compose.yaml"
    _atomic_text(compose_path, policy.sanitized_compose_yaml, 0o600)
    return compose_path


class UnsafeNaturalLanguagePlanner:
    def __init__(self, benchmarks_dir: Path, session_root: Path):
        self.benchmarks_dir = benchmarks_dir.resolve()
        self.session_root = session_root.resolve()
        self.session_root.mkdir(parents=True, exist_ok=True)

    def _new_session(self, text: str, seed: str, session_id: str | None) -> Path:
        identity = session_id or _unsafe_session_id(text, seed)
        if not UNSAFE_SESSION_PATTERN.fullmatch(identity):
            raise ValueError("invalid unsafe NL session identity")
        path = (self.session_root / identity).resolve()
        path.relative_to(self.session_root)
        if path.exists():
            raise FileExistsError(f"unsafe NL session already exists: {path}")
        path.mkdir(parents=True)
        return path

    def plan(
        self,
        text: str,
        *,
        provider: LLMProvider,
        seed: str,
        session_id: str | None = None,
    ) -> Dict[str, Any]:
        session = self._new_session(text, seed, session_id)
        created = _utcnow().isoformat()
        source = {
            "schema_version": 1,
            "mode": "unsafe_plan_only",
            "text": text,
            "text_sha256": hashlib.sha256(" ".join(text.split()).encode("utf-8")).hexdigest(),
            "seed": seed,
            "created_at": created,
            "docker_state_changed": False,
        }
        atomic_json(session / "input.json", source)
        security = inspect_natural_language(text)
        atomic_json(session / "security_input.json", security.to_dict())
        snapshot = policy_snapshot()
        snapshot["policy_fingerprint"] = canonical_sha256(snapshot)
        atomic_json(session / "unsafe_policy_snapshot.json", snapshot)
        if not security.allowed:
            return self._finish(session, {
                "status": "blocked", "session": str(session),
                "provider_invoked": False, "security": security.to_dict(),
            })

        messages = build_unsafe_messages(text)
        request = {
            "schema_version": 1,
            "prompt_version": UNSAFE_PROMPT_VERSION,
            "messages": messages,
            "output_schema": UNSAFE_PLAN_OUTPUT_SCHEMA,
            "provider": provider.provider_id,
            "model": provider.model_id,
        }
        request["prompt_fingerprint"] = canonical_sha256(request)
        atomic_json(session / "provider_request.json", request)
        cache_key = _cache_key(
            text=text, seed=seed, provider=provider,
            policy_fingerprint=snapshot["policy_fingerprint"],
        )
        cache_path = self.session_root / "_unsafe_cache" / f"{cache_key}.json"
        cache_hit = cache_path.is_file()
        if cache_hit:
            response = ProviderResponse(**_read(cache_path)["response"])
        else:
            try:
                response = provider.complete_structured(
                    messages, UNSAFE_PLAN_OUTPUT_SCHEMA, seed=seed
                )
            except Exception as exc:
                failure = {
                    "schema_version": 1,
                    "provider": provider.provider_id,
                    "model": provider.model_id,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "failed_at": _utcnow().isoformat(),
                }
                atomic_json(session / "provider_error.json", failure)
                return self._finish(session, {
                    "status": "provider_error", "session": str(session),
                    "provider_invoked": True, "provider_cache_hit": False,
                    "provider_error": failure,
                })
        atomic_json(session / "provider_response.json", response.to_dict())
        try:
            validate_unsafe_provider_output(response.output)
            plan = UnsafeScenarioPlan.from_provider_output(
                response.output,
                source_text=text,
                seed=seed,
                provider_model=f"{response.provider}:{response.model}",
            )
        except Exception as exc:
            rejection = {
                "schema_version": 1, "allowed": False,
                "error_type": type(exc).__name__, "error": str(exc),
            }
            atomic_json(session / "unsafe_schema_rejection.json", rejection)
            return self._finish(session, {
                "status": "schema_rejected", "session": str(session),
                "provider_invoked": True, "provider_cache_hit": cache_hit,
                "schema": rejection,
            })
        if not cache_hit:
            atomic_json(cache_path, {
                "schema_version": 1, "cache_key": cache_key,
                "response": response.to_dict(),
            })
        label = _session_label(session)
        try:
            policy = compile_unsafe_policy(plan, session_label=label)
        except Exception as exc:
            rejection = {
                "schema_version": 1,
                "allowed": False,
                "error_type": type(exc).__name__,
                "error": str(exc),
                "plan_fingerprint": plan.fingerprint,
            }
            atomic_json(session / "unsafe_policy.json", rejection)
            atomic_json(session / "unsafe_plan_rejected.json", {
                **plan.to_dict(), "plan_fingerprint": plan.fingerprint,
            })
            return self._finish(session, {
                "status": "policy_rejected", "session": str(session),
                "provider_invoked": True, "provider_cache_hit": cache_hit,
                "policy": rejection,
            })

        plan_record = {**plan.to_dict(), "plan_fingerprint": plan.fingerprint}
        atomic_json(session / "unsafe_plan.json", plan_record)
        atomic_json(session / "unsafe_policy.json", policy.to_dict())
        bundle = session / "unsafe_bundle"
        compose_path = _materialize_bundle(bundle, plan, policy)
        preview = {
            "schema_version": 1,
            "unsafe_generated": True,
            "mode": "plan_only_no_docker_state_change",
            "execution_authorized": False,
            "promotion_eligible": False,
            "qualification_status": "forbidden",
            "publication_status": "forbidden",
            "session_label": label,
            "plan_fingerprint": plan.fingerprint,
            "policy_fingerprint": policy.policy_fingerprint,
            "raw_compose_yaml": plan.compose_yaml,
            "sanitized_compose_yaml": policy.sanitized_compose_yaml,
            "generated_files": [
                {"path": item.path, "mode": item.mode, "content": item.content}
                for item in plan.files
            ],
            "shell_steps": [item.__dict__ for item in plan.steps],
            "effective_limits": policy.effective_limits,
            "risks": list(policy.risks),
        }
        preview["preview_fingerprint"] = canonical_sha256(preview)
        atomic_json(session / "unsafe_preview.json", preview)
        token = secrets.token_urlsafe(48)
        challenge = signed_record({
            "schema_version": 1,
            "challenge_kind": "unsafe_arbitrary_code_v1",
            "unsafe_generated": True,
            "session_label": label,
            "plan_fingerprint": plan.fingerprint,
            "policy_fingerprint": policy.policy_fingerprint,
            "preview_fingerprint": preview["preview_fingerprint"],
            "token_sha256": hashlib.sha256(token.encode("utf-8")).hexdigest(),
            "issued_at": _utcnow().isoformat(),
            "expires_at": (_utcnow() + timedelta(hours=2)).isoformat(),
            "consumed": False,
            "acknowledgement_required": "acknowledge-arbitrary-code",
            "qualification_authorized": False,
            "publication_authorized": False,
        }, "challenge_fingerprint")
        atomic_json(session / "unsafe_approval_challenge.json", challenge, mode=0o600)
        return self._finish(session, {
            "status": "ready", "session": str(session),
            "unsafe_plan": str(session / "unsafe_plan.json"),
            "approval_token": token,
            "approval_expires_at": challenge["expires_at"],
            "provider_invoked": True,
            "provider_cache_hit": cache_hit,
            "plan_fingerprint": plan.fingerprint,
            "policy_fingerprint": policy.policy_fingerprint,
            "compose_path": str(compose_path),
            "preview": preview,
        })

    def _finish(self, session: Path, result: Mapping[str, Any]) -> Dict[str, Any]:
        audit = signed_record({
            "schema_version": 1,
            "unsafe_generated": True,
            "created_at": _utcnow().isoformat(),
            "nl_contract_sha256": nl_contract_sha256(),
            "status": result["status"],
            "session": str(session),
            "evidence": sorted(str(path.relative_to(session)) for path in session.rglob("*.*")),
        }, "audit_fingerprint")
        atomic_json(session / "unsafe_audit.json", audit)
        output = dict(result)
        output["nl_contract_sha256"] = audit["nl_contract_sha256"]
        output["audit_fingerprint"] = audit["audit_fingerprint"]
        return output


class UnsafeNaturalLanguageExecutor:
    def __init__(self, benchmarks_dir: Path, allowed_root: Path):
        self.benchmarks_dir = benchmarks_dir.resolve()
        self.allowed_root = allowed_root.resolve()

    def _plan_path(self, value: Path) -> Path:
        path = value.resolve()
        path.relative_to(self.allowed_root)
        if path.name != "unsafe_plan.json" or not path.is_file():
            raise ValueError("plan must be unsafe_plan.json under the allowed session root")
        return path

    @staticmethod
    def _capture_text(path: Path, content: str) -> Dict[str, Any]:
        encoded = content.encode("utf-8", errors="replace")
        truncated = len(encoded) > MAX_CAPTURE_BYTES
        if truncated:
            encoded = encoded[:MAX_CAPTURE_BYTES]
            content = encoded.decode("utf-8", errors="replace") + "\n[truncated]\n"
        _atomic_text(path, content, 0o600)
        return {"path": str(path), "bytes": len(encoded), "truncated": truncated}

    def _run(
        self,
        *,
        name: str,
        args: Sequence[str],
        cwd: Path,
        timeout: int,
        evidence_dir: Path,
        commands: list,
        disk_guard: Path | None = None,
        max_disk_delta_bytes: int | None = None,
    ) -> subprocess.CompletedProcess:
        started = _utcnow().isoformat()
        disk_exceeded = False
        output_exceeded = False
        if disk_guard is not None and (
            max_disk_delta_bytes is None or max_disk_delta_bytes <= 0
        ):
            raise ValueError("disk-guarded command needs a positive disk limit")
        initial_free = shutil.disk_usage(disk_guard).free if disk_guard else None
        stdout_descriptor, stdout_temporary = tempfile.mkstemp(
            prefix=f".{name}.stdout.", dir=evidence_dir,
        )
        stderr_descriptor, stderr_temporary = tempfile.mkstemp(
            prefix=f".{name}.stderr.", dir=evidence_dir,
        )
        try:
            stdout_handle = os.fdopen(stdout_descriptor, "wb")
            stderr_handle = os.fdopen(stderr_descriptor, "wb")
            process = subprocess.Popen(
                list(args), cwd=cwd, stdout=stdout_handle, stderr=stderr_handle,
                env={**os.environ, "COMPOSE_PROGRESS": "plain"},
            )
            deadline = time.monotonic() + timeout
            timed_out = False
            while process.poll() is None:
                timed_out = time.monotonic() >= deadline
                output_exceeded = (
                    Path(stdout_temporary).stat().st_size > MAX_CAPTURE_BYTES
                    or Path(stderr_temporary).stat().st_size > MAX_CAPTURE_BYTES
                )
                if disk_guard is not None and initial_free is not None:
                    current_free = shutil.disk_usage(disk_guard).free
                    disk_exceeded = (
                        initial_free - current_free > int(max_disk_delta_bytes)
                    )
                if timed_out or disk_exceeded or output_exceeded:
                    process.terminate()
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                    break
                time.sleep(0.05)
            output_exceeded = output_exceeded or (
                Path(stdout_temporary).stat().st_size > MAX_CAPTURE_BYTES
                or Path(stderr_temporary).stat().st_size > MAX_CAPTURE_BYTES
            )
            stdout_handle.close()
            stderr_handle.close()
            stdout_value = Path(stdout_temporary).read_bytes()[:MAX_CAPTURE_BYTES].decode(
                "utf-8", errors="replace"
            )
            stderr_value = Path(stderr_temporary).read_bytes()[:MAX_CAPTURE_BYTES].decode(
                "utf-8", errors="replace"
            )
            return_code = process.returncode
            if timed_out:
                return_code = 124
                stderr_value += "\n[execution time budget exceeded]\n"
            if disk_exceeded:
                return_code = 125
                stderr_value += "\n[build disk budget exceeded]\n"
            if output_exceeded:
                return_code = 126
                stderr_value += "\n[command output budget exceeded]\n"
            completed = subprocess.CompletedProcess(
                list(args), return_code, stdout=stdout_value, stderr=stderr_value,
            )
        finally:
            for temporary in (stdout_temporary, stderr_temporary):
                try:
                    os.unlink(temporary)
                except FileNotFoundError:
                    pass
        stdout = self._capture_text(evidence_dir / f"{name}.stdout.log", completed.stdout)
        stderr = self._capture_text(evidence_dir / f"{name}.stderr.log", completed.stderr)
        record = {
            "name": name, "argv": list(args), "cwd": str(cwd),
            "started_at": started, "completed_at": _utcnow().isoformat(),
            "timeout_seconds": timeout, "timed_out": timed_out,
            "disk_guard": str(disk_guard) if disk_guard else None,
            "disk_budget_exceeded": disk_exceeded,
            "output_budget_exceeded": output_exceeded,
            "exit_code": completed.returncode, "stdout": stdout, "stderr": stderr,
        }
        commands.append(record)
        atomic_json(evidence_dir / "commands.json", {"schema_version": 1, "commands": commands})
        return completed

    def _claim(self, session: Path, challenge: Mapping[str, Any]) -> None:
        claim_path = session / "unsafe_execution.claim"
        try:
            descriptor = os.open(claim_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError as exc:
            raise ValueError("unsafe approval has already been claimed") from exc
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump({
                "challenge_fingerprint": challenge["challenge_fingerprint"],
                "claimed_at": _utcnow().isoformat(),
            }, handle, sort_keys=True)
            handle.write("\n")

    def execute(
        self,
        plan_path: Path,
        approval_token: str,
        *,
        acknowledge_arbitrary_code: bool,
    ) -> Dict[str, Any]:
        if not acknowledge_arbitrary_code:
            raise ValueError("--acknowledge-arbitrary-code is required")
        path = self._plan_path(plan_path)
        session = path.parent
        plan_value = _read(path)
        plan_value.pop("plan_fingerprint", None)
        plan = UnsafeScenarioPlan.from_dict(plan_value)
        challenge_path = session / "unsafe_approval_challenge.json"
        challenge = _read(challenge_path)
        if challenge.get("challenge_kind") != "unsafe_arbitrary_code_v1":
            raise ValueError("approval token is not an unsafe-code challenge")
        if challenge.get("consumed"):
            raise ValueError("unsafe approval token has already been consumed")
        supplied_hash = hashlib.sha256(approval_token.encode("utf-8")).hexdigest()
        if not secrets.compare_digest(supplied_hash, challenge["token_sha256"]):
            raise ValueError("unsafe approval token is invalid")
        if _utcnow() > datetime.fromisoformat(challenge["expires_at"]):
            raise ValueError("unsafe approval token has expired")
        if challenge.get("qualification_authorized") or challenge.get("publication_authorized"):
            raise ValueError("unsafe approval challenge cannot authorize qualification or publication")
        policy = compile_unsafe_policy(plan, session_label=challenge["session_label"])
        if challenge["plan_fingerprint"] != plan.fingerprint:
            raise ValueError("unsafe plan changed after approval")
        if challenge["policy_fingerprint"] != policy.policy_fingerprint:
            raise ValueError("unsafe policy result changed after approval")
        self._claim(session, challenge)
        consumed = dict(challenge)
        consumed["consumed"] = True
        consumed["consumed_at"] = _utcnow().isoformat()
        consumed["challenge_fingerprint"] = ""
        consumed["challenge_fingerprint"] = canonical_sha256(consumed)
        atomic_json(challenge_path, consumed, mode=0o600)

        workspace = session / "unsafe_execution"
        if workspace.exists():
            raise FileExistsError("unsafe execution workspace already exists")
        workspace.mkdir(parents=True)
        bundle = workspace / "bundle"
        compose_path = _materialize_bundle(bundle, plan, policy)
        evidence = workspace / "evidence"
        evidence.mkdir()
        commands: list = []
        docker = str(SNAP_DOCKER_WRAPPER) if SNAP_DOCKER_WRAPPER.is_file() else "docker"
        docker_cli = str(SNAP_DOCKER_BINARY) if SNAP_DOCKER_BINARY.is_file() else docker
        project = challenge["session_label"]
        compose = [docker, "compose", "-p", project, "-f", str(compose_path)]
        error = None
        runtime_started: float | None = None
        image_evidence = []
        runtime_snapshot = []
        cleanup = {"attempted": False, "verified": False, "remaining_containers": [], "remaining_networks": [], "remaining_images": []}
        try:
            docker_root_result = self._run(
                name="000_docker_root",
                args=[docker_cli, "info", "--format", "{{.DockerRootDir}}"], cwd=bundle,
                timeout=30, evidence_dir=evidence, commands=commands,
            )
            if docker_root_result.returncode != 0:
                raise RuntimeError("cannot resolve Docker root for disk-budget enforcement")
            docker_root = Path(docker_root_result.stdout.strip()).resolve()
            if not docker_root.is_dir():
                raise RuntimeError("Docker root is unavailable for disk-budget enforcement")
            base_image_evidence = []
            for index, base_image in enumerate(policy.base_images):
                inspected_base = self._run(
                    name=f"000_base_image_{index:03d}",
                    args=[docker_cli, "image", "inspect", base_image], cwd=bundle,
                    timeout=30, evidence_dir=evidence, commands=commands,
                )
                if inspected_base.returncode != 0:
                    raise RuntimeError(
                        f"unsafe base image must already exist locally: {base_image}"
                    )
                value = json.loads(inspected_base.stdout)[0]
                base_image_evidence.append({
                    "reference": base_image, "id": value["Id"],
                    "repo_digests": value.get("RepoDigests") or [],
                    "size": int(value.get("Size", 0)),
                })
            atomic_json(evidence / "base_images.json", {
                "schema_version": 1, "images": base_image_evidence,
            })
            build = self._run(
                name="001_build", args=[*compose, "build", "--no-cache"], cwd=bundle,
                timeout=plan.budget.max_build_seconds, evidence_dir=evidence, commands=commands,
                disk_guard=docker_root,
                max_disk_delta_bytes=plan.budget.max_disk_mb * 1024 * 1024,
            )
            if build.returncode != 0:
                raise RuntimeError("unsafe Compose build failed")
            images = self._run(
                name="002_images", args=[*compose, "config", "--images"], cwd=bundle,
                timeout=30, evidence_dir=evidence, commands=commands,
            )
            if images.returncode != 0:
                raise RuntimeError("unsafe Compose image inventory failed")
            unique_images = sorted(set(line.strip() for line in images.stdout.splitlines() if line.strip()))
            unique_ids = set()
            total_image_bytes = 0
            for index, image_name in enumerate(unique_images):
                inspected = self._run(
                    name=f"003_image_{index:03d}",
                    args=[docker_cli, "image", "inspect", image_name], cwd=bundle,
                    timeout=30, evidence_dir=evidence, commands=commands,
                )
                if inspected.returncode != 0:
                    raise RuntimeError(f"unsafe image inspection failed: {image_name}")
                image = json.loads(inspected.stdout)[0]
                if image["Id"] not in unique_ids:
                    total_image_bytes += int(image.get("Size", 0))
                    unique_ids.add(image["Id"])
                image_evidence.append({
                    "name": image_name, "id": image["Id"], "size": int(image.get("Size", 0)),
                    "repo_digests": image.get("RepoDigests") or [],
                })
            if total_image_bytes > plan.budget.max_disk_mb * 1024 * 1024:
                raise RuntimeError("unsafe generated images exceed the disk budget")
            atomic_json(evidence / "images.json", {
                "schema_version": 1, "total_unique_bytes": total_image_bytes,
                "images": image_evidence,
            })
            up = self._run(
                name="004_up", args=[*compose, "up", "-d", "--no-build"], cwd=bundle,
                timeout=min(300, plan.budget.max_runtime_seconds), evidence_dir=evidence,
                commands=commands,
            )
            if up.returncode != 0:
                raise RuntimeError("unsafe Compose up failed")
            runtime_started = time.monotonic()
            listed = self._run(
                name="005_project_containers",
                args=[
                    docker_cli, "ps", "-aq", "--filter",
                    f"label=com.docker.compose.project={project}",
                ],
                cwd=bundle, timeout=30, evidence_dir=evidence, commands=commands,
            )
            container_ids = [line.strip() for line in listed.stdout.splitlines() if line.strip()]
            if len(container_ids) != len(policy.service_ids):
                raise RuntimeError("unsafe project container count differs from the approved plan")
            for index, container_id in enumerate(container_ids):
                inspected = self._run(
                    name=f"006_container_{index:03d}",
                    args=[docker_cli, "inspect", container_id], cwd=bundle,
                    timeout=30, evidence_dir=evidence, commands=commands,
                )
                container = json.loads(inspected.stdout)[0]
                labels = container["Config"].get("Labels") or {}
                host = container["HostConfig"]
                violations = []
                if labels.get("benchmark.unsafe.session") != project:
                    violations.append("session_label")
                if labels.get("benchmark.unsafe.generated") != "true":
                    violations.append("unsafe_label")
                if host.get("Privileged"):
                    violations.append("privileged")
                if host.get("NetworkMode") == "host" or host.get("PidMode") == "host" or host.get("IpcMode") == "host":
                    violations.append("host_namespace")
                if host.get("Binds"):
                    violations.append("host_bind")
                if not host.get("ReadonlyRootfs"):
                    violations.append("writable_rootfs")
                if set(host.get("CapAdd") or []) - ALLOWED_CAPABILITIES:
                    violations.append("capabilities")
                if int(host.get("Memory") or 0) <= 0 or int(host.get("Memory") or 0) > policy.effective_limits["memory_mb_per_service"] * 1024 * 1024:
                    violations.append("memory_limit")
                expected_nano_cpus = int(policy.effective_limits["cpu_per_service"] * 1_000_000_000)
                if int(host.get("NanoCpus") or 0) <= 0 or int(host.get("NanoCpus") or 0) > expected_nano_cpus:
                    violations.append("cpu_limit")
                if int(host.get("PidsLimit") or 0) != policy.effective_limits["pids_per_service"]:
                    violations.append("pids_limit")
                tmpfs = host.get("Tmpfs") or {}
                if set(tmpfs) != {"/tmp", "/run"}:
                    violations.append("tmpfs_scope")
                if violations:
                    raise RuntimeError(f"unsafe runtime isolation verification failed: {violations}")
                runtime_snapshot.append({
                    "id": container["Id"], "name": container["Name"],
                    "image": container["Image"], "labels": labels,
                    "host_config": {
                        "privileged": host.get("Privileged"),
                        "network_mode": host.get("NetworkMode"),
                        "pid_mode": host.get("PidMode"),
                        "ipc_mode": host.get("IpcMode"),
                        "binds": host.get("Binds"),
                        "readonly_rootfs": host.get("ReadonlyRootfs"),
                        "memory": host.get("Memory"), "nano_cpus": host.get("NanoCpus"),
                        "pids_limit": host.get("PidsLimit"), "cap_add": host.get("CapAdd"),
                        "security_opt": host.get("SecurityOpt"), "tmpfs": host.get("Tmpfs"),
                    },
                })
            atomic_json(evidence / "runtime_snapshot.json", {
                "schema_version": 1, "containers": runtime_snapshot,
            })
            for index, step in enumerate(plan.steps):
                if runtime_started is None:
                    raise RuntimeError("unsafe runtime clock was not initialized")
                remaining = plan.budget.max_runtime_seconds - int(time.monotonic() - runtime_started)
                if remaining <= 0:
                    raise RuntimeError("unsafe lifecycle exceeded its runtime budget")
                timeout = min(step.timeout_seconds, plan.budget.max_step_seconds, remaining)
                completed = self._run(
                    name=f"step_{index:03d}_{step.step_id}",
                    args=[
                        *compose, "exec", "-T", step.service,
                        "/bin/sh", "-lc", step.shell,
                    ],
                    cwd=bundle, timeout=timeout, evidence_dir=evidence, commands=commands,
                )
                if completed.returncode != step.expected_exit_code:
                    raise RuntimeError(
                        f"unsafe lifecycle step failed: {step.step_id} "
                        f"expected={step.expected_exit_code} actual={completed.returncode}"
                    )
        except Exception as exc:
            error = {"error_type": type(exc).__name__, "error": str(exc)}
        finally:
            self._run(
                name="998_logs", args=[*compose, "logs", "--no-color", "--timestamps", "--tail", "1000"],
                cwd=bundle, timeout=60, evidence_dir=evidence, commands=commands,
            )
            cleanup["attempted"] = True
            self._run(
                name="999_down",
                args=[*compose, "down", "--remove-orphans", "--volumes", "--rmi", "local", "--timeout", "10"],
                cwd=bundle, timeout=180, evidence_dir=evidence, commands=commands,
            )
            remaining_containers = self._run(
                name="cleanup_containers",
                args=[docker_cli, "ps", "-aq", "--filter", f"label=com.docker.compose.project={project}"],
                cwd=bundle, timeout=30, evidence_dir=evidence, commands=commands,
            )
            remaining_networks = self._run(
                name="cleanup_networks",
                args=[docker_cli, "network", "ls", "-q", "--filter", f"label=com.docker.compose.project={project}"],
                cwd=bundle, timeout=30, evidence_dir=evidence, commands=commands,
            )
            cleanup["remaining_containers"] = [item for item in remaining_containers.stdout.splitlines() if item]
            cleanup["remaining_networks"] = [item for item in remaining_networks.stdout.splitlines() if item]
            remaining_images = []
            for index, image in enumerate(image_evidence):
                checked = self._run(
                    name=f"cleanup_image_check_{index:03d}",
                    args=[docker_cli, "image", "inspect", image["name"]],
                    cwd=bundle, timeout=30, evidence_dir=evidence, commands=commands,
                )
                if checked.returncode == 0:
                    remaining_images.append(image["name"])
            if cleanup["remaining_containers"]:
                self._run(
                    name="cleanup_force_containers",
                    args=[docker_cli, "rm", "-f", *cleanup["remaining_containers"]],
                    cwd=bundle, timeout=60, evidence_dir=evidence, commands=commands,
                )
            if cleanup["remaining_networks"]:
                self._run(
                    name="cleanup_force_networks",
                    args=[docker_cli, "network", "rm", *cleanup["remaining_networks"]],
                    cwd=bundle, timeout=60, evidence_dir=evidence, commands=commands,
                )
            if remaining_images:
                self._run(
                    name="cleanup_force_images",
                    args=[docker_cli, "image", "rm", "-f", *remaining_images],
                    cwd=bundle, timeout=120, evidence_dir=evidence, commands=commands,
                )
            post_containers = self._run(
                name="cleanup_verify_containers",
                args=[docker_cli, "ps", "-aq", "--filter", f"label=com.docker.compose.project={project}"],
                cwd=bundle, timeout=30, evidence_dir=evidence, commands=commands,
            )
            post_networks = self._run(
                name="cleanup_verify_networks",
                args=[docker_cli, "network", "ls", "-q", "--filter", f"label=com.docker.compose.project={project}"],
                cwd=bundle, timeout=30, evidence_dir=evidence, commands=commands,
            )
            cleanup["remaining_containers"] = [item for item in post_containers.stdout.splitlines() if item]
            cleanup["remaining_networks"] = [item for item in post_networks.stdout.splitlines() if item]
            remaining_images = []
            for index, image in enumerate(image_evidence):
                checked = self._run(
                    name=f"cleanup_verify_image_{index:03d}",
                    args=[docker_cli, "image", "inspect", image["name"]],
                    cwd=bundle, timeout=30, evidence_dir=evidence, commands=commands,
                )
                if checked.returncode == 0:
                    remaining_images.append(image["name"])
            cleanup["remaining_images"] = remaining_images
            cleanup["verified"] = not any((
                cleanup["remaining_containers"], cleanup["remaining_networks"], remaining_images,
            ))
            atomic_json(evidence / "cleanup.json", {"schema_version": 1, **cleanup})

        status = "complete" if error is None and cleanup["verified"] else "failed"
        result = signed_record({
            "schema_version": 1,
            "unsafe_generated": True,
            "status": status,
            "plan_fingerprint": plan.fingerprint,
            "policy_fingerprint": policy.policy_fingerprint,
            "nl_contract_sha256": nl_contract_sha256(),
            "project": project,
            "service_count": len(policy.service_ids),
            "steps": len(plan.steps),
            "error": error,
            "cleanup": cleanup,
            "qualification_status": "forbidden",
            "publication_status": "forbidden",
            "promotion_eligible": False,
            "ai_invoked_during_execution": False,
            "completed_at": _utcnow().isoformat(),
        }, "execution_fingerprint")
        atomic_json(session / "unsafe_execution_result.json", result)
        return result
