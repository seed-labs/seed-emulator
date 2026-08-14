"""Compile independently produced AgentArtifacts into one benchmark bundle."""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
from typing import Any, Dict, Iterable, List, Mapping, Sequence

from generator.bundle.artifacts import AgentArtifact, ArtifactStore
from generator.bundle.models import BenchmarkBundleSpec, CompiledBenchmarkBundle
from generator.bundle.plugins import PluginRegistry, builtin_registry
from generator.bundle.security import review_bundle
from generator.bundle.specs import (
    BlindPolicy, LifecycleSpec, OracleSpec, ScoringSpec, ServiceSpec,
    TestSpec, WorkloadSpec,
)
from generator.contracts import inspect_contracts
from generator.faults.compiler import compile_fault_set
from generator.faults.models import FaultSpec


def _asset_capabilities(asset: Mapping[str, Any]) -> set[str]:
    result = set(str(item) for item in asset.get("capabilities", ()))
    for software in asset.get("software", ()):
        result.update(str(item) for item in software.get("capabilities", ()))
    return result


def resolve_assets(selector: Mapping[str, Any], capabilities: Mapping[str, Any]):
    assets = list(capabilities.get("assets") or [])
    if "container" in selector:
        assets = [x for x in assets if x.get("container") == selector["container"]]
    if "role" in selector:
        assets = [x for x in assets if str(selector["role"]) in str(x.get("role", ""))]
    if "asn" in selector:
        values = selector["asn"] if isinstance(selector["asn"], list) else [selector["asn"]]
        allowed = {int(x) for x in values}
        assets = [x for x in assets if int(x.get("asn", -1)) in allowed]
    if "software" in selector:
        assets = [
            x for x in assets if any(
                item.get("software_id") == selector["software"]
                for item in x.get("software", ())
            )
        ]
    if "capability" in selector:
        assets = [x for x in assets if selector["capability"] in _asset_capabilities(x)]
    assets.sort(key=lambda item: str(item.get("container", "")))
    choose = int(selector.get("choose", 1))
    if len(assets) < choose:
        raise ValueError(f"selector matched {len(assets)}/{choose} assets")
    return tuple(assets[:choose])


def _flatten(artifacts: Sequence[AgentArtifact], artifact_type: str, field: str):
    result = []
    for artifact in artifacts:
        if artifact.artifact_type == artifact_type:
            values = artifact.payload.get(field, ())
            if not isinstance(values, list):
                raise ValueError(f"artifact {artifact.artifact_id} field {field} must be a list")
            result.extend(values)
    return result


class BundleCompiler:
    """Contract-aware compiler with no AI or implicit code execution."""

    def __init__(
        self, benchmarks_dir: Path, artifact_store: ArtifactStore,
        *, registry: PluginRegistry | None = None,
    ):
        self.benchmarks_dir = benchmarks_dir.resolve()
        self.artifact_store = artifact_store
        if registry is None:
            from generator.faults.drivers import DRIVERS
            registry = builtin_registry(DRIVERS)
        self.registry = registry

    def _capabilities(self, topology_id: str) -> Dict[str, Any]:
        from generator.topology.bindings import load_capability_manifest
        return load_capability_manifest(topology_id)

    def compile(
        self, spec: BenchmarkBundleSpec,
        *, capabilities: Mapping[str, Any] | None = None,
    ) -> CompiledBenchmarkBundle:
        artifacts = tuple(self.artifact_store.load(x) for x in spec.artifact_ids)
        fingerprint_set = {x.artifact_fingerprint for x in artifacts}
        for artifact in artifacts:
            missing = set(artifact.input_fingerprints) - fingerprint_set
            if missing:
                raise ValueError(
                    f"artifact {artifact.artifact_id} has unresolved inputs={sorted(missing)}"
                )
        topology_artifacts = [x for x in artifacts if x.artifact_type == "topology_ref"]
        if len(topology_artifacts) != 1:
            raise ValueError("bundle requires exactly one topology_ref artifact")
        topology_id = str(topology_artifacts[0].payload.get("topology_id", ""))
        if not topology_id:
            raise ValueError("topology_ref has no topology_id")
        capability_manifest = dict(capabilities or self._capabilities(topology_id))
        if capability_manifest.get("topology_id") not in {None, topology_id}:
            raise ValueError("capability manifest targets another topology")
        topology_fingerprint = str(capability_manifest.get("topology_fingerprint", ""))
        if not topology_fingerprint:
            raise ValueError("capability manifest has no topology fingerprint")

        services = tuple(ServiceSpec.from_dict(x) for x in _flatten(artifacts, "service", "services"))
        workloads = tuple(WorkloadSpec.from_dict(x) for x in _flatten(artifacts, "workload", "workloads"))
        tests = tuple(TestSpec.from_dict(x) for x in _flatten(artifacts, "test", "tests"))
        oracles = tuple(OracleSpec.from_dict(x) for x in _flatten(artifacts, "oracle", "oracles"))
        scoring_values = _flatten(artifacts, "scoring", "scoring")
        lifecycle_values = _flatten(artifacts, "lifecycle", "lifecycles")
        policy_values = _flatten(artifacts, "blind_policy", "policies")
        if not services or not workloads or not tests or not oracles:
            raise ValueError("bundle requires services, workloads, tests and oracles")
        if len(scoring_values) != 1 or len(lifecycle_values) != 1 or len(policy_values) != 1:
            raise ValueError("bundle requires one scoring, lifecycle and blind policy")
        scoring = ScoringSpec.from_dict(scoring_values[0])
        lifecycle = LifecycleSpec.from_dict(lifecycle_values[0])
        blind_policy = BlindPolicy.from_dict(policy_values[0])

        service_ids = {x.service_id for x in services}
        if len(service_ids) != len(services):
            raise ValueError("duplicate service id")
        if any(set(item.dependencies) - service_ids for item in services):
            raise ValueError("service has an unknown dependency")
        if any(item.target_service not in service_ids for item in workloads):
            raise ValueError("workload has an unknown target service")
        test_ids = {x.test_id for x in tests}
        if len(test_ids) != len(tests):
            raise ValueError("duplicate test id")
        for oracle in oracles:
            if set(oracle.required_tests) - test_ids:
                raise ValueError("oracle refers to an unknown test")
            for ids in oracle.phase_requirements.values():
                if set(ids) - test_ids:
                    raise ValueError("oracle phase refers to an unknown test")
        if set(scoring.weights) - test_ids:
            raise ValueError("scoring refers to an unknown test")

        catalog = {
            str(item.get("software_id"))
            for item in capability_manifest.get("software_catalog", ())
        }
        for raw in _flatten(artifacts, "software", "required_software"):
            software_id = str(raw)
            if software_id not in catalog:
                raise ValueError(f"required software is absent: {software_id}")

        for service in services:
            self.registry.require(service.driver, kind="service")
            targets = resolve_assets(service.selector, capability_manifest)
            for target in targets:
                missing = set(service.capabilities_required) - _asset_capabilities(target)
                if missing:
                    raise ValueError(
                        f"service {service.service_id} target lacks capabilities={sorted(missing)}"
                    )
        for workload in workloads:
            descriptor = self.registry.require(workload.driver, kind="workload")
            resolve_assets(workload.source, capability_manifest)
            if workload.duration_seconds > 60 and not descriptor.supports_sampling:
                raise ValueError("long workload requires a sampling-capable driver")
        for test in tests:
            self.registry.require(test.driver, kind="probe")
            resolve_assets(test.selector, capability_manifest)

        plans = []
        must_break, must_preserve = set(), set()
        for artifact in artifacts:
            if artifact.artifact_type != "fault_set":
                continue
            raw_faults = artifact.payload.get("faults")
            if not isinstance(raw_faults, list) or not raw_faults:
                raise ValueError("fault_set artifact requires faults")
            faults = tuple(FaultSpec.from_dict(x) for x in raw_faults)
            relationship = str(artifact.payload.get("relationship", "independent"))
            plan = compile_fault_set(faults, capability_manifest, relationship=relationship)
            plans.append(plan)
            must_break.update(plan.impact.get("must_break", ()))
            must_preserve.update(plan.impact.get("must_preserve", ()))
        if not plans:
            raise ValueError("bundle requires at least one compiled fault plan")
        active_expectations = {x.expectation_id for x in tests if x.phase == "active"}
        if must_break - active_expectations or must_preserve - active_expectations:
            raise ValueError(
                "active tests do not cover fault expectations: "
                f"must_break={sorted(must_break - active_expectations)}, "
                f"must_preserve={sorted(must_preserve - active_expectations)}"
            )
        recovery_expectations = {x.expectation_id for x in tests if x.phase == "recovery"}
        if must_break - recovery_expectations:
            raise ValueError("recovery tests do not cover every must_break expectation")

        public_bundle = {
            "schema_version": 1,
            "benchmark_id": spec.benchmark_id,
            "generator_contract_sha256": inspect_contracts(
                self.benchmarks_dir
            ).sha256,
            "topology": {
                "topology_id": topology_id,
                "topology_fingerprint": topology_fingerprint,
            },
            "services": [
                {"service_id": x.service_id, "driver": x.driver, "ports": list(x.ports)}
                for x in services
            ],
            "workloads": [
                {"workload_id": x.workload_id, "driver": x.driver,
                 "target_service": x.target_service}
                for x in workloads
            ],
            "public_tests": [
                {"test_id": x.test_id, "phase": x.phase, "driver": x.driver}
                for x in tests if x.public
            ],
            "scenario_metadata_included": False,
        }
        private_bundle = {
            "schema_version": 1,
            "services": [x.to_dict() for x in services],
            "workloads": [x.to_dict() for x in workloads],
            "tests": [x.to_dict() for x in tests],
            "oracles": [x.to_dict() for x in oracles],
            "scoring": scoring.to_dict(),
            "lifecycle": lifecycle.to_dict(),
            "blind_policy": blind_policy.to_dict(),
            "fault_plans": [x.to_dict() for x in plans],
            "must_break": sorted(must_break),
            "must_preserve": sorted(must_preserve),
        }
        review = review_bundle(
            public_bundle=public_bundle, private_bundle=private_bundle,
            forbidden_public_fields=blind_policy.forbidden_public_fields,
            known_assets=(x["container"] for x in capability_manifest.get("assets", ())),
        )
        return CompiledBenchmarkBundle.build(
            benchmark_id=spec.benchmark_id, seed=spec.seed,
            topology_id=topology_id, topology_fingerprint=topology_fingerprint,
            generator_contract_sha256=public_bundle[
                "generator_contract_sha256"
            ],
            artifact_fingerprints=tuple(x.artifact_fingerprint for x in artifacts),
            public_bundle=public_bundle, private_bundle=private_bundle,
            safety_review=review,
        )

    @staticmethod
    def write(bundle: CompiledBenchmarkBundle, output: Path) -> Path:
        output = output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(
            prefix=f".{output.name}.", suffix=".tmp", dir=output.parent, text=True
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(bundle.to_dict(), handle, ensure_ascii=False, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, output)
        except Exception:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass
            raise
        return output
