"""Shared deterministic helpers for semantic fault drivers."""

import hashlib
import json
from typing import Any

from benchmark_agent.models import FaultCapabilityBinding, FaultCapabilityProposal


def fingerprint(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def binding(
    proposal: FaultCapabilityProposal,
    facts: dict[str, Any],
    evidence: dict[str, Any],
    *,
    driver: str,
    baseline_probe: dict[str, Any],
    inject_operation: dict[str, Any],
    recovery_operation: dict[str, Any],
    candidate_operations: list[dict[str, Any]],
) -> FaultCapabilityBinding:
    evidence_fingerprint = fingerprint(evidence)
    identity = {
        "proposal": proposal.model_dump(),
        "topology_fingerprint": facts["fingerprint"],
        "evidence_fingerprint": evidence_fingerprint,
    }
    return FaultCapabilityBinding(
        binding_id="binding-" + fingerprint(identity)[:20],
        fault_kind=proposal.fault_kind,
        target_service=proposal.target_service,
        driver=driver,
        baseline_probe=baseline_probe,
        inject_operation=inject_operation,
        recovery_operation=recovery_operation,
        candidate_operations=candidate_operations,
        evidence_snapshot=evidence,
        topology_fingerprint=facts["fingerprint"],
        evidence_fingerprint=evidence_fingerprint,
    )


def require(value: bool, message: str) -> None:
    if not value:
        raise ValueError(message)
