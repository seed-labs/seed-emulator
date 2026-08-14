#!/usr/bin/env python3
"""Command-line interface for multi-agent BenchmarkBundles."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from generator.bundle.artifacts import AgentArtifact, ArtifactStore
from generator.bundle.compiler import BundleCompiler
from generator.bundle.coordinator import AgentTask, BenchmarkCoordinator
from generator.bundle.models import BenchmarkBundleSpec, CompiledBenchmarkBundle
from generator.bundle.plugins import builtin_registry
from generator.bundle.qualification import qualify_bundle
from generator.bundle.scale import validate_bundle_scales
from generator.bundle.lifecycle import BundleLifecycleExecutor, DockerLifecycleRunner
from generator.bundle.pipeline import ProductionGenerator, ProductionWorkerRuntime
from generator.bundle.publishing import score_submission
from generator.bundle.request import BenchmarkRequest
from generator.bundle.scheduler import (
    DistributedScheduler, ProductionJob, continuous_validation_matrix,
)
from generator.bundle.templates import builtin_template_registry
from generator.bundle.workers import WorkerContext, run_external_worker_once


BENCHMARKS_DIR = Path(__file__).resolve().parents[2]


def _read(path):
    return json.loads(Path(path).resolve().read_text(encoding="utf-8"))


def _write(path, value):
    destination = Path(path).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(destination)
    return destination


def build_parser():
    parser = argparse.ArgumentParser(description="Multi-agent BenchmarkBundle v1")
    commands = parser.add_subparsers(dest="command", required=True)
    artifact = commands.add_parser("artifact-put")
    artifact.add_argument("--artifact", required=True)
    artifact.add_argument("--store", required=True)
    compile_p = commands.add_parser("compile")
    compile_p.add_argument("--spec", required=True)
    compile_p.add_argument("--store", required=True)
    compile_p.add_argument("--capabilities")
    compile_p.add_argument("--output", required=True)
    for name in ("review", "validate"):
        command = commands.add_parser(name)
        command.add_argument("--bundle", required=True)
    split = commands.add_parser("split")
    split.add_argument("--bundle", required=True)
    split.add_argument("--public-output", required=True)
    split.add_argument("--private-output", required=True)
    run = commands.add_parser("run")
    run.add_argument("--bundle", required=True)
    run.add_argument("--capabilities", required=True)
    run.add_argument("--journal-dir", required=True)
    run.add_argument("--output", required=True)
    coordinate = commands.add_parser("coordinate-init")
    coordinate.add_argument("--tasks", required=True)
    coordinate.add_argument("--store", required=True)
    coordinate.add_argument("--state", required=True)
    status = commands.add_parser("coordinate-status")
    status.add_argument("--store", required=True)
    status.add_argument("--state", required=True)
    claim = commands.add_parser("coordinate-claim")
    claim.add_argument("--store", required=True)
    claim.add_argument("--state", required=True)
    claim.add_argument("--worker-id", required=True)
    claim.add_argument("--agent-role")
    complete = commands.add_parser("coordinate-complete")
    complete.add_argument("--store", required=True)
    complete.add_argument("--state", required=True)
    complete.add_argument("--task-id", required=True)
    complete.add_argument("--lease-id", required=True)
    complete.add_argument("--artifact", required=True)
    fail = commands.add_parser("coordinate-fail")
    fail.add_argument("--store", required=True)
    fail.add_argument("--state", required=True)
    fail.add_argument("--task-id", required=True)
    fail.add_argument("--lease-id", required=True)
    fail.add_argument("--error", required=True)
    qualify = commands.add_parser("qualify")
    qualify.add_argument("--bundle", required=True)
    qualify.add_argument("--receipt", action="append", required=True)
    qualify.add_argument("--output", required=True)
    scale = commands.add_parser("scale-validate")
    scale.add_argument("--bundle", required=True)
    scale.add_argument("--size", action="append", type=int)
    scale.add_argument("--capabilities")
    scale.add_argument("--output", required=True)
    generate = commands.add_parser("generate")
    generate.add_argument("--request", required=True)
    generate.add_argument("--workspace", required=True)
    generate.add_argument("--capabilities")
    generate.add_argument("--release-version", default="1.0.0")
    generate.add_argument("--template-file", action="append")
    worker = commands.add_parser("worker-run")
    worker.add_argument("--request", required=True)
    worker.add_argument("--capabilities", required=True)
    worker.add_argument("--store", required=True)
    worker.add_argument("--state", required=True)
    worker.add_argument("--role", required=True)
    worker.add_argument("--worker-id", required=True)
    worker.add_argument("--template-file", action="append")
    score = commands.add_parser("score")
    score.add_argument("--evidence", required=True)
    score.add_argument("--output", required=True)
    enqueue = commands.add_parser("schedule-enqueue")
    enqueue.add_argument("--scheduler", required=True)
    enqueue.add_argument("--job", required=True)
    schedule_status = commands.add_parser("schedule-status")
    schedule_status.add_argument("--scheduler", required=True)
    schedule_claim = commands.add_parser("schedule-claim")
    schedule_claim.add_argument("--scheduler", required=True)
    schedule_claim.add_argument("--worker-id", required=True)
    schedule_claim.add_argument("--resource-class", required=True)
    schedule_claim.add_argument("--max-scale", type=int, required=True)
    schedule_complete = commands.add_parser("schedule-complete")
    schedule_complete.add_argument("--scheduler", required=True)
    schedule_complete.add_argument("--job-id", required=True)
    schedule_complete.add_argument("--lease-id", required=True)
    schedule_complete.add_argument("--result", required=True)
    schedule_fail = commands.add_parser("schedule-fail")
    schedule_fail.add_argument("--scheduler", required=True)
    schedule_fail.add_argument("--job-id", required=True)
    schedule_fail.add_argument("--lease-id", required=True)
    schedule_fail.add_argument("--error", required=True)
    schedule_fail.add_argument("--quarantine", action="store_true")
    schedule_run = commands.add_parser("schedule-run")
    schedule_run.add_argument("--scheduler", required=True)
    schedule_run.add_argument("--allowed-root", required=True)
    schedule_run.add_argument("--worker-id", required=True)
    schedule_run.add_argument("--resource-class", required=True)
    schedule_run.add_argument("--max-scale", type=int, required=True)
    ci_matrix = commands.add_parser("ci-matrix")
    ci_matrix.add_argument("--output", required=True)
    templates = commands.add_parser("templates")
    templates.add_argument("--template-file", action="append")
    commands.add_parser("plugins")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.command == "generate":
        request = BenchmarkRequest.from_dict(_read(args.request))
        capabilities = _read(args.capabilities) if args.capabilities else None
        registry = builtin_template_registry()
        for path in args.template_file or ():
            registry.load_file(Path(path))
        summary = ProductionGenerator(BENCHMARKS_DIR).generate(
            request, Path(args.workspace), capabilities=capabilities,
            release_version=args.release_version, templates=registry,
        )
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 0
    if args.command == "worker-run":
        request = BenchmarkRequest.from_dict(_read(args.request))
        registry = builtin_template_registry()
        for path in args.template_file or ():
            registry.load_file(Path(path))
        context = WorkerContext.build(request, _read(args.capabilities), registry)
        coordinator = BenchmarkCoordinator(
            Path(args.state), ArtifactStore(Path(args.store))
        )
        result = run_external_worker_once(
            coordinator, context, role=args.role, worker_id=args.worker_id
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    if args.command == "score":
        result = score_submission(_read(args.evidence))
        path = _write(args.output, result)
        print(json.dumps({"output": str(path), **result}, indent=2, sort_keys=True))
        return 0 if result["passed"] else 2
    if args.command.startswith("schedule-"):
        scheduler = DistributedScheduler(Path(args.scheduler))
        if args.command == "schedule-run":
            result = ProductionWorkerRuntime(
                BENCHMARKS_DIR, scheduler, Path(args.allowed_root)
            ).run_once(
                worker_id=args.worker_id, resource_class=args.resource_class,
                max_scale=args.max_scale,
            )
            print(json.dumps(result, indent=2, sort_keys=True)); return 0
        if args.command == "schedule-enqueue":
            job = ProductionJob.from_dict(_read(args.job)); scheduler.enqueue(job)
            print(f"enqueued_job={job.job_id}"); return 0
        if args.command == "schedule-status":
            recovered = scheduler.recover_expired()
            print(json.dumps({"state": scheduler.load(), "recovered": recovered}, indent=2, sort_keys=True)); return 0
        if args.command == "schedule-claim":
            print(json.dumps(scheduler.claim(
                worker_id=args.worker_id, resource_class=args.resource_class,
                max_scale=args.max_scale,
            ), indent=2, sort_keys=True)); return 0
        if args.command == "schedule-complete":
            scheduler.complete(args.job_id, args.lease_id, _read(args.result))
            print(f"completed_job={args.job_id}"); return 0
        scheduler.fail(
            args.job_id, args.lease_id, args.error, quarantine=args.quarantine
        )
        print(f"failed_job={args.job_id} quarantine={args.quarantine}"); return 0
    if args.command == "ci-matrix":
        value = continuous_validation_matrix(); path = _write(args.output, value)
        print(json.dumps({"output": str(path), **value}, indent=2, sort_keys=True)); return 0
    if args.command == "templates":
        registry = builtin_template_registry()
        for path in args.template_file or ():
            registry.load_file(Path(path))
        print(json.dumps([
            item.to_dict() for item in registry.inventory()
        ], indent=2, sort_keys=True)); return 0
    if args.command == "artifact-put":
        raw = _read(args.artifact)
        if not raw.get("artifact_fingerprint"):
            raw["artifact_fingerprint"] = ""
            artifact = AgentArtifact(
                artifact_type=raw["artifact_type"], artifact_id=raw["artifact_id"],
                producer=raw["producer"], payload=dict(raw["payload"]),
                input_fingerprints=tuple(raw.get("input_fingerprints", ())),
                capabilities_required=tuple(raw.get("capabilities_required", ())),
                warnings=tuple(raw.get("warnings", ())),
                schema_version=int(raw.get("schema_version", 1)),
            )
        else:
            artifact = AgentArtifact.from_dict(raw)
        path = ArtifactStore(Path(args.store)).write(artifact)
        print(f"stored_artifact={artifact.artifact_id} path={path}")
        return 0
    if args.command == "compile":
        spec = BenchmarkBundleSpec.from_dict(_read(args.spec))
        compiler = BundleCompiler(BENCHMARKS_DIR, ArtifactStore(Path(args.store)))
        capabilities = _read(args.capabilities) if args.capabilities else None
        bundle = compiler.compile(spec, capabilities=capabilities)
        path = compiler.write(bundle, Path(args.output))
        print(f"compiled_bundle={bundle.benchmark_id} fingerprint={bundle.bundle_fingerprint} output={path}")
        return 0
    if args.command in {"review", "validate", "split", "run", "qualify", "scale-validate"}:
        bundle = CompiledBenchmarkBundle.from_dict(_read(args.bundle))
        if args.command == "review":
            print(json.dumps(bundle.safety_review, indent=2, sort_keys=True))
            return 0 if bundle.safety_review.get("approved") else 2
        if args.command == "validate":
            print(f"valid_bundle={bundle.benchmark_id} fingerprint={bundle.bundle_fingerprint}")
            return 0
        if args.command == "split":
            public = _write(args.public_output, bundle.public_bundle)
            private = _write(args.private_output, bundle.private_bundle)
            print(f"public_bundle={public} private_bundle={private}")
            return 0
        if args.command == "run":
            executor = BundleLifecycleExecutor(
                Path(args.journal_dir), DockerLifecycleRunner()
            )
            path = executor.run(
                bundle, _read(args.capabilities), Path(args.output),
                blind_mode=True,
            )
            print(f"bundle_lifecycle_receipt={path}")
            return 0
        if args.command == "qualify":
            path = qualify_bundle(bundle, [Path(x) for x in args.receipt], Path(args.output))
            print(f"qualified_bundle={bundle.benchmark_id} record={path}")
            return 0
        report = validate_bundle_scales(
            bundle, args.size or (5, 20, 100, 1000, 10000),
            base_capabilities=(
                _read(args.capabilities) if args.capabilities else None
            ),
        )
        path = _write(args.output, report)
        print(json.dumps({"report": str(path), **report}, indent=2, sort_keys=True))
        return 0 if report["passed"] else 2
    if args.command == "coordinate-init":
        raw = _read(args.tasks)
        tasks = tuple(AgentTask.from_dict(x) for x in raw.get("tasks", raw))
        coordinator = BenchmarkCoordinator(Path(args.state), ArtifactStore(Path(args.store)))
        state = coordinator.initialize(tasks)
        print(json.dumps({"state": str(Path(args.state).resolve()), "ready": coordinator.ready_tasks(), "definition_fingerprint": state["definition_fingerprint"]}, indent=2))
        return 0
    if args.command == "coordinate-status":
        coordinator = BenchmarkCoordinator(Path(args.state), ArtifactStore(Path(args.store)))
        recovered = coordinator.recover_expired_leases()
        print(json.dumps({"state": coordinator.load(), "ready": coordinator.ready_tasks(), "recovered_leases": recovered}, indent=2, sort_keys=True))
        return 0
    if args.command == "coordinate-claim":
        coordinator = BenchmarkCoordinator(Path(args.state), ArtifactStore(Path(args.store)))
        print(json.dumps(coordinator.claim_next(
            worker_id=args.worker_id, agent_role=args.agent_role
        ), indent=2, sort_keys=True))
        return 0
    if args.command == "coordinate-complete":
        coordinator = BenchmarkCoordinator(Path(args.state), ArtifactStore(Path(args.store)))
        raw = _read(args.artifact)
        artifact = AgentArtifact.from_dict(raw)
        path = coordinator.complete_claim(
            args.task_id, args.lease_id, artifact
        )
        print(f"completed_task={args.task_id} artifact={path}")
        return 0
    if args.command == "coordinate-fail":
        coordinator = BenchmarkCoordinator(Path(args.state), ArtifactStore(Path(args.store)))
        coordinator.fail_claim(args.task_id, args.lease_id, args.error)
        print(f"failed_task={args.task_id}")
        return 0
    if args.command == "plugins":
        from generator.faults.drivers import DRIVERS
        print(json.dumps([x.to_dict() for x in builtin_registry(DRIVERS).inventory()], indent=2, sort_keys=True))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
