"""Audited NL planning sessions, one-time approval, and real execution."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
from typing import Any, Dict, Mapping

from generator.bundle.pipeline import ProductionGenerator
from generator.bundle.request import BenchmarkRequest
from generator.nl.audit import atomic_json, canonical_sha256, nl_contract_sha256, signed_record
from generator.nl.catalog import build_capability_catalog
from generator.nl.clarification import analyze_clarifications
from generator.nl.compiler import compile_intent
from generator.nl.models import BenchmarkIntent
from generator.nl.prompts import PROMPT_VERSION, build_messages
from generator.nl.provider import LLMProvider, ProviderResponse
from generator.nl.schema import BENCHMARK_INTENT_OUTPUT_SCHEMA, validate_provider_output
from generator.nl.security import inspect_intent, inspect_natural_language
from generator.topology.bindings import load_capability_manifest
from generator.topology.compiler import validate_compiled_output
from generator.topology.registry import load_plan, output_dir


SESSION_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_.-]{2,95}$")
SNAP_DOCKER_WRAPPER = Path("/snap/bin/docker")
SNAP_DOCKER_BINARY = Path("/snap/docker/current/bin/docker")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _read(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_blind_receipt(receipt: Mapping[str, Any]) -> None:
    """Fail closed unless a lifecycle receipt proves an untainted no-AI blind run."""
    required = {
        "ai_invoked": False,
        "blind_mode": True,
        "passed": True,
        "topology_tainted": False,
    }
    violations = [
        field for field, expected in required.items()
        if receipt.get(field) is not expected
    ]
    if violations:
        raise RuntimeError(
            f"NL-generated lifecycle receipt violates blind/no-AI policy: {sorted(violations)}"
        )


def _session_id(text: str, seed: str) -> str:
    stamp = _utcnow().strftime("%Y%m%dT%H%M%SZ")
    suffix = hashlib.sha256(f"{text}\0{seed}".encode("utf-8")).hexdigest()[:12]
    return f"nl_{stamp}_{suffix}"


def _provider_cache_key(
    *, text: str, seed: str, provider: LLMProvider, catalog_fingerprint: str,
) -> str:
    return canonical_sha256({
        "text": " ".join(text.split()),
        "seed": seed,
        "provider": provider.provider_id,
        "model": provider.model_id,
        "catalog_fingerprint": catalog_fingerprint,
        "prompt_version": PROMPT_VERSION,
        "schema": BENCHMARK_INTENT_OUTPUT_SCHEMA,
    })


class NaturalLanguagePlanner:
    def __init__(self, benchmarks_dir: Path, session_root: Path):
        self.benchmarks_dir = benchmarks_dir.resolve()
        self.session_root = session_root.resolve()
        self.session_root.mkdir(parents=True, exist_ok=True)

    def _new_session(self, text: str, seed: str, session_id: str | None) -> Path:
        identity = session_id or _session_id(text, seed)
        if not SESSION_PATTERN.fullmatch(identity):
            raise ValueError("invalid NL session identity")
        path = (self.session_root / identity).resolve()
        path.relative_to(self.session_root)
        if path.exists():
            raise FileExistsError(f"NL session already exists: {path}")
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
            "text": text,
            "text_sha256": hashlib.sha256(" ".join(text.split()).encode("utf-8")).hexdigest(),
            "seed": seed,
            "created_at": created,
        }
        atomic_json(session / "input.json", source)
        initial_security = inspect_natural_language(text)
        atomic_json(session / "security_input.json", initial_security.to_dict())
        catalog = build_capability_catalog(self.benchmarks_dir)
        atomic_json(session / "capability_snapshot.json", catalog.to_dict())
        if not initial_security.allowed:
            result = self._finish(session, {
                "status": "blocked", "session": str(session),
                "security": initial_security.to_dict(),
                "provider_invoked": False,
            })
            return result

        messages = build_messages(text, catalog.snapshot)
        prompt_record = {
            "schema_version": 1,
            "prompt_version": PROMPT_VERSION,
            "messages": messages,
            "output_schema": BENCHMARK_INTENT_OUTPUT_SCHEMA,
            "provider": provider.provider_id,
            "model": provider.model_id,
        }
        prompt_record["prompt_fingerprint"] = canonical_sha256(prompt_record)
        atomic_json(session / "provider_request.json", prompt_record)

        cache_key = _provider_cache_key(
            text=text, seed=seed, provider=provider, catalog_fingerprint=catalog.fingerprint
        )
        cache_path = self.session_root / "_cache" / f"{cache_key}.json"
        cache_hit = cache_path.is_file()
        if cache_hit:
            response = ProviderResponse(**_read(cache_path)["response"])
        else:
            response = provider.complete_structured(
                messages, BENCHMARK_INTENT_OUTPUT_SCHEMA, seed=seed
            )
            validate_provider_output(response.output)
            atomic_json(cache_path, {"schema_version": 1, "cache_key": cache_key, "response": response.to_dict()})
        validate_provider_output(response.output)
        atomic_json(session / "provider_response.json", response.to_dict())
        intent = BenchmarkIntent.from_provider_output(
            response.output,
            source_text=text,
            seed=seed,
            provider_model=f"{response.provider}:{response.model}",
        )
        atomic_json(session / "normalized_intent.json", {
            **intent.to_dict(), "intent_fingerprint": intent.fingerprint
        })
        intent_security = inspect_intent(intent, text)
        atomic_json(session / "security_intent.json", intent_security.to_dict())
        if not intent_security.allowed:
            return self._finish(session, {
                "status": "blocked", "session": str(session),
                "security": intent_security.to_dict(),
                "provider_invoked": True, "provider_cache_hit": cache_hit,
            })

        clarification = analyze_clarifications(intent, catalog)
        atomic_json(session / "clarification.json", clarification.to_dict())
        if clarification.status != "ready":
            return self._finish(session, {
                "status": clarification.status,
                "session": str(session),
                "intent_fingerprint": intent.fingerprint,
                "clarification": clarification.to_dict(),
                "provider_invoked": True,
                "provider_cache_hit": cache_hit,
            })

        compiled = compile_intent(intent, catalog)
        compiled_dir = session / "compiled"
        atomic_json(compiled_dir / "topology_request.json", compiled.topology_request.to_dict())
        atomic_json(compiled_dir / "benchmark_request.json", compiled.benchmark_request.to_dict())
        atomic_json(session / "approved_intent.json", intent.to_dict())
        atomic_json(session / "preview.json", compiled.preview)
        capabilities = load_capability_manifest(compiled.benchmark_request.topology_id)
        generator_summary = ProductionGenerator(self.benchmarks_dir).generate(
            compiled.benchmark_request,
            session / "bundle_plan",
            capabilities=capabilities,
        )
        if generator_summary["qualification_status"] != "not_requested":
            raise RuntimeError("nl-plan unexpectedly executed a lifecycle")
        atomic_json(session / "generator_plan_summary.json", generator_summary)

        token = secrets.token_urlsafe(32)
        challenge = signed_record({
            "schema_version": 1,
            "intent_fingerprint": intent.fingerprint,
            "plan_fingerprint": compiled.plan_fingerprint,
            "catalog_fingerprint": catalog.fingerprint,
            "token_sha256": hashlib.sha256(token.encode("utf-8")).hexdigest(),
            "issued_at": _utcnow().isoformat(),
            "expires_at": (_utcnow() + timedelta(hours=24)).isoformat(),
            "consumed": False,
            "publish_authorized": intent.publish_requested,
        }, "challenge_fingerprint")
        atomic_json(session / "approval_challenge.json", challenge, mode=0o600)
        return self._finish(session, {
            "status": "ready",
            "session": str(session),
            "approved_intent": str(session / "approved_intent.json"),
            "approval_token": token,
            "approval_expires_at": challenge["expires_at"],
            "intent_fingerprint": intent.fingerprint,
            "plan_fingerprint": compiled.plan_fingerprint,
            "provider_invoked": True,
            "provider_cache_hit": cache_hit,
            "preview": compiled.preview,
            "generator_plan": generator_summary,
        })

    def _finish(self, session: Path, result: Mapping[str, Any]) -> Dict[str, Any]:
        audit = signed_record({
            "schema_version": 1,
            "created_at": _utcnow().isoformat(),
            "nl_contract_sha256": nl_contract_sha256(),
            "status": result["status"],
            "session": str(session),
            "evidence": sorted(str(path.relative_to(session)) for path in session.rglob("*.json")),
        }, "audit_fingerprint")
        atomic_json(session / "audit.json", audit)
        output = dict(result)
        output["nl_contract_sha256"] = audit["nl_contract_sha256"]
        output["audit_fingerprint"] = audit["audit_fingerprint"]
        return output


class NaturalLanguageExecutor:
    def __init__(self, benchmarks_dir: Path, allowed_root: Path):
        self.benchmarks_dir = benchmarks_dir.resolve()
        self.allowed_root = allowed_root.resolve()

    def _intent_path(self, value: Path) -> Path:
        path = value.resolve()
        path.relative_to(self.allowed_root)
        if path.name != "approved_intent.json" or not path.is_file():
            raise ValueError("intent must be an approved_intent.json under the allowed root")
        return path

    def execute(
        self, intent_path: Path, approval_token: str, *, release_version: str = "1.0.0",
    ) -> Dict[str, Any]:
        path = self._intent_path(intent_path)
        session = path.parent
        intent = BenchmarkIntent.from_dict(_read(path))
        challenge_path = session / "approval_challenge.json"
        challenge = _read(challenge_path)
        if challenge.get("consumed"):
            raise ValueError("approval token has already been consumed")
        supplied_token_hash = hashlib.sha256(approval_token.encode("utf-8")).hexdigest()
        if not secrets.compare_digest(supplied_token_hash, challenge["token_sha256"]):
            raise ValueError("approval token is invalid")
        if _utcnow() > datetime.fromisoformat(challenge["expires_at"]):
            raise ValueError("approval token has expired")
        if challenge["intent_fingerprint"] != intent.fingerprint:
            raise ValueError("approval challenge targets another intent")

        catalog = build_capability_catalog(self.benchmarks_dir)
        compiled = compile_intent(intent, catalog)
        if catalog.fingerprint != challenge["catalog_fingerprint"]:
            raise ValueError("capability catalog changed; run nl-plan again")
        if compiled.plan_fingerprint != challenge["plan_fingerprint"]:
            raise ValueError("compiled plan changed; run nl-plan again")

        consumed = dict(challenge)
        consumed["consumed"] = True
        consumed["consumed_at"] = _utcnow().isoformat()
        consumed["challenge_fingerprint"] = ""
        consumed["challenge_fingerprint"] = canonical_sha256(consumed)
        atomic_json(challenge_path, consumed, mode=0o600)

        request_value = compiled.benchmark_request.to_dict()
        request_value["execute_lifecycle"] = True
        request_value["publish"] = bool(intent.publish_requested)
        request = BenchmarkRequest.from_dict(request_value)
        plan = load_plan(request.topology_id)
        validate_compiled_output(plan)
        compose_file = output_dir(request.topology_id) / "docker-compose.yml"
        if not compose_file.is_file():
            raise ValueError("compiled topology Compose file is missing")
        workspace = session / "execution"
        if workspace.exists():
            raise FileExistsError("NL execution workspace already exists")

        compose_cli = str(SNAP_DOCKER_WRAPPER) if SNAP_DOCKER_WRAPPER.is_file() else "docker"
        compose = [compose_cli, "compose", "-f", str(compose_file)]
        subprocess.run(compose + ["up", "-d"], cwd=self.benchmarks_dir, check=True)
        original_path = os.environ.get("PATH", "")
        if SNAP_DOCKER_BINARY.is_file() and os.access(SNAP_DOCKER_BINARY, os.X_OK):
            os.environ["PATH"] = f"{SNAP_DOCKER_BINARY.parent}:{original_path}"
        try:
            summary = ProductionGenerator(self.benchmarks_dir).generate(
                request,
                workspace,
                capabilities=load_capability_manifest(request.topology_id),
                release_version=release_version,
            )
        finally:
            os.environ["PATH"] = original_path
            subprocess.run(
                compose + ["down", "--remove-orphans"],
                cwd=self.benchmarks_dir,
                check=False,
            )
        qualification = _read(workspace / "qualification.json")
        receipts = []
        for reference in qualification["receipts"]:
            receipt = _read(Path(reference["path"]))
            validate_blind_receipt(receipt)
            receipts.append({
                "run_id": receipt["run_id"], "passed": receipt["passed"],
                "ai_invoked": receipt["ai_invoked"], "blind_mode": receipt["blind_mode"],
                "topology_tainted": receipt["topology_tainted"],
            })
        result = signed_record({
            "schema_version": 1,
            "status": "complete",
            "intent_fingerprint": intent.fingerprint,
            "plan_fingerprint": compiled.plan_fingerprint,
            "nl_contract_sha256": nl_contract_sha256(),
            "generator_summary": summary,
            "qualification_status": qualification["status"],
            "receipts": receipts,
            "ai_invoked": False,
            "completed_at": _utcnow().isoformat(),
        }, "execution_fingerprint")
        atomic_json(session / "execution_result.json", result)
        return result
