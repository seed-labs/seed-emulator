"""One-command production pipeline from BenchmarkRequest to release evidence."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Dict, Mapping

from generator.bundle.artifacts import AgentArtifact, ArtifactStore
from generator.bundle.compiler import BundleCompiler
from generator.bundle.coordinator import BenchmarkCoordinator
from generator.bundle.lifecycle import BundleLifecycleExecutor, DockerLifecycleRunner
from generator.bundle.isolation import BundleRunIsolator
from generator.bundle.publishing import ReleaseRegistry, publish_bundle
from generator.bundle.qualification import qualify_bundle
from generator.bundle.quality import QualityIndex, assess_bundle
from generator.bundle.request import (
    BenchmarkRequest, build_agent_tasks, bundle_spec_for_request,
)
from generator.bundle.scale import validate_bundle_scales
from generator.bundle.scheduler import (
    BuildCache, DistributedScheduler, ProductionJob,
    continuous_validation_matrix,
)
from generator.bundle.workers import WorkerContext, builtin_worker_handlers
from generator.bundle.templates import ApplicationTemplateRegistry


def _atomic_json(path: Path, value: Mapping[str, Any]) -> Path:
    path = path.resolve(); path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True); handle.write("\n")
            handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        try: os.unlink(temporary)
        except FileNotFoundError: pass
        raise
    return path


class ProductionGenerator:
    def __init__(self, benchmarks_dir: Path):
        self.benchmarks_dir = benchmarks_dir.resolve()

    def _prepare_topology(self, request: BenchmarkRequest) -> Mapping[str, Any]:
        if request.prepare_topology:
            if not request.topology_spec:
                raise ValueError("prepare_topology requires topology_spec")
            path = (self.benchmarks_dir / request.topology_spec).resolve()
            if self.benchmarks_dir not in path.parents or not path.is_file():
                raise ValueError("topology_spec is outside benchmarks or missing")
            from generator.topology.compiler import compile_topology
            from generator.topology.models import TopologyRequest
            from generator.topology.registry import register_request
            topology_request = TopologyRequest.from_json_file(path)
            if topology_request.topology_id != request.topology_id:
                raise ValueError("BenchmarkRequest and topology_spec IDs differ")
            plan = register_request(topology_request)
            compile_topology(plan)
        from generator.topology.bindings import load_capability_manifest
        return load_capability_manifest(request.topology_id)

    def generate(
        self, request: BenchmarkRequest, workspace: Path,
        *, capabilities: Mapping[str, Any] | None = None,
        release_version: str = "1.0.0",
        templates: ApplicationTemplateRegistry | None = None,
    ) -> Dict[str, Any]:
        """Generate one Bundle, owning Docker state when execution is requested."""
        workspace = workspace.resolve(); workspace.mkdir(parents=True, exist_ok=True)
        base_capabilities = dict(capabilities or self._prepare_topology(request))
        if not request.execute_lifecycle:
            return self._generate_bound(
                request, workspace, capabilities=base_capabilities,
                release_version=release_version, templates=templates,
            )
        isolator = BundleRunIsolator(
            self.benchmarks_dir, request.topology_id, request.request_id, workspace
        )
        with isolator:
            runtime_capabilities = isolator.capabilities(base_capabilities)
            result = self._generate_bound(
                request, workspace, capabilities=runtime_capabilities,
                release_version=release_version, templates=templates,
                isolator=isolator,
            )
        isolation = json.loads(isolator.report_path.read_text(encoding="utf-8"))
        result["isolation_status"] = isolation["status"]
        result["isolation_session_id"] = isolation["session_id"]
        result["isolation_cleanup_verified"] = isolation["cleanup_verified"]
        result.pop("summary_fingerprint", None)
        result["summary_fingerprint"] = hashlib.sha256(
            json.dumps(result, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        _atomic_json(workspace / "summary.json", result)
        return result

    def _generate_bound(
        self, request: BenchmarkRequest, workspace: Path,
        *, capabilities: Mapping[str, Any] | None = None,
        release_version: str = "1.0.0",
        templates: ApplicationTemplateRegistry | None = None,
        isolator: BundleRunIsolator | None = None,
    ) -> Dict[str, Any]:
        workspace = workspace.resolve(); workspace.mkdir(parents=True, exist_ok=True)
        capabilities = dict(capabilities or self._prepare_topology(request))
        if capabilities.get("topology_id") != request.topology_id:
            raise ValueError("production pipeline capabilities target another topology")
        request_path = _atomic_json(workspace / "request.json", request.to_dict())
        store = ArtifactStore(workspace / "artifacts")
        tasks = build_agent_tasks(request)
        _atomic_json(workspace / "tasks.json", {"tasks": [x.to_dict() for x in tasks]})
        coordinator = BenchmarkCoordinator(workspace / "coordinator.json", store)
        coordinator.initialize(tasks)
        context = WorkerContext.build(request, capabilities, templates)
        state = coordinator.run(
            builtin_worker_handlers(context), worker_id="builtin_production_worker"
        )
        if state["result"] != "complete":
            raise RuntimeError("production Agent DAG did not complete")

        worker_artifacts = tuple(store.load(task.output_artifact_id) for task in tasks)
        lifecycle = AgentArtifact(
            artifact_type="lifecycle",
            artifact_id=f"{request.request_id}_lifecycle",
            producer="lifecycle_controller",
            payload={"lifecycles": [{
                "repeat_runs": request.qualification_runs,
                "baseline_timeout": 120, "fault_timeout": 120,
                "recovery_timeout": 300,
            }]},
            input_fingerprints=tuple(x.artifact_fingerprint for x in worker_artifacts),
        )
        store.write(lifecycle)
        spec = bundle_spec_for_request(request)
        _atomic_json(workspace / "bundle_spec.json", spec.to_dict())
        compiler = BundleCompiler(self.benchmarks_dir, store)
        bundle = compiler.compile(spec, capabilities=capabilities)
        compiler.write(bundle, workspace / "compiled_bundle.json")

        quality = assess_bundle(bundle, request)
        _atomic_json(workspace / "quality.json", quality)
        if not quality["passed"]:
            failed = sorted(key for key, passed in quality["checks"].items() if not passed)
            raise ValueError(f"benchmark quality gate failed: {failed}")
        QualityIndex(workspace.parent / "quality_index.json").register(quality)
        scale = validate_bundle_scales(
            bundle, (5, 20, 100, 1000, 10000),
            base_capabilities=capabilities,
        )
        _atomic_json(workspace / "scale_validation.json", scale)
        ci_matrix = continuous_validation_matrix()
        _atomic_json(workspace / "ci_matrix.json", ci_matrix)
        cache = BuildCache(workspace.parent / "cache")
        cache_key = cache.put("compiled_bundles", {
            "request": request.fingerprint,
            "topology": bundle.topology_fingerprint,
            "contract": bundle.generator_contract_sha256,
        }, {
            "bundle_fingerprint": bundle.bundle_fingerprint,
            "quality_fingerprint": quality["quality_fingerprint"],
        })

        qualification = None
        if request.execute_lifecycle:
            qualification_path = workspace / "qualification.json"
            if qualification_path.exists():
                qualification = json.loads(qualification_path.read_text(encoding="utf-8"))
                if qualification.get("bundle_fingerprint") != bundle.bundle_fingerprint:
                    raise ValueError("stale qualification exists in production workspace")
            else:
                executor = BundleLifecycleExecutor(
                    workspace / "journals", DockerLifecycleRunner()
                )
                receipts = []
                for index in range(1, request.qualification_runs + 1):
                    receipt = workspace / f"lifecycle_round_{index:02d}.json"
                    executor.run(bundle, capabilities, receipt, blind_mode=True)
                    receipts.append(receipt)
                qualify_bundle(bundle, receipts, qualification_path)
                qualification = json.loads(qualification_path.read_text(encoding="utf-8"))

        release = None
        if request.publish:
            if not qualification:
                raise ValueError("formal release requires qualification")
            if isolator is not None:
                # Publication is allowed only after session-scoped Docker state
                # has been removed and independently inventoried as empty.
                isolator.stop()
            release = publish_bundle(
                bundle, version=release_version,
                public_root=workspace.parent / "releases_public",
                private_root=workspace.parent / "releases_private",
                registry=ReleaseRegistry(workspace.parent / "release_registry.json"),
                quality_report=quality, qualification=qualification,
            )
        summary: Dict[str, Any] = {
            "schema_version": 1, "request_id": request.request_id,
            "request_fingerprint": request.fingerprint,
            "bundle_fingerprint": bundle.bundle_fingerprint,
            "generator_contract_sha256": bundle.generator_contract_sha256,
            "quality_fingerprint": quality["quality_fingerprint"],
            "quality_passed": quality["passed"], "scale_passed": scale["passed"],
            "coordinator_result": state["result"], "worker_count": len(tasks),
            "cache_key": cache_key,
            "qualification_status": (qualification or {}).get("status", "not_requested"),
            "release": release, "workspace": str(workspace),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        unsigned = dict(summary)
        summary["summary_fingerprint"] = hashlib.sha256(
            json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        _atomic_json(workspace / "summary.json", summary)
        return summary


class ProductionWorkerRuntime:
    """Execute one whitelisted scheduler job inside an approved workspace root."""

    def __init__(
        self, benchmarks_dir: Path, scheduler: DistributedScheduler,
        allowed_root: Path,
    ):
        self.generator = ProductionGenerator(benchmarks_dir)
        self.scheduler = scheduler
        self.allowed_root = allowed_root.resolve()
        self.allowed_root.mkdir(parents=True, exist_ok=True)

    def _path(self, value: object, *, must_exist=False) -> Path:
        path = Path(str(value)).resolve()
        if path != self.allowed_root and self.allowed_root not in path.parents:
            raise ValueError("scheduled job path is outside the worker root")
        if must_exist and not path.is_file():
            raise ValueError("scheduled job input file is missing")
        return path

    def run_once(
        self, *, worker_id: str, resource_class: str, max_scale: int,
    ) -> Dict[str, Any]:
        claim = self.scheduler.claim(
            worker_id=worker_id, resource_class=resource_class,
            max_scale=max_scale,
        )
        if claim is None:
            return {"status": "idle", "worker_id": worker_id}
        job = ProductionJob.from_dict(claim["job"])
        try:
            if job.job_kind != "benchmark.generate":
                raise ValueError("worker only accepts benchmark.generate jobs")
            allowed = {"request", "capabilities", "workspace", "release_version"}
            if set(job.payload) - allowed or not {"request", "workspace"} <= set(job.payload):
                raise ValueError("scheduled generation payload is invalid")
            request_path = self._path(job.payload["request"], must_exist=True)
            workspace = self._path(job.payload["workspace"])
            request = BenchmarkRequest.from_dict(
                json.loads(request_path.read_text(encoding="utf-8"))
            )
            if request.fingerprint != job.request_fingerprint or request.scale != job.scale:
                raise ValueError("scheduled job differs from its BenchmarkRequest")
            capabilities = None
            if job.payload.get("capabilities"):
                capability_path = self._path(job.payload["capabilities"], must_exist=True)
                capabilities = json.loads(capability_path.read_text(encoding="utf-8"))
            result = self.generator.generate(
                request, workspace, capabilities=capabilities,
                release_version=str(job.payload.get("release_version", "1.0.0")),
            )
            self.scheduler.complete(job.job_id, claim["lease_id"], result)
            return {"status": "complete", "job_id": job.job_id, "result": result}
        except Exception as exc:
            self.scheduler.fail(
                job.job_id, claim["lease_id"], str(exc),
                quarantine=isinstance(exc, ValueError),
            )
            raise
