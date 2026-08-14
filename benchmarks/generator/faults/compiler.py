"""Resolve FaultSpec selectors and compile safe deterministic fault plans."""

from __future__ import annotations

from dataclasses import replace
import re
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from generator.faults.drivers import get_driver
from generator.faults.models import CompiledFaultPlan, FaultAction, FaultSpec, canonical_sha256


FAULT_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_.-]{2,95}$")


def _assets(capabilities: Mapping[str, Any]) -> List[Mapping[str, Any]]:
    assets = capabilities.get("assets")
    if not isinstance(assets, list) or not assets:
        raise ValueError("capability manifest has no assets")
    return [item for item in assets if isinstance(item, Mapping)]


def resolve_targets(
    spec: FaultSpec,
    capabilities: Mapping[str, Any],
) -> Tuple[Mapping[str, Any], ...]:
    """Resolve a bounded selector without depending on container naming."""
    selector = spec.selector
    allowed = {
        "container", "role", "asn", "interface", "choose",
        "software", "fault_profile",
    }
    if set(selector) - allowed:
        raise ValueError(f"unsupported selector keys={sorted(set(selector) - allowed)}")
    candidates = _assets(capabilities)
    if "container" in selector:
        candidates = [x for x in candidates if x.get("container") == selector["container"]]
    if "role" in selector:
        role = str(selector["role"])
        candidates = [x for x in candidates if role in str(x.get("role", ""))]
    if "asn" in selector:
        values = selector["asn"] if isinstance(selector["asn"], list) else [selector["asn"]]
        asns = {int(item) for item in values}
        candidates = [x for x in candidates if int(x.get("asn", -1)) in asns]
    if "interface" in selector:
        interface = str(selector["interface"])
        candidates = [
            x for x in candidates
            if any(str(i.get("name")) == interface for i in x.get("interfaces", []))
        ]
    if "software" in selector:
        software_id = str(selector["software"])
        candidates = [
            x for x in candidates
            if any(
                item.get("software_id") == software_id
                for item in x.get("software", ())
            )
        ]
    if "fault_profile" in selector:
        profile_id = str(selector["fault_profile"])
        candidates = [
            x for x in candidates
            if any(
                profile.get("profile_id") == profile_id
                for software in x.get("software", ())
                for profile in software.get("fault_profiles", ())
            )
        ]
    candidates.sort(key=lambda x: str(x.get("container", "")))
    choose = int(selector.get("choose", 1))
    if not 1 <= choose <= 64:
        raise ValueError("FaultSpec v1 choose must be between 1 and 64")
    if len(candidates) < choose:
        raise ValueError(f"selector matched {len(candidates)}/{choose} required assets")
    # Seeded rotation makes broad selectors deterministic and reproducible.
    if len(candidates) > choose:
        seed_value = int(canonical_sha256({"seed": spec.seed})[:16], 16)
        offset = seed_value % len(candidates)
        candidates = candidates[offset:] + candidates[:offset]
    return tuple(candidates[:choose])


def _validate_fault_spec(spec: FaultSpec) -> None:
    if spec.schema_version != 1 or not FAULT_ID_PATTERN.fullmatch(spec.fault_id):
        raise ValueError("invalid FaultSpec v1 identity")
    allowed_schedule = {"at_seconds", "duration_seconds"}
    if set(spec.schedule) - allowed_schedule:
        raise ValueError("unsupported FaultSpec v1 schedule")
    if float(spec.schedule.get("at_seconds", 0)) < 0:
        raise ValueError("fault schedule cannot start before zero")
    if float(spec.schedule.get("duration_seconds", 0)) < 0:
        raise ValueError("fault duration cannot be negative")
    allowed_safety = {"max_affected_assets", "max_affected_asns", "protected_assets", "require_recovery"}
    if set(spec.safety) - allowed_safety:
        raise ValueError("unsupported FaultSpec v1 safety key")
    if spec.safety.get("require_recovery", True) is not True:
        raise ValueError("all generated faults must require recovery")


def compile_fault(spec: FaultSpec, capabilities: Mapping[str, Any]) -> CompiledFaultPlan:
    return compile_fault_set((spec,), capabilities, relationship="single")


def compile_fault_set(
    specs: Sequence[FaultSpec],
    capabilities: Mapping[str, Any],
    *,
    relationship: str = "independent",
) -> CompiledFaultPlan:
    """Compile, impact-check and conflict-check one or more fault specs."""
    if not specs:
        raise ValueError("fault set must not be empty")
    if relationship not in {"single", "independent", "cascading", "mixed"}:
        raise ValueError("unsupported fault relationship")
    if len(specs) == 1 and relationship != "single":
        relationship = "single"
    ids = [item.fault_id for item in specs]
    if len(ids) != len(set(ids)):
        raise ValueError("fault ids must be unique")
    actions: List[FaultAction] = []
    action_ids_by_fault: Dict[str, Tuple[str, ...]] = {}
    asset_by_container = {
        str(item.get("container")): item for item in _assets(capabilities)
    }
    for index, spec in enumerate(specs):
        _validate_fault_spec(spec)
        unknown_dependencies = set(spec.depends_on) - set(ids[:index])
        if unknown_dependencies:
            raise ValueError(f"unknown or forward dependencies={sorted(unknown_dependencies)}")
        driver = get_driver(spec.fault_type)
        discovered = driver.discover(spec, capabilities)
        scoped_capabilities = dict(capabilities)
        scoped_capabilities["assets"] = list(discovered)
        targets = resolve_targets(spec, scoped_capabilities)
        protected = set(spec.safety.get("protected_assets", ()))
        selected = {str(item["container"]) for item in targets}
        if selected & protected:
            raise ValueError("selector includes a protected asset")
        dependency_actions = tuple(
            action_id
            for dependency in spec.depends_on
            for action_id in action_ids_by_fault[dependency]
        )
        generated = []
        for target_index, target in enumerate(targets):
            action = driver.plan(spec, (target,))
            if len(targets) > 1:
                action = replace(
                    action,
                    action_id=f"{action.action_id}-{target_index + 1:02d}",
                )
            driver.precheck(action)
            generated.append(replace(
                action, depends_on=dependency_actions,
                at_seconds=float(spec.schedule.get("at_seconds", 0)),
                duration_seconds=float(spec.schedule.get("duration_seconds", 0)),
            ))
        action_ids_by_fault[spec.fault_id] = tuple(
            item.action_id for item in generated
        )
        actions.extend(generated)
    action_count = len(actions)
    actions = [
        replace(
            action, inject_order=index,
            cleanup_order=action_count - index - 1,
        )
        for index, action in enumerate(actions)
    ]
    affected_assets = tuple(dict.fromkeys(x for a in actions for x in a.targets))
    affected_asns = tuple(sorted({
        int(asset_by_container[x]["asn"])
        for x in affected_assets if x in asset_by_container and "asn" in asset_by_container[x]
    }))
    max_assets = min(int(s.safety.get("max_affected_assets", 1)) for s in specs)
    max_asns = min(int(s.safety.get("max_affected_asns", max_assets)) for s in specs)
    if len(affected_assets) > max_assets or len(affected_asns) > max_asns:
        raise ValueError(
            f"impact exceeds budget: assets={len(affected_assets)}/{max_assets}, "
            f"asns={len(affected_asns)}/{max_asns}"
        )
    lock_owner: Dict[str, str] = {}
    for action in actions:
        for lock in action.resource_locks:
            if lock in lock_owner:
                raise ValueError(
                    f"fault conflict on {lock}: {lock_owner[lock]} and {action.action_id}"
                )
            lock_owner[lock] = action.action_id
    impact = {
        "affected_asset_count": len(affected_assets),
        "affected_asn_count": len(affected_asns),
        "resource_locks": sorted(lock_owner),
        "must_break": [x for s in specs for x in s.expectations.get("must_break", [])],
        "must_preserve": [x for s in specs for x in s.expectations.get("must_preserve", [])],
    }
    topology_fingerprint = str(capabilities.get("topology_fingerprint", ""))
    unsigned = {
        "fault_ids": ids,
        "topology_fingerprint": topology_fingerprint,
        "actions": [item.to_dict() for item in actions],
        "affected_assets": list(affected_assets),
        "affected_asns": list(affected_asns),
        "relationship": relationship,
        "impact": impact,
    }
    return CompiledFaultPlan(
        fault_ids=tuple(ids), topology_fingerprint=topology_fingerprint,
        actions=tuple(actions), affected_assets=affected_assets,
        affected_asns=affected_asns, relationship=relationship,
        plan_fingerprint=canonical_sha256(unsigned), impact=impact,
    )
