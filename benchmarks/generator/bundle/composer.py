"""Conflict-aware deterministic composition of Bundle fault candidates."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from generator.bundle.request import BenchmarkRequest
from generator.faults.compiler import compile_fault_set
from generator.faults.models import FaultSpec


@dataclass(frozen=True)
class ComposedFaultSet:
    candidates: Tuple[Mapping[str, Any], ...]
    specs: Tuple[FaultSpec, ...]
    relationship: str


def _dependencies(index: int, specs: Sequence[FaultSpec], relationship: str):
    if index == 0 or relationship == "independent":
        return ()
    if relationship == "cascading":
        return (specs[index - 1].fault_id,)
    # Mixed sets intentionally contain both dependent and independent roots.
    return (specs[index - 1].fault_id,) if index % 2 == 1 else ()


def _specs(
    candidates: Sequence[Mapping[str, Any]], request: BenchmarkRequest,
    protected_asset: str,
) -> Tuple[FaultSpec, ...]:
    result = []
    for index, candidate in enumerate(candidates):
        template_id = str(candidate["template_id"])
        result.append(FaultSpec(
            fault_id=f"fault_{index + 1:02d}_{template_id}",
            fault_type=str(candidate["fault_type"]),
            selector=dict(candidate["selector"]),
            parameters=dict(candidate["parameters"]),
            expectations={
                "must_break": list(candidate["must_break"]),
                "must_preserve": ["observer_availability"],
            },
            safety={
                "max_affected_assets": request.fault_count,
                "max_affected_asns": request.fault_count,
                "protected_assets": [protected_asset],
                "require_recovery": True,
            },
            seed=f"{request.seed}:{template_id}:{index}",
            schedule={"at_seconds": 0, "duration_seconds": 0},
            depends_on=_dependencies(index, result, request.fault_relationship),
        ))
    return tuple(result)


def compose_fault_candidates(
    candidates: Sequence[Mapping[str, Any]], request: BenchmarkRequest,
    capabilities: Mapping[str, Any], *, protected_asset: str,
) -> ComposedFaultSet:
    """Greedily maximize coverage while rejecting compiler-level conflicts."""
    if not 1 <= request.fault_count <= len(candidates):
        raise ValueError("fault combination count is outside candidate range")
    remaining = sorted(candidates, key=lambda item: str(item["candidate_id"]))
    selected = []
    covered = set()
    rejection_reasons = []
    while len(selected) < request.fault_count:
        compatible = []
        for candidate in remaining:
            proposed = [*selected, candidate]
            specs = _specs(proposed, request, protected_asset)
            relationship = "single" if len(specs) == 1 else request.fault_relationship
            if relationship == "mixed" and len(specs) < 3:
                relationship = "cascading"
            try:
                compile_fault_set(
                    specs, capabilities, relationship=relationship
                )
            except ValueError as exc:
                rejection_reasons.append(
                    f"{candidate['candidate_id']}: {exc}"
                )
                continue
            features = {
                f"driver:{candidate['fault_type']}",
                f"asset:{candidate['asset']}",
                *(f"expectation:{x}" for x in candidate.get("must_break", ())),
            }
            compatible.append((
                len(features - covered), str(candidate["candidate_id"]),
                candidate, features,
            ))
        if not compatible:
            reasons = "; ".join(sorted(set(rejection_reasons))[-8:])
            raise ValueError(
                f"only composed {len(selected)}/{request.fault_count} "
                f"conflict-free faults: {reasons}"
            )
        _gain, _identity, chosen, features = sorted(
            compatible, key=lambda row: (-row[0], row[1])
        )[0]
        selected.append(chosen); covered.update(features); remaining.remove(chosen)
    specs = _specs(selected, request, protected_asset)
    relationship = "single" if len(specs) == 1 else request.fault_relationship
    # Compile once more as the final fail-closed composition contract.
    compile_fault_set(specs, capabilities, relationship=relationship)
    return ComposedFaultSet(tuple(selected), specs, relationship)
