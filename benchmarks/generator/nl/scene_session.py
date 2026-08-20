"""Audited planning and approved delivery for arbitrary declarative scenes."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
from typing import Any, Dict, Mapping

from generator.nl.audit import atomic_json, canonical_sha256, nl_contract_sha256, signed_record
from generator.nl.catalog import build_capability_catalog
from generator.nl.provider import LLMProvider, ProviderResponse
from generator.nl.scene_bridge import (
    analyze_scene_requirements,
    compile_scene_intent,
    validate_scene_manifest,
)
from generator.nl.scene_models import (
    BENCHMARK_SCENE_OUTPUT_SCHEMA,
    BenchmarkSceneIntent,
    validate_scene_provider_output,
)
from generator.nl.scene_provider import SCENE_PROMPT_VERSION, build_scene_messages
from generator.nl.security import inspect_natural_language
from generator.topology.compiler import compile_topology, validate_compiled_output
from generator.topology.registry import output_dir, register_request, spec_dir


SCENE_SESSION_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_.-]{2,95}$")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _read(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _scene_session_id(text: str, seed: str) -> str:
    stamp = _utcnow().strftime("%Y%m%dT%H%M%SZ")
    suffix = hashlib.sha256(f"{text}\0{seed}".encode("utf-8")).hexdigest()[:12]
    return f"scene_{stamp}_{suffix}"


def _cache_key(
    *, text: str, seed: str, provider: LLMProvider, catalog_fingerprint: str,
) -> str:
    return canonical_sha256({
        "text": " ".join(text.split()),
        "seed": seed,
        "provider": provider.provider_id,
        "model": provider.model_id,
        "catalog": catalog_fingerprint,
        "prompt_version": SCENE_PROMPT_VERSION,
        "schema": BENCHMARK_SCENE_OUTPUT_SCHEMA,
    })


class NaturalLanguageScenePlanner:
    def __init__(self, benchmarks_dir: Path, session_root: Path):
        self.benchmarks_dir = benchmarks_dir.resolve()
        self.session_root = session_root.resolve()
        self.session_root.mkdir(parents=True, exist_ok=True)

    def _new_session(self, text: str, seed: str, session_id: str | None) -> Path:
        identity = session_id or _scene_session_id(text, seed)
        if not SCENE_SESSION_PATTERN.fullmatch(identity):
            raise ValueError("invalid natural-language scene session identity")
        path = (self.session_root / identity).resolve()
        path.relative_to(self.session_root)
        if path.exists():
            raise FileExistsError(f"natural-language scene session exists: {path}")
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
        source = {
            "schema_version": 1,
            "mode": "arbitrary_declarative_scene_plan_only",
            "text": text,
            "text_sha256": hashlib.sha256(
                " ".join(text.split()).encode("utf-8")
            ).hexdigest(),
            "seed": seed,
            "created_at": _utcnow().isoformat(),
            "docker_state_changed": False,
        }
        atomic_json(session / "input.json", source)
        input_security = inspect_natural_language(text)
        atomic_json(session / "security_input.json", input_security.to_dict())
        catalog = build_capability_catalog(self.benchmarks_dir)
        atomic_json(session / "capability_snapshot.json", catalog.to_dict())
        if not input_security.allowed:
            return self._finish(session, {
                "status": "blocked", "session": str(session),
                "provider_invoked": False, "security": input_security.to_dict(),
            })

        messages = build_scene_messages(text, catalog.snapshot)
        request = {
            "schema_version": 1,
            "prompt_version": SCENE_PROMPT_VERSION,
            "messages": messages,
            "output_schema": BENCHMARK_SCENE_OUTPUT_SCHEMA,
            "provider": provider.provider_id,
            "model": provider.model_id,
        }
        request["prompt_fingerprint"] = canonical_sha256(request)
        atomic_json(session / "provider_request.json", request)
        cache_key = _cache_key(
            text=text, seed=seed, provider=provider,
            catalog_fingerprint=catalog.fingerprint,
        )
        cache_path = self.session_root / "_scene_cache" / f"{cache_key}.json"
        cache_hit = cache_path.is_file()
        if cache_hit:
            response = ProviderResponse(**_read(cache_path)["response"])
        else:
            try:
                response = provider.complete_structured(
                    messages, BENCHMARK_SCENE_OUTPUT_SCHEMA, seed=seed
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
            validate_scene_provider_output(response.output)
            intent = BenchmarkSceneIntent.from_provider_output(
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
            atomic_json(session / "scene_schema_rejection.json", rejection)
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
        intent_record = {**intent.to_dict(), "scene_fingerprint": intent.fingerprint}
        atomic_json(session / "normalized_scene.json", intent_record)
        objective_security = inspect_natural_language(intent.objective)
        source_matches = secrets.compare_digest(
            intent.source_text_sha256, source["text_sha256"]
        )
        security = {
            "schema_version": 1,
            "allowed": objective_security.allowed and source_matches,
            "objective": objective_security.to_dict(),
            "source_fingerprint_matches": source_matches,
            "shell_or_docker_fields_representable": False,
        }
        atomic_json(session / "security_scene.json", security)
        if not security["allowed"]:
            return self._finish(session, {
                "status": "blocked", "session": str(session),
                "provider_invoked": True, "provider_cache_hit": cache_hit,
                "security": security,
            })
        requirements = analyze_scene_requirements(intent, catalog)
        atomic_json(session / "scene_requirements.json", requirements.to_dict())
        if requirements.status != "ready":
            return self._finish(session, {
                "status": requirements.status, "session": str(session),
                "provider_invoked": True, "provider_cache_hit": cache_hit,
                "scene_fingerprint": intent.fingerprint,
                "requirements": requirements.to_dict(),
            })
        try:
            bridge = compile_scene_intent(intent, catalog)
        except Exception as exc:
            rejection = {
                "schema_version": 1, "allowed": False,
                "error_type": type(exc).__name__, "error": str(exc),
                "scene_fingerprint": intent.fingerprint,
            }
            atomic_json(session / "scene_policy_rejection.json", rejection)
            return self._finish(session, {
                "status": "policy_rejected", "session": str(session),
                "provider_invoked": True, "provider_cache_hit": cache_hit,
                "policy": rejection,
            })
        compiled = session / "compiled"
        atomic_json(compiled / "topology_request.json", bridge.topology_request.to_dict())
        atomic_json(compiled / "topology_plan.json", bridge.topology_plan.to_dict())
        atomic_json(compiled / "benchmark_request.json", bridge.benchmark_request.to_dict())
        atomic_json(compiled / "bridge_plan.json", bridge.to_dict())
        atomic_json(session / "approved_scene.json", intent.to_dict())
        atomic_json(session / "scene_preview.json", bridge.preview)
        token = secrets.token_urlsafe(32)
        challenge = signed_record({
            "schema_version": 1,
            "challenge_kind": "declarative_scene_delivery_v1",
            "scene_fingerprint": intent.fingerprint,
            "bridge_fingerprint": bridge.bridge_fingerprint,
            "catalog_fingerprint": catalog.fingerprint,
            "topology_fingerprint": bridge.topology_plan.fingerprint,
            "token_sha256": hashlib.sha256(token.encode("utf-8")).hexdigest(),
            "issued_at": _utcnow().isoformat(),
            "expires_at": (_utcnow() + timedelta(hours=24)).isoformat(),
            "consumed": False,
            "docker_execution_authorized": False,
            "publication_authorized": False,
        }, "challenge_fingerprint")
        atomic_json(session / "scene_approval_challenge.json", challenge, mode=0o600)
        return self._finish(session, {
            "status": "ready", "session": str(session),
            "approved_scene": str(session / "approved_scene.json"),
            "approval_token": token,
            "approval_expires_at": challenge["expires_at"],
            "scene_fingerprint": intent.fingerprint,
            "bridge_fingerprint": bridge.bridge_fingerprint,
            "provider_invoked": True, "provider_cache_hit": cache_hit,
            "preview": bridge.preview,
        })

    def _finish(self, session: Path, result: Mapping[str, Any]) -> Dict[str, Any]:
        audit = signed_record({
            "schema_version": 1,
            "created_at": _utcnow().isoformat(),
            "nl_contract_sha256": nl_contract_sha256(),
            "status": result["status"],
            "session": str(session),
            "evidence": sorted(
                str(path.relative_to(session)) for path in session.rglob("*.json")
            ),
        }, "audit_fingerprint")
        atomic_json(session / "scene_audit.json", audit)
        output = dict(result)
        output["nl_contract_sha256"] = audit["nl_contract_sha256"]
        output["audit_fingerprint"] = audit["audit_fingerprint"]
        return output


class NaturalLanguageSceneDeliverer:
    def __init__(self, benchmarks_dir: Path, allowed_root: Path):
        self.benchmarks_dir = benchmarks_dir.resolve()
        self.allowed_root = allowed_root.resolve()

    def _scene_path(self, value: Path) -> Path:
        path = value.resolve()
        path.relative_to(self.allowed_root)
        if path.name != "approved_scene.json" or not path.is_file():
            raise ValueError("scene must be approved_scene.json under the session root")
        return path

    @staticmethod
    def _claim(session: Path, challenge: Mapping[str, Any]) -> None:
        path = session / "scene_delivery.claim"
        try:
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError as exc:
            raise ValueError("scene delivery approval has already been claimed") from exc
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump({
                "challenge_fingerprint": challenge["challenge_fingerprint"],
                "claimed_at": _utcnow().isoformat(),
            }, handle, sort_keys=True)
            handle.write("\n")

    def deliver(self, scene_path: Path, approval_token: str) -> Dict[str, Any]:
        path = self._scene_path(scene_path)
        session = path.parent
        intent = BenchmarkSceneIntent.from_dict(_read(path))
        challenge_path = session / "scene_approval_challenge.json"
        challenge = _read(challenge_path)
        if challenge.get("challenge_kind") != "declarative_scene_delivery_v1":
            raise ValueError("approval challenge cannot authorize scene delivery")
        if challenge.get("consumed"):
            raise ValueError("scene delivery approval token has already been consumed")
        supplied = hashlib.sha256(approval_token.encode("utf-8")).hexdigest()
        if not secrets.compare_digest(supplied, challenge["token_sha256"]):
            raise ValueError("scene delivery approval token is invalid")
        if _utcnow() > datetime.fromisoformat(challenge["expires_at"]):
            raise ValueError("scene delivery approval token has expired")
        if challenge.get("docker_execution_authorized") or challenge.get("publication_authorized"):
            raise ValueError("scene delivery token cannot authorize Docker or publication")
        catalog = build_capability_catalog(self.benchmarks_dir)
        bridge = compile_scene_intent(intent, catalog)
        if intent.fingerprint != challenge["scene_fingerprint"]:
            raise ValueError("scene changed after approval")
        if catalog.fingerprint != challenge["catalog_fingerprint"]:
            raise ValueError("capability catalog changed; run scene plan again")
        if bridge.bridge_fingerprint != challenge["bridge_fingerprint"]:
            raise ValueError("scene bridge changed after approval")
        if bridge.topology_plan.fingerprint != challenge["topology_fingerprint"]:
            raise ValueError("topology plan changed after approval")
        topology_specs = spec_dir(intent.topology_id, self.benchmarks_dir)
        topology_output = output_dir(intent.topology_id, self.benchmarks_dir)
        topology_root = topology_output.parent
        if topology_specs.exists() or topology_root.exists():
            raise FileExistsError("scene topology identity is already registered")
        self._claim(session, challenge)
        consumed = dict(challenge)
        consumed["consumed"] = True
        consumed["consumed_at"] = _utcnow().isoformat()
        consumed["challenge_fingerprint"] = ""
        consumed["challenge_fingerprint"] = canonical_sha256(consumed)
        atomic_json(challenge_path, consumed, mode=0o600)
        delivery = session / "scene_delivery"
        delivery.mkdir(parents=True, exist_ok=False)
        error = None
        cleanup = {"attempted": False, "verified": True}
        manifest = None
        handoff = None
        generator_summary = {
            "schema_version": 1,
            "status": "not_requested",
            "reason": "scene bridge delivery boundary is the topology capability manifest",
            "nine_worker_handoff_ready": False,
        }
        try:
            registered = register_request(
                bridge.topology_request, root=self.benchmarks_dir
            )
            if registered.fingerprint != bridge.topology_plan.fingerprint:
                raise RuntimeError("registered topology differs from approved plan")
            compile_topology(registered, root=self.benchmarks_dir)
            manifest = validate_compiled_output(
                registered, root=self.benchmarks_dir
            )
            handoff = validate_scene_manifest(bridge, manifest)
            handoff["manifest_path"] = str(
                topology_output / "topology_manifest.json"
            )
            atomic_json(delivery / "topology_manifest.json", manifest)
            atomic_json(delivery / "manifest_handoff.json", handoff)
            generator_summary["nine_worker_handoff_ready"] = True
            generator_summary["benchmark_request_fingerprint"] = (
                bridge.benchmark_request.fingerprint
            )
            atomic_json(delivery / "downstream_handoff_status.json", generator_summary)
        except Exception as exc:
            error = {"error_type": type(exc).__name__, "error": str(exc)}
            cleanup["attempted"] = True
            for target, allowed_parent in (
                (topology_specs, (self.benchmarks_dir / "topology_specs").resolve()),
                (topology_root, (self.benchmarks_dir / "generated/declarative").resolve()),
            ):
                resolved = target.resolve()
                resolved.relative_to(allowed_parent)
                if resolved.exists():
                    shutil.rmtree(resolved)
            cleanup["verified"] = not topology_specs.exists() and not topology_root.exists()
        status = "delivered" if error is None else "failed"
        result = signed_record({
            "schema_version": 1,
            "status": status,
            "scene_fingerprint": intent.fingerprint,
            "bridge_fingerprint": bridge.bridge_fingerprint,
            "topology_id": intent.topology_id,
            "topology_fingerprint": bridge.topology_plan.fingerprint,
            "manifest_handoff": handoff,
            "generator_summary": generator_summary,
            "error": error,
            "cleanup": cleanup,
            "docker_state_changed": False,
            "execute_lifecycle": False,
            "publication_status": "not_requested",
            "ai_invoked_during_compilation": False,
            "completed_at": _utcnow().isoformat(),
        }, "delivery_fingerprint")
        atomic_json(session / "scene_delivery_result.json", result)
        return result
