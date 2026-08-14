"""Deterministic ambiguity detection and extension-proposal routing."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Tuple

from generator.nl.catalog import CapabilityCatalog
from generator.nl.models import BenchmarkIntent


@dataclass(frozen=True)
class ClarificationQuestion:
    code: str
    field: str
    question: str


@dataclass(frozen=True)
class ClarificationResult:
    status: str
    questions: Tuple[ClarificationQuestion, ...]
    extension_proposals: Tuple[Dict[str, Any], ...]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "questions": [asdict(item) for item in self.questions],
            "extension_proposals": list(self.extension_proposals),
        }


def analyze_clarifications(
    intent: BenchmarkIntent, catalog: CapabilityCatalog,
) -> ClarificationResult:
    questions = []
    extensions = []
    if not intent.applications:
        questions.append(ClarificationQuestion(
            "missing_applications", "applications", "请指定至少一个应用，例如 nginx、bind9 或 postgresql。"
        ))
    if intent.difficulty is None:
        questions.append(ClarificationQuestion(
            "missing_difficulty", "difficulty", "请指定难度：easy、medium、hard 或 expert。"
        ))
    if not intent.fault_types or intent.fault_count < 1:
        questions.append(ClarificationQuestion(
            "missing_faults", "fault_types", "请指定至少一种故障，例如延迟、丢包或容器停止。"
        ))
    if intent.fault_count > len(intent.applications) and intent.applications:
        questions.append(ClarificationQuestion(
            "fault_count_exceeds_applications", "fault_count", "故障数量不能超过所选应用数量。"
        ))
    if intent.fault_count and len(intent.fault_types) > intent.fault_count:
        questions.append(ClarificationQuestion(
            "fault_type_count_conflict", "fault_count", "故障类型数量超过声明的故障数量，请确认组合。"
        ))
    unsupported_apps = sorted(set(intent.applications) - set(catalog.application_ids))
    unsupported_faults = sorted(set(intent.fault_types) - set(catalog.fault_ids))
    unknown = sorted(set(intent.unknown_requirements) | set(unsupported_apps) | set(unsupported_faults))
    for item in unknown:
        extensions.append({
            "requirement": item,
            "status": "human_review_required",
            "needed_components": [
                "ApplicationTemplate or capability mapping",
                "FaultDriver when new fault semantics are required",
                "workload/probe tests",
                "no-AI lifecycle evidence",
            ],
        })
    if intent.topology_id and intent.topology_id not in catalog.topology_ids:
        extensions.append({
            "requirement": intent.topology_id,
            "status": "human_review_required",
            "needed_components": ["TopologyRequest", "resource budget", "compiled capability manifest"],
        })
    if extensions:
        status = "extension_required"
    elif questions:
        status = "needs_clarification"
    else:
        selected = (
            catalog.topology(intent.topology_id)
            if intent.topology_id
            else catalog.select_topology(
                intent.applications, observer_required=intent.observer_required, scale=intent.scale
            )
        )
        if selected is None or not set(intent.applications) <= set(selected["application_templates"]):
            status = "extension_required"
            extensions.append({
                "requirement": "topology_application_capacity",
                "status": "human_review_required",
                "needed_components": [
                    "TopologyRequest with selected applications",
                    "resource budget and address plan",
                    "compiled capability manifest",
                ],
            })
        else:
            status = "ready"
    return ClarificationResult(status, tuple(questions), tuple(extensions))
