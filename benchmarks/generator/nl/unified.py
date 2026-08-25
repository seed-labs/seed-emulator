"""One public NL workflow for isolated arbitrary benchmark generation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Mapping

from generator.nl.audit import atomic_json, canonical_sha256, signed_record
from generator.nl.provider import LLMProvider
from generator.nl.unsafe_models import UnsafeScenarioPlan
from generator.nl.unsafe_session import (
    UnsafeNaturalLanguageExecutor,
    UnsafeNaturalLanguagePlanner,
)


UNIFIED_SCHEMA_VERSION = 1


def _read(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _plan_value(session: Path, result: Mapping[str, Any]) -> Dict[str, Any]:
    unsafe_path = Path(str(result["unsafe_plan"])).resolve()
    unsafe_path.relative_to(session.resolve())
    value = {
        "schema_version": UNIFIED_SCHEMA_VERSION,
        "kind": "arbitrary_benchmark",
        "execution_class": "isolated_arbitrary_code",
        "session": str(session.resolve()),
        "unsafe_plan": str(unsafe_path),
        "plan_fingerprint": str(result["plan_fingerprint"]),
        "policy_fingerprint": str(result["policy_fingerprint"]),
        "generated_dimensions": {
            "topology": True, "software": True, "faults": True, "tests": True,
        },
        "safety_analysis": "passed",
        "deployment": "isolated_compose_project",
        "lifecycle": ["baseline", "inject", "observe", "recover", "verify"],
        "evidence_collection": "required",
        "scoring_preparation": "pending_execution",
        "promotion_eligible": False,
    }
    value["unified_plan_fingerprint"] = canonical_sha256(value)
    return value


class UnifiedNaturalLanguagePlanner:
    """Generate the arbitrary benchmark IR and route it to the isolated backend."""

    def __init__(self, benchmarks_dir: Path, session_root: Path):
        self.benchmarks_dir = benchmarks_dir.resolve()
        self.session_root = session_root.resolve()

    def plan(
        self, text: str, *, provider: LLMProvider, seed: str,
        session_id: str | None = None,
    ) -> Dict[str, Any]:
        result = UnsafeNaturalLanguagePlanner(
            self.benchmarks_dir, self.session_root,
        ).plan(text, provider=provider, seed=seed, session_id=session_id)
        output = dict(result)
        output["workflow"] = "arbitrary_benchmark_v1"
        output["execution_class"] = "isolated_arbitrary_code"
        if result["status"] != "ready":
            return output
        session = Path(str(result["session"])).resolve()
        plan = _plan_value(session, result)
        path = session / "benchmark_plan.json"
        atomic_json(path, plan)
        preview = dict(output.get("preview", {}))
        preview.update({
            "workflow": plan["kind"],
            "execution_class": plan["execution_class"],
            "generated_dimensions": plan["generated_dimensions"],
            "lifecycle": plan["lifecycle"],
            "scoring_preparation": "after_successful_execution",
        })
        output["plan"] = str(path)
        output["unified_plan_fingerprint"] = plan["unified_plan_fingerprint"]
        output["preview"] = preview
        return output


class UnifiedNaturalLanguageExecutor:
    """Execute one approved unified plan and prepare evidence for scoring."""

    def __init__(self, benchmarks_dir: Path, allowed_root: Path):
        self.benchmarks_dir = benchmarks_dir.resolve()
        self.allowed_root = allowed_root.resolve()

    def _load_plan(self, value: Path) -> tuple[Path, Dict[str, Any]]:
        path = value.resolve()
        path.relative_to(self.allowed_root)
        if path.name != "benchmark_plan.json" or not path.is_file():
            raise ValueError("plan must be benchmark_plan.json under the NL session root")
        data = _read(path)
        fingerprint = data.pop("unified_plan_fingerprint", None)
        if set(data) != {
            "schema_version", "kind", "execution_class", "session", "unsafe_plan",
            "plan_fingerprint", "policy_fingerprint", "generated_dimensions",
            "safety_analysis", "deployment", "lifecycle", "evidence_collection",
            "scoring_preparation", "promotion_eligible",
        }:
            raise ValueError("invalid unified benchmark plan keys")
        if data["schema_version"] != 1 or data["kind"] != "arbitrary_benchmark":
            raise ValueError("unsupported unified benchmark plan")
        if data["execution_class"] != "isolated_arbitrary_code":
            raise ValueError("unsupported unified execution class")
        if not isinstance(fingerprint, str) or fingerprint != canonical_sha256(data):
            raise ValueError("unified benchmark plan fingerprint mismatch")
        session = path.parent.resolve()
        if Path(str(data["session"])).resolve() != session:
            raise ValueError("unified benchmark session binding mismatch")
        unsafe_path = Path(str(data["unsafe_plan"])).resolve()
        unsafe_path.relative_to(session)
        if unsafe_path != session / "unsafe_plan.json":
            raise ValueError("unified benchmark backend plan binding is invalid")
        unsafe_value = _read(unsafe_path)
        unsafe_fingerprint = unsafe_value.pop("plan_fingerprint", None)
        unsafe = UnsafeScenarioPlan.from_dict(unsafe_value)
        if unsafe.fingerprint != unsafe_fingerprint or unsafe.fingerprint != data["plan_fingerprint"]:
            raise ValueError("unified benchmark backend plan changed")
        data["unified_plan_fingerprint"] = fingerprint
        return unsafe_path, data

    @staticmethod
    def _evidence_manifest(session: Path) -> Dict[str, Any]:
        excluded = {"evidence_manifest.json", "benchmark_execution_result.json"}
        files = []
        for path in sorted(item for item in session.rglob("*") if item.is_file()):
            if path.name in excluded:
                continue
            content = path.read_bytes()
            files.append({
                "path": str(path.relative_to(session)), "bytes": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
            })
        value = {"schema_version": 1, "files": files}
        value["evidence_fingerprint"] = canonical_sha256(value)
        return value

    def execute(
        self, plan_path: Path, approval_token: str, *, acknowledge_arbitrary_code: bool,
    ) -> Dict[str, Any]:
        unsafe_path, unified = self._load_plan(plan_path)
        result = UnsafeNaturalLanguageExecutor(
            self.benchmarks_dir, self.allowed_root,
        ).execute(
            unsafe_path, approval_token,
            acknowledge_arbitrary_code=acknowledge_arbitrary_code,
        )
        session = plan_path.resolve().parent
        unsafe_value = _read(unsafe_path)
        unsafe_value.pop("plan_fingerprint", None)
        unsafe = UnsafeScenarioPlan.from_dict(unsafe_value)
        phases = sorted({step.phase for step in unsafe.steps})
        required = {"baseline", "inject", "recover", "verify"}
        lifecycle_complete = required <= set(phases)
        ready = result["status"] == "complete" and result["cleanup"]["verified"] and lifecycle_complete
        scoring = signed_record({
            "schema_version": 1,
            "status": "ready" if ready else "not_ready",
            "execution_fingerprint": result["execution_fingerprint"],
            "unified_plan_fingerprint": unified["unified_plan_fingerprint"],
            "phase_coverage": phases,
            "required_phase_coverage": sorted(required),
            "tests_total": sum(step.phase in {"baseline", "observe", "verify"} for step in unsafe.steps),
            "tests_passed": sum(step.phase in {"baseline", "observe", "verify"} for step in unsafe.steps) if ready else 0,
            "provisional_score": 100.0 if ready else 0.0,
            "promotion_eligible": False,
            "reason": "isolated arbitrary-code evidence is score-ready but requires later capability promotion",
        }, "scoring_fingerprint")
        atomic_json(session / "scoring_preparation.json", scoring)
        evidence = self._evidence_manifest(session)
        atomic_json(session / "evidence_manifest.json", evidence)
        output = signed_record({
            "schema_version": 1,
            "status": result["status"],
            "workflow": "arbitrary_benchmark_v1",
            "execution_class": "isolated_arbitrary_code",
            "unified_plan_fingerprint": unified["unified_plan_fingerprint"],
            "backend_execution_fingerprint": result["execution_fingerprint"],
            "lifecycle": {"phases": phases, "complete": lifecycle_complete},
            "cleanup": result["cleanup"],
            "evidence_manifest": str(session / "evidence_manifest.json"),
            "evidence_fingerprint": evidence["evidence_fingerprint"],
            "scoring_preparation": str(session / "scoring_preparation.json"),
            "scoring_status": scoring["status"],
            "provisional_score": scoring["provisional_score"],
            "promotion_eligible": False,
            "ai_invoked_during_execution": False,
        }, "execution_fingerprint")
        atomic_json(session / "benchmark_execution_result.json", output)
        return output
