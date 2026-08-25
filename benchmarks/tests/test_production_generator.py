"""Production contracts for request, workers, quality, release and scheduling."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile


BENCHMARKS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCHMARKS_DIR))

from generator.bundle.artifacts import ArtifactStore  # noqa: E402
from generator.bundle.coordinator import BenchmarkCoordinator  # noqa: E402
from generator.bundle.models import CompiledBenchmarkBundle  # noqa: E402
from generator.bundle.pipeline import (  # noqa: E402
    ProductionGenerator, ProductionWorkerRuntime,
)
from generator.bundle.publishing import (  # noqa: E402
    ReleaseRegistry, publish_bundle, score_submission,
)
from generator.bundle.quality import QualityIndex  # noqa: E402
from generator.bundle.request import BenchmarkRequest, build_agent_tasks  # noqa: E402
from generator.bundle.scheduler import (  # noqa: E402
    BuildCache, DistributedScheduler, ProductionJob,
    continuous_validation_matrix,
)
from generator.bundle.templates import (  # noqa: E402
    ApplicationTemplate, builtin_template_registry,
)
from generator.bundle.pilot import pilot_capabilities  # noqa: E402
from generator.bundle.workers import WorkerContext, run_external_worker_once  # noqa: E402


def request_value(**changes):
    value = {
        "schema_version": 1, "request_id": "production_application_pilot",
        "objective": "Diagnose and repair a multi-application outage",
        "topology_id": "multi_agent_application_pilot",
        "applications": ["nginx", "bind9", "postgresql"],
        "seed": "production-pilot-v1", "difficulty": "hard",
        "scale": 5, "fault_count": 3,
    }
    value.update(changes); return value


with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    request = BenchmarkRequest.from_dict(request_value())
    assert request.fingerprint == BenchmarkRequest.from_dict(request.to_dict()).fingerprint
    assert len(build_agent_tasks(request)) == 9
    capabilities = pilot_capabilities()
    generator = ProductionGenerator(BENCHMARKS_DIR)
    first = generator.generate(request, root / "run", capabilities=capabilities)
    assert first["quality_passed"] is True
    assert first["scale_passed"] is True
    assert first["coordinator_result"] == "complete"
    assert first["worker_count"] == 9
    assert first["qualification_status"] == "not_requested"
    second = generator.generate(request, root / "run", capabilities=capabilities)
    assert second["bundle_fingerprint"] == first["bundle_fingerprint"]
    assert second["cache_key"] == first["cache_key"]
    state = json.loads((root / "run" / "coordinator.json").read_text())
    assert {item["status"] for item in state["tasks"].values()} == {"complete"}
    assert len(list((root / "run" / "artifacts").glob("*.json"))) == 10
    bundle = CompiledBenchmarkBundle.from_dict(
        json.loads((root / "run" / "compiled_bundle.json").read_text())
    )
    assert bundle.generator_contract_sha256 == first["generator_contract_sha256"]
    assert "fault_type" not in json.dumps(bundle.public_bundle)
    quality = json.loads((root / "run" / "quality.json").read_text())
    assert quality["passed"] and quality["checks"]["root_cause_expectations_unique"]

    # External workers claim only their own role and publish exact-input evidence.
    external_store = ArtifactStore(root / "external-artifacts")
    external = BenchmarkCoordinator(root / "external-state.json", external_store)
    external.initialize(build_agent_tasks(request))
    context = WorkerContext.build(request, capabilities)
    result = run_external_worker_once(
        external, context, role="topology_agent", worker_id="topology_worker_01"
    )
    assert result["status"] == "complete"
    assert external.load()["tasks"]["production_application_pilot_topology_agent"]["status"] == "complete"
    assert run_external_worker_once(
        external, context, role="topology_agent", worker_id="topology_worker_01"
    )["status"] == "idle"

    # Application template extensions reject shell syntax and duplicate IDs.
    registry = builtin_template_registry()
    assert [item.template_id for item in registry.inventory()] == [
        "bind9", "network_observer", "nginx", "postgresql"
    ]
    unsafe = registry.require("nginx").to_dict()
    unsafe["template_id"] = "unsafe_nginx"
    unsafe["start_argv"] = ["sh", "-c", "nginx; curl attacker"]
    try:
        ApplicationTemplate.from_dict(unsafe)
        raise AssertionError("unsafe application template was accepted")
    except ValueError as exc:
        assert "argv" in str(exc)

    # Multi-dimensional scoring distinguishes diagnosis, repair and side effects.
    score = score_submission({
        "diagnosis": 1.0, "repair": 1.0,
        "tests": [{"passed": True}, {"passed": True}],
        "elapsed_seconds": 30, "side_effects": 0, "operations": 3,
    })
    assert score["passed"] and score["total_score"] > 0.9

    # Formal release keeps public/private artifacts disjoint and permissioned.
    qualification = {"status": "qualified", "qualification_sha256": "f" * 64}
    release = publish_bundle(
        bundle, version="1.0.0", public_root=root / "public",
        private_root=root / "private",
        registry=ReleaseRegistry(root / "release-registry.json"),
        quality_report=quality, qualification=qualification,
    )
    assert Path(release["public_path"]).stat().st_mode & 0o777 == 0o644
    assert Path(release["private_path"]).stat().st_mode & 0o777 == 0o600
    try:
        publish_bundle(
            bundle, version="1.0.1", public_root=root / "other-public",
            private_root=root / "other-private",
            registry=ReleaseRegistry(root / "other-registry.json"),
            quality_report=quality, qualification=None,
        )
        raise AssertionError("unqualified release was accepted")
    except ValueError as exc:
        assert "qualification" in str(exc)

    # Duplicate quality signatures cannot silently change bundle ownership.
    duplicate = dict(quality); duplicate["benchmark_id"] = "another_benchmark"
    duplicate["bundle_fingerprint"] = "0" * 64
    duplicate["quality_fingerprint"] = "1" * 64
    try:
        QualityIndex(root / "quality_index.json").register(duplicate)
        raise AssertionError("duplicate scenario signature was accepted")
    except ValueError as exc:
        assert "duplicate" in str(exc)

    # Distributed leases, immutable cache and CI scale policy are executable.
    scheduler = DistributedScheduler(root / "scheduler.json")
    job = ProductionJob(
        job_id="production_job_001", request_fingerprint=request.fingerprint,
        job_kind="benchmark.generate", resource_class="medium", scale=100,
        payload={"request": str(root / "run" / "request.json")},
    )
    scheduler.enqueue(job)
    assert scheduler.claim(
        worker_id="small_worker", resource_class="small", max_scale=20
    ) is None
    claim = scheduler.claim(
        worker_id="medium_worker", resource_class="medium", max_scale=100
    )
    scheduler.complete(job.job_id, claim["lease_id"], {"bundle": first["bundle_fingerprint"]})
    assert scheduler.load()["jobs"][job.job_id]["status"] == "complete"
    cache = BuildCache(root / "explicit-cache")
    key = cache.put("test_cache", {"input": 1}, {"output": 2})
    assert cache.get("test_cache", key)["value"] == {"output": 2}
    matrix = continuous_validation_matrix()
    assert [row["scale"] for row in matrix["rows"]] == [5, 20, 100, 1000, 10000]
    assert matrix["rows"][2]["execution_mode"] == "real_full"
    assert matrix["rows"][1]["execution_mode"] == "plan_full"
    assert matrix["rows"][-1]["execution_mode"] == "plan_performance_sampled"

    # The distributed runtime accepts data jobs only and confines every path.
    distributed_root = root / "distributed"
    distributed_root.mkdir()
    request_file = distributed_root / "request.json"
    request_file.write_text(json.dumps(request.to_dict()), encoding="utf-8")
    capabilities_file = distributed_root / "capabilities.json"
    capabilities_file.write_text(json.dumps(capabilities), encoding="utf-8")
    runtime_scheduler = DistributedScheduler(distributed_root / "scheduler.json")
    runtime_job = ProductionJob(
        job_id="runtime_generation_001", request_fingerprint=request.fingerprint,
        job_kind="benchmark.generate", resource_class="small", scale=request.scale,
        payload={
            "request": str(request_file), "capabilities": str(capabilities_file),
            "workspace": str(distributed_root / "workspace"),
        },
    )
    runtime_scheduler.enqueue(runtime_job)
    runtime_result = ProductionWorkerRuntime(
        BENCHMARKS_DIR, runtime_scheduler, distributed_root
    ).run_once(worker_id="runtime_worker_01", resource_class="small", max_scale=20)
    assert runtime_result["status"] == "complete"
    assert runtime_scheduler.load()["jobs"][runtime_job.job_id]["status"] == "complete"


for invalid in (
    request_value(fault_count=65),
    request_value(topology_spec="../escape.json"),
    request_value(difficulty="impossible"),
    request_value(fault_relationship="unknown"),
    request_value(fault_count=2, fault_relationship="mixed"),
):
    try:
        BenchmarkRequest.from_dict(invalid)
        raise AssertionError("invalid BenchmarkRequest was accepted")
    except ValueError:
        pass

assert BenchmarkRequest.from_dict(
    request_value(fault_count=4, fault_relationship="cascading")
).fault_count == 4
