"""Deterministic safety and compilation bridge into topology capabilities."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import ipaddress
import json
from typing import Any, Dict, Mapping, Tuple

from generator.bundle.request import BenchmarkRequest
from generator.bundle.templates import builtin_template_registry
from generator.nl.catalog import CapabilityCatalog
from generator.nl.scene_models import BenchmarkSceneIntent, SceneApplicationPlacement
from generator.software import SoftwareSpec
from generator.topology.models import ResourceBudget, TopologyPlan, TopologyRequest
from generator.topology.planner import plan_topology


SCENE_FAULT_BINDINGS = {
    "container.stopped": "container_stopped",
    "dns.nameserver": "dns_nameserver",
    "network.acl.scoped": "scoped_acl",
    "network.netem": "netem",
    "routing.bird.wrong_asn": "bird_wrong_asn",
}
PRIVATE_ASN_RANGES = ((64512, 65534), (4200000000, 4294967294))
POOL_ENVELOPES = {
    "lan_pool": ipaddress.ip_network("10.0.0.0/8"),
    "ix_pool": ipaddress.ip_network("172.16.0.0/12"),
    "loopback_pool": ipaddress.ip_network("100.64.0.0/10"),
}


def _sha(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _resource_class(scale: int) -> str:
    if scale <= 20:
        return "small"
    if scale <= 100:
        return "medium"
    if scale <= 1000:
        return "large"
    return "xlarge"


@dataclass(frozen=True)
class SceneRequirementResult:
    status: str
    questions: Tuple[Dict[str, str], ...]
    extension_proposals: Tuple[Dict[str, Any], ...]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "questions": list(self.questions),
            "extension_proposals": list(self.extension_proposals),
        }


def analyze_scene_requirements(
    intent: BenchmarkSceneIntent, catalog: CapabilityCatalog,
) -> SceneRequirementResult:
    questions = []
    extensions = []
    if not intent.application_placements:
        questions.append({
            "code": "missing_applications", "field": "application_placements",
            "question": "请指定至少一个已知应用，例如 nginx、bind9 或 postgresql。",
        })
    if not intent.fault_types or intent.fault_count < 1:
        questions.append({
            "code": "missing_faults", "field": "fault_types",
            "question": "请指定至少一种可验证故障。",
        })
    application_ids = {item.template_id for item in intent.application_placements}
    placement_ids = [item.template_id for item in intent.application_placements]
    duplicate_placements = sorted({
        item for item in placement_ids if placement_ids.count(item) > 1
    })
    if duplicate_placements:
        questions.append({
            "code": "duplicate_application_placement",
            "field": "application_placements",
            "question": (
                "同一应用模板出现多个 placement；请明确单一选择器或扩展多实例放置模型："
                + ", ".join(duplicate_placements)
            ),
        })
    unknown_apps = sorted(application_ids - set(catalog.application_ids))
    unknown_faults = sorted(set(intent.fault_types) - set(catalog.fault_ids))
    unsupported_scene_faults = sorted(
        set(intent.fault_types) - set(SCENE_FAULT_BINDINGS)
    )
    for requirement in sorted(
        set(intent.unknown_requirements) | set(unknown_apps) | set(unknown_faults)
        | set(unsupported_scene_faults)
    ):
        extensions.append({
            "requirement": requirement,
            "status": "human_review_required",
            "needed_components": [
                "audited application template or FaultDriver binding",
                "deterministic workload and probe",
                "topology capability-manifest mapping",
                "no-AI lifecycle evidence",
            ],
        })
    effective_apps = len(application_ids | ({"network_observer"} if intent.observer_required else set()))
    if intent.fault_count > effective_apps and effective_apps:
        questions.append({
            "code": "fault_count_exceeds_applications", "field": "fault_count",
            "question": "故障数量不能超过应用及观测角色数量，请调整组合。",
        })
    status = "extension_required" if extensions else (
        "needs_clarification" if questions else "ready"
    )
    return SceneRequirementResult(status, tuple(questions), tuple(extensions))


@dataclass(frozen=True)
class CompiledSceneBridge:
    intent: BenchmarkSceneIntent
    topology_request: TopologyRequest
    topology_plan: TopologyPlan
    benchmark_request: BenchmarkRequest
    application_capabilities: Dict[str, str]
    fault_bindings: Dict[str, str]
    safety_report: Dict[str, Any]
    preview: Dict[str, Any]
    bridge_fingerprint: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent": self.intent.to_dict(),
            "topology_request": self.topology_request.to_dict(),
            "topology_plan": self.topology_plan.to_dict(),
            "benchmark_request": self.benchmark_request.to_dict(),
            "application_capabilities": self.application_capabilities,
            "fault_bindings": self.fault_bindings,
            "safety_report": self.safety_report,
            "preview": self.preview,
            "bridge_fingerprint": self.bridge_fingerprint,
        }


def _private_topology_policy(intent: BenchmarkSceneIntent) -> Dict[str, Any]:
    topology = intent.topology
    checks = []
    for field, envelope in POOL_ENVELOPES.items():
        try:
            network = ipaddress.ip_network(str(topology[field]), strict=True)
        except ValueError as exc:
            raise ValueError(f"scene {field} is not a strict network") from exc
        if network.version != 4 or not network.subnet_of(envelope):
            raise ValueError(f"scene {field} escapes its approved address envelope")
        checks.append({"check": field, "network": str(network), "envelope": str(envelope)})
    asn_start = int(topology["asn_start"])
    asn_end = asn_start + int(topology["as_count"]) - 1
    if not any(lower <= asn_start <= asn_end <= upper for lower, upper in PRIVATE_ASN_RANGES):
        raise ValueError("scene ASN allocation escapes private-use ranges")
    checks.append({"check": "private_asn_range", "start": asn_start, "end": asn_end})
    return {
        "schema_version": 1,
        "allowed": True,
        "execution_authorized": False,
        "host_operations_present": False,
        "shell_present": False,
        "docker_operations_present": False,
        "address_and_asn_checks": checks,
        "policy": {
            "topology_model": "TopologyRequest v1 only",
            "software_source": "audited ApplicationTemplate catalog only",
            "fault_source": "audited FaultDriver bindings only",
            "host_path_access": "not representable",
            "arbitrary_commands": "not representable",
        },
    }


def _software_for_placement(
    placement: SceneApplicationPlacement,
) -> tuple[SoftwareSpec, str]:
    template = builtin_template_registry().require(placement.template_id)
    return SoftwareSpec(
        software_id=template.software_id,
        packages=template.packages,
        target_roles=placement.target_roles,
        target_asns=placement.target_asns,
        target_nodes=placement.target_nodes,
        capabilities=(template.capability,),
    ), template.capability


def _placement_assets(
    placement: SceneApplicationPlacement,
    *,
    asn_start: int,
    as_count: int,
    hosts_per_as: int,
) -> set[tuple[int, str, str]]:
    """Resolve one declarative placement without consulting container names."""
    assets = {
        (asn, role, node)
        for asn in range(asn_start, asn_start + as_count)
        for role, node in (
            [("router", "router0")]
            + [("host", f"host{index}") for index in range(hosts_per_as)]
        )
    }
    return {
        (asn, role, node)
        for asn, role, node in assets
        if role in placement.target_roles
        and (not placement.target_asns or asn in placement.target_asns)
        and (not placement.target_nodes or node in placement.target_nodes)
    }


def _resolve_application_placements(
    intent: BenchmarkSceneIntent,
) -> tuple[Tuple[SceneApplicationPlacement, ...], Dict[str, Any]]:
    """Turn empty selectors into exact deterministic, observer-safe placements.

    In the natural-language scene contract an empty ASN and node selector means
    "compiler chooses one asset", not "install everywhere".  This keeps the
    generated service target separate from the protected blind-test observer.
    Explicit broad selectors remain broad and are rejected if they overlap the
    observer.
    """
    topology = intent.topology
    asn_start = int(topology["asn_start"])
    as_count = int(topology["as_count"])
    hosts_per_as = int(topology["hosts_per_as"])
    placements = list(intent.application_placements)
    observers = [item for item in placements if item.template_id == "network_observer"]
    applications = [item for item in placements if item.template_id != "network_observer"]
    if not observers:
        observers = [SceneApplicationPlacement("network_observer", ("host",), (), ())]
    observer = observers[0]
    if observer.target_roles != ("host",):
        raise ValueError("network observer placement must target host assets only")

    explicit_application_assets = set()
    for placement in applications:
        if placement.target_asns or placement.target_nodes:
            explicit_application_assets |= _placement_assets(
                placement, asn_start=asn_start, as_count=as_count,
                hosts_per_as=hosts_per_as,
            )

    if not observer.target_asns and not observer.target_nodes:
        observer_candidates = [
            (asn, "host", f"host{index}")
            for asn in reversed(range(asn_start, asn_start + as_count))
            for index in reversed(range(hosts_per_as))
        ]
        selected = next(
            (asset for asset in observer_candidates if asset not in explicit_application_assets),
            None,
        )
        if selected is None:
            raise ValueError("no isolated host remains for the protected network observer")
        observer = SceneApplicationPlacement(
            "network_observer", ("host",), (selected[0],), (selected[2],),
        )

    observer_assets = _placement_assets(
        observer, asn_start=asn_start, as_count=as_count,
        hosts_per_as=hosts_per_as,
    )
    if not observer_assets:
        raise ValueError("network observer selector matches no topology asset")

    resolved_applications = []
    compiler_selected = []
    occupied = set(observer_assets)
    for placement in applications:
        resolved = placement
        if not placement.target_asns and not placement.target_nodes:
            candidates = [
                (asn, role, node)
                for role in ("host", "router")
                if role in placement.target_roles
                for asn in range(asn_start, asn_start + as_count)
                for node in (
                    [f"host{index}" for index in range(hosts_per_as)]
                    if role == "host" else ["router0"]
                )
            ]
            selected = next((asset for asset in candidates if asset not in occupied), None)
            if selected is None:
                raise ValueError(
                    f"no isolated topology asset remains for application={placement.template_id}"
                )
            resolved = SceneApplicationPlacement(
                placement.template_id, (selected[1],), (selected[0],), (selected[2],),
            )
            compiler_selected.append(placement.template_id)
        selected_assets = _placement_assets(
            resolved, asn_start=asn_start, as_count=as_count,
            hosts_per_as=hosts_per_as,
        )
        if not selected_assets:
            raise ValueError(
                f"application placement matches no topology asset: {placement.template_id}"
            )
        if selected_assets & observer_assets:
            raise ValueError(
                f"application placement overlaps protected observer: {placement.template_id}"
            )
        occupied |= selected_assets
        resolved_applications.append(resolved)

    resolved = tuple(resolved_applications + [observer])
    report = {
        "check": "application_observer_isolation",
        "allowed": True,
        "empty_selector_semantics": "deterministic_single_asset",
        "compiler_selected_applications": compiler_selected,
        "observer_assets": [
            {"asn": asn, "role": role, "node": node}
            for asn, role, node in sorted(observer_assets)
        ],
        "resolved_placements": [
            {
                "template_id": item.template_id,
                "target_roles": list(item.target_roles),
                "target_asns": list(item.target_asns),
                "target_nodes": list(item.target_nodes),
            }
            for item in resolved
        ],
    }
    return resolved, report


def compile_scene_intent(
    intent: BenchmarkSceneIntent, catalog: CapabilityCatalog,
) -> CompiledSceneBridge:
    requirements = analyze_scene_requirements(intent, catalog)
    if requirements.status != "ready":
        raise ValueError(f"scene requirements are not ready: {requirements.status}")
    safety = _private_topology_policy(intent)
    placements, placement_report = _resolve_application_placements(intent)
    safety["application_placement_check"] = placement_report
    software = []
    capabilities = {}
    for placement in placements:
        spec, capability = _software_for_placement(placement)
        software.append(spec)
        capabilities[placement.template_id] = capability
    topology_value = dict(intent.topology)
    budget = ResourceBudget.from_dict(topology_value.pop("budget"))
    topology_request = TopologyRequest(
        topology_id=intent.topology_id,
        master_seed=intent.seed,
        budget=budget,
        software=tuple(software),
        explicit_edges=tuple(
            tuple(int(endpoint) for endpoint in edge)
            for edge in topology_value.pop("explicit_edges")
        ),
        **topology_value,
    )
    topology_plan = plan_topology(topology_request)
    if any(
        fault in {"network.acl.scoped", "routing.bird.wrong_asn"}
        for fault in intent.fault_types
    ) and not topology_plan.external_links:
        raise ValueError("selected routing/ACL fault requires at least one external AS link")
    applications = tuple(
        item.template_id for item in placements
        if item.template_id != "network_observer"
    )
    scale = topology_plan.resource_estimate.containers - 2
    benchmark_request = BenchmarkRequest.from_dict({
        "schema_version": 1,
        "request_id": intent.request_id,
        "objective": intent.objective,
        "topology_id": intent.topology_id,
        "applications": list(applications),
        "seed": intent.seed,
        "difficulty": intent.difficulty,
        "scale": scale,
        "fault_count": intent.fault_count,
        "fault_types": list(intent.fault_types),
        "observer_template": "network_observer",
        "topology_spec": f"topology_specs/{intent.topology_id}/request.json",
        "prepare_topology": False,
        "execute_lifecycle": False,
        "qualification_runs": 2,
        "publish": False,
        "resource_class": _resource_class(scale),
    })
    fault_bindings = {
        fault: SCENE_FAULT_BINDINGS[fault] for fault in intent.fault_types
    }
    preview = {
        "schema_version": 1,
        "mode": "plan_only_no_docker_state_change",
        "arbitrary_scene_bridge": True,
        "execution_authorized": False,
        "publication_authorized": False,
        "topology_id": intent.topology_id,
        "topology_fingerprint": topology_plan.fingerprint,
        "edge_policy": topology_plan.edge_policy,
        "explicit_allocated_edges": [
            [item.left_asn, item.right_asn] for item in topology_plan.external_links
        ],
        "resource_estimate": topology_plan.resource_estimate.__dict__,
        "application_capabilities": capabilities,
        "fault_bindings": fault_bindings,
        "handoff_target": "Topology capability manifest",
        "next_stage": "register and compile only after one-time approval",
        "safety": safety,
    }
    bridge_fingerprint = _sha({
        "intent": intent.fingerprint,
        "catalog": catalog.fingerprint,
        "topology": topology_plan.fingerprint,
        "benchmark": benchmark_request.fingerprint,
        "capabilities": capabilities,
        "fault_bindings": fault_bindings,
        "safety": safety,
    })
    preview["bridge_fingerprint"] = bridge_fingerprint
    return CompiledSceneBridge(
        intent, topology_request, topology_plan, benchmark_request,
        capabilities, fault_bindings, safety, preview, bridge_fingerprint,
    )


def validate_scene_manifest(
    bridge: CompiledSceneBridge, manifest: Mapping[str, Any],
) -> Dict[str, Any]:
    if manifest.get("topology_id") != bridge.topology_request.topology_id:
        raise ValueError("capability manifest targets another topology")
    if manifest.get("topology_fingerprint") != bridge.topology_plan.fingerprint:
        raise ValueError("capability manifest fingerprint differs from the bridge plan")
    software_catalog = list(manifest.get("software_catalog") or [])
    declared_capabilities = {
        capability
        for item in software_catalog
        for capability in item.get("capabilities", [])
    }
    missing_capabilities = set(bridge.application_capabilities.values()) - declared_capabilities
    if missing_capabilities:
        raise ValueError(
            f"capability manifest lacks declared applications: {sorted(missing_capabilities)}"
        )
    bindings = manifest.get("fault_component_bindings") or {}
    missing_bindings = [
        fault for fault, binding in bridge.fault_bindings.items()
        if not bindings.get(binding)
    ]
    if missing_bindings:
        raise ValueError(
            f"capability manifest lacks fault targets: {sorted(missing_bindings)}"
        )
    result = {
        "schema_version": 1,
        "accepted": True,
        "topology_id": bridge.topology_request.topology_id,
        "topology_fingerprint": bridge.topology_plan.fingerprint,
        "bridge_fingerprint": bridge.bridge_fingerprint,
        "asset_count": len(manifest.get("assets") or []),
        "application_capabilities": bridge.application_capabilities,
        "fault_bindings": bridge.fault_bindings,
        "manifest_sha256": _sha(dict(manifest)),
    }
    result["handoff_fingerprint"] = _sha(result)
    return result
