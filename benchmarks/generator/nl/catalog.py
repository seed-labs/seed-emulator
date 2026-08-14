"""Versioned snapshot of applications, faults, topologies and resource policy."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Tuple

from generator.bundle.plugins import builtin_registry
from generator.bundle.templates import builtin_template_registry
from generator.faults.drivers import DRIVERS
from generator.topology.models import TopologyRequest
from generator.topology.registry import list_plans, output_dir


def _sha(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


class CapabilityCatalog:
    def __init__(self, snapshot: Mapping[str, Any]):
        self.snapshot = dict(snapshot)
        self.fingerprint = _sha(self.snapshot)

    @property
    def application_ids(self) -> Tuple[str, ...]:
        return tuple(item["template_id"] for item in self.snapshot["applications"])

    @property
    def fault_ids(self) -> Tuple[str, ...]:
        return tuple(item["plugin_id"] for item in self.snapshot["faults"])

    @property
    def topology_ids(self) -> Tuple[str, ...]:
        return tuple(item["topology_id"] for item in self.snapshot["topologies"])

    def topology(self, topology_id: str) -> Dict[str, Any]:
        for item in self.snapshot["topologies"]:
            if item["topology_id"] == topology_id:
                return dict(item)
        raise ValueError(f"unknown topology capability={topology_id}")

    def select_topology(
        self, applications: Iterable[str], *, observer_required: bool, scale: int,
    ) -> Dict[str, Any] | None:
        required = set(applications)
        if observer_required:
            required.add("network_observer")
        candidates = [
            item for item in self.snapshot["topologies"]
            if item["compiled"]
            and required <= set(item["application_templates"])
            and item["resource_estimate"]["containers"] >= scale
        ]
        if not candidates:
            return None
        return dict(sorted(candidates, key=lambda item: (
            item["resource_estimate"]["containers"], item["topology_id"]
        ))[0])

    def to_dict(self) -> Dict[str, Any]:
        return {**self.snapshot, "catalog_fingerprint": self.fingerprint}


def build_capability_catalog(benchmarks_dir: Path) -> CapabilityCatalog:
    templates = builtin_template_registry().inventory()
    applications = [item.to_dict() for item in templates]
    capability_to_template = {item.capability: item.template_id for item in templates}
    faults = [
        item.to_dict() for item in builtin_registry(DRIVERS).inventory()
        if item.kind == "fault"
    ]
    topologies = []
    for plan in list_plans(benchmarks_dir):
        request = TopologyRequest.from_dict(plan.request)
        capabilities = {
            capability
            for software in request.software
            for capability in software.capabilities
        }
        app_ids = sorted(
            capability_to_template[item] for item in capabilities
            if item in capability_to_template
        )
        topologies.append({
            "topology_id": plan.topology_id,
            "topology_name": plan.topology_name,
            "topology_fingerprint": plan.fingerprint,
            "edge_policy": plan.edge_policy,
            "application_templates": app_ids,
            "resource_estimate": plan.resource_estimate.__dict__,
            "request": request.to_dict(),
            "compiled": (output_dir(plan.topology_id, benchmarks_dir) / "topology_manifest.json").is_file(),
        })
    snapshot = {
        "schema_version": 1,
        "applications": sorted(applications, key=lambda item: item["template_id"]),
        "faults": sorted(faults, key=lambda item: item["plugin_id"]),
        "topologies": sorted(topologies, key=lambda item: item["topology_id"]),
        "resource_policy": {
            "max_scale": 10000,
            "qualification_runs": {"minimum": 2, "maximum": 10},
            "resource_classes": ["small", "medium", "large", "xlarge"],
            "real_execution_requires_approval": True,
            "publication_requires_qualification": True,
        },
    }
    return CapabilityCatalog(snapshot)
