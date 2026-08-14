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
    scale.add_argument("--output", required=True)
    commands.add_parser("plugins")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
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
        report = validate_bundle_scales(bundle, args.size or (5, 20, 100, 1000, 10000))
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
        print(json.dumps(coordinator.claim_next(worker_id=args.worker_id), indent=2, sort_keys=True))
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
