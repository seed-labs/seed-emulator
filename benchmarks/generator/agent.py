#!/usr/bin/env python3
"""CLI and orchestration agent for generating large benchmark suites."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from typing import Dict, Iterable, List, Optional

from generator.contracts import ContractSnapshot, inspect_contracts
from generator.models import GenerationJob, SuiteManifest
from generator.planner import plan_suite
from generator.storage import suite_manifest_path, validate_manifest_file, write_manifest
from generator.templates import TEMPLATES
from generator.validator import validate_manifest


BENCHMARKS_DIR = Path(__file__).resolve().parents[1]


class BenchmarkGeneratorAgent:
    """Contract-aware planner, validator, and atomic suite writer."""

    def __init__(self, benchmarks_dir: Path = BENCHMARKS_DIR):
        self.benchmarks_dir = benchmarks_dir.resolve()

    def inspect(self) -> ContractSnapshot:
        return inspect_contracts(self.benchmarks_dir)

    def plan(self, job: GenerationJob) -> SuiteManifest:
        snapshot = self.inspect()
        manifest = plan_suite(
            job,
            contract_sha256=snapshot.sha256,
            benchmarks_dir=self.benchmarks_dir,
        )
        validate_manifest(manifest)
        return manifest

    def generate(
        self,
        job: GenerationJob,
        *,
        force: bool = False,
    ) -> Path:
        manifest = self.plan(job)
        return write_manifest(
            self.benchmarks_dir,
            manifest,
            force=force,
        )

    def validate(self, path: Path) -> SuiteManifest:
        manifest = validate_manifest_file(path)
        current = self.inspect()
        if manifest.contract_sha256 != current.sha256:
            raise ValueError(
                "manifest contract hash differs from the current benchmark interface"
            )
        if any(spec.main_score_eligible for spec in manifest.scenarios):
            from generator.promotion import verify_promotion_record

            verify_promotion_record(self.benchmarks_dir, manifest)
        return manifest

    def load_suite(self, suite_id: str) -> SuiteManifest:
        return self.validate(suite_manifest_path(self.benchmarks_dir, suite_id))

    def compile_fault_specs(self, specs, capabilities, *, relationship="independent"):
        """Public fault-planning entry point used by large-scale producers."""
        from generator.faults.compiler import compile_fault_set

        return compile_fault_set(specs, capabilities, relationship=relationship)

    def fault_coverage(self, plans, capabilities):
        from generator.faults.coverage import measure_coverage

        return measure_coverage(plans, capabilities)

    def select_fault_combinations(
        self, candidates, capabilities, *, count, master_seed, max_components=3
    ):
        from generator.faults.coverage import select_combinations

        return select_combinations(
            candidates, capabilities, count=count, master_seed=master_seed,
            max_components=max_components,
        )

    @staticmethod
    def build_batches(
        manifest: SuiteManifest,
        batch_size: int,
    ) -> List[Dict[str, object]]:
        if not 1 <= batch_size <= 500:
            raise ValueError("batch_size must be between 1 and 500")
        topology_order: List[str] = []
        grouped: Dict[str, List[str]] = {}
        for spec in manifest.scenarios:
            if spec.topology not in grouped:
                topology_order.append(spec.topology)
                grouped[spec.topology] = []
            grouped[spec.topology].append(spec.name)
        batches: List[Dict[str, object]] = []
        for topology in topology_order:
            names = grouped[topology]
            for offset in range(0, len(names), batch_size):
                batches.append(
                    {
                        "index": len(batches),
                        "topology": topology,
                        "scenarios": names[offset:offset + batch_size],
                    }
                )
        return batches

    def run_lifecycle_batches(
        self,
        manifest: SuiteManifest,
        *,
        batch_size: int,
        start_batch: int = 0,
        reuse_running: bool = False,
        dry_run: bool = False,
        receipt_prefix: str = "",
    ) -> List[Dict[str, object]]:
        batches = self.build_batches(manifest, batch_size)
        if not 0 <= start_batch <= len(batches):
            raise ValueError("start_batch is outside the planned batch range")
        planned = batches[start_batch:]
        if dry_run:
            return planned
        previous_topology = ""
        for batch in planned:
            index = int(batch["index"])
            topology = str(batch["topology"])
            report_path = self.benchmarks_dir / "reports" / (
                f"GENERATOR_{manifest.suite_id.upper()}_"
                f"LIFECYCLE_BATCH_{index:04d}.md"
            )
            command = [
                sys.executable,
                "-u",
                str(self.benchmarks_dir / "benchmark_cli.py"),
                "--agent",
                "rule",
                "--validate-only",
                "--scenario",
                ",".join(batch["scenarios"]),
                "--report",
                str(report_path),
            ]
            if receipt_prefix:
                receipt_path = self.benchmarks_dir / "reports" / (
                    f"{receipt_prefix}_BATCH_{index:04d}.json"
                )
                command.extend(["--receipt", str(receipt_path)])
            if (
                (index == start_batch and reuse_running)
                or (previous_topology and previous_topology == topology)
            ):
                command.append("--reuse-running")
            subprocess.run(
                command,
                cwd=self.benchmarks_dir.parent,
                check=True,
            )
            previous_topology = topology
        return planned

    def qualify(
        self,
        suite_id: str,
        *,
        topology_evidence: Path,
        observation_evidence: Path,
        rounds: int = 2,
        batch_size: int = 20,
        reuse_running: bool = False,
    ) -> Path:
        """Run independent no-AI lifecycle rounds and atomically promote."""
        from generator.promotion import MIN_LIFECYCLE_RUNS, promote_suite

        if rounds < MIN_LIFECYCLE_RUNS:
            raise ValueError(
                f"qualification requires at least {MIN_LIFECYCLE_RUNS} rounds"
            )
        manifest = self.load_suite(suite_id)
        receipt_paths = []
        for round_index in range(1, rounds + 1):
            prefix = f"PROMOTION_{suite_id.upper()}_ROUND_{round_index:02d}"
            batches = self.run_lifecycle_batches(
                manifest,
                batch_size=batch_size,
                reuse_running=(reuse_running or round_index > 1),
                receipt_prefix=prefix,
            )
            receipt_paths.extend(
                self.benchmarks_dir / "reports" /
                f"{prefix}_BATCH_{int(batch['index']):04d}.json"
                for batch in batches
            )
        return promote_suite(
            self.benchmarks_dir,
            suite_id,
            receipt_paths,
            topology_evidence=topology_evidence,
            observation_evidence=observation_evidence,
        )


def _add_job_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--suite-id", required=True)
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--seed", default="0")
    parser.add_argument(
        "--template",
        action="append",
        dest="templates",
        choices=sorted(TEMPLATES),
        help="Audited template to include; repeat to select multiple",
    )
    parser.add_argument("--topology", default="")
    parser.add_argument("--track", default="robustness")
    parser.add_argument(
        "--disabled",
        action="store_true",
        help="Write a suite that is not loaded by the scenario registry",
    )


def _job_from_args(args: argparse.Namespace) -> GenerationJob:
    return GenerationJob(
        suite_id=args.suite_id,
        case_count=args.count,
        master_seed=str(args.seed),
        template_ids=tuple(args.templates or ()),
        topology=args.topology,
        benchmark_track=args.track,
        enabled=not args.disabled,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate deterministic benchmark suites against current contracts"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    inventory = subparsers.add_parser("inventory")
    inventory.set_defaults(action="inventory")

    preview = subparsers.add_parser("preview")
    _add_job_arguments(preview)
    preview.set_defaults(action="preview")

    generate = subparsers.add_parser("generate")
    _add_job_arguments(generate)
    generate.add_argument("--force", action="store_true")
    generate.set_defaults(action="generate")

    validate = subparsers.add_parser("validate")
    validate.add_argument("--suite-id", required=True)
    validate.set_defaults(action="validate")

    batches = subparsers.add_parser("batches")
    batches.add_argument("--suite-id", required=True)
    batches.add_argument("--batch-size", type=int, default=20)
    batches.set_defaults(action="batches")

    lifecycle = subparsers.add_parser("run-lifecycle")
    lifecycle.add_argument("--suite-id", required=True)
    lifecycle.add_argument("--batch-size", type=int, default=20)
    lifecycle.add_argument("--start-batch", type=int, default=0)
    lifecycle.add_argument("--reuse-running", action="store_true")
    lifecycle.add_argument("--dry-run", action="store_true")
    lifecycle.set_defaults(action="lifecycle")
    promote = subparsers.add_parser("promote")
    promote.add_argument("--suite-id", required=True)
    promote.add_argument("--receipt", action="append", required=True)
    promote.add_argument("--topology-evidence", required=True)
    promote.add_argument("--observation-evidence", required=True)
    promote.set_defaults(action="promote")
    qualify = subparsers.add_parser("qualify")
    qualify.add_argument("--suite-id", required=True)
    qualify.add_argument("--rounds", type=int, default=2)
    qualify.add_argument("--batch-size", type=int, default=20)
    qualify.add_argument("--reuse-running", action="store_true")
    qualify.add_argument("--topology-evidence", required=True)
    qualify.add_argument("--observation-evidence", required=True)
    qualify.set_defaults(action="qualify")
    return parser


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    agent = BenchmarkGeneratorAgent()
    if args.action == "inventory":
        snapshot = agent.inspect()
        print(
            json.dumps(
                {
                    "benchmarks_dir": str(snapshot.benchmarks_dir),
                    "contract_sha256": snapshot.sha256,
                    "templates": {
                        key: {
                            "topology": value.topology,
                            "fault_type": value.fault_type,
                            "difficulty": value.difficulty,
                        }
                        for key, value in sorted(TEMPLATES.items())
                    },
                    "cli_options": snapshot.cli_options,
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    if args.action == "preview":
        manifest = agent.plan(_job_from_args(args))
        print(json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if args.action == "generate":
        path = agent.generate(_job_from_args(args), force=args.force)
        print(f"generated_suite={args.suite_id} manifest={path}")
        return 0
    if args.action == "validate":
        path = suite_manifest_path(BENCHMARKS_DIR, args.suite_id)
        manifest = agent.validate(path)
        print(
            f"valid_suite={manifest.suite_id} scenarios={len(manifest.scenarios)} "
            f"manifest={path}"
        )
        return 0
    if args.action == "batches":
        manifest = agent.load_suite(args.suite_id)
        batches = agent.build_batches(manifest, args.batch_size)
        print(json.dumps(batches, ensure_ascii=False, indent=2))
        return 0
    if args.action == "lifecycle":
        manifest = agent.load_suite(args.suite_id)
        batches = agent.run_lifecycle_batches(
            manifest,
            batch_size=args.batch_size,
            start_batch=args.start_batch,
            reuse_running=args.reuse_running,
            dry_run=args.dry_run,
        )
        print(
            json.dumps(
                {
                    "suite_id": manifest.suite_id,
                    "batches": batches,
                    "dry_run": args.dry_run,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    if args.action == "promote":
        from generator.promotion import promote_suite

        record = promote_suite(
            BENCHMARKS_DIR,
            args.suite_id,
            [Path(item) for item in args.receipt],
            topology_evidence=Path(args.topology_evidence),
            observation_evidence=Path(args.observation_evidence),
        )
        print(f"promoted_suite={args.suite_id} record={record}")
        return 0
    if args.action == "qualify":
        record = agent.qualify(
            args.suite_id,
            topology_evidence=Path(args.topology_evidence),
            observation_evidence=Path(args.observation_evidence),
            rounds=args.rounds,
            batch_size=args.batch_size,
            reuse_running=args.reuse_running,
        )
        print(f"qualified_suite={args.suite_id} record={record}")
        return 0
    raise AssertionError(args.action)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        # Standard Unix CLI behavior when output is intentionally truncated by
        # tools such as head(1).
        raise SystemExit(0)
