#!/usr/bin/env python3
"""CLI for compiling, selecting, measuring and recovering fault plans."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from generator.faults.compiler import compile_fault_set
from generator.faults.coverage import measure_coverage, select_combinations
from generator.faults.journal import FaultExecutor
from generator.faults.models import CompiledFaultPlan, FaultSpec
from generator.faults.software import discover_software_fault_specs


def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _load_plans(paths):
    return tuple(CompiledFaultPlan.from_dict(_read(Path(path))) for path in paths)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="FaultSpec v1 compiler and executor")
    sub = root.add_subparsers(dest="command", required=True)
    compile_p = sub.add_parser("compile")
    compile_p.add_argument("--spec", required=True)
    compile_p.add_argument("--capabilities", required=True)
    compile_p.add_argument("--relationship", default="independent")
    compile_p.add_argument("--output", required=True)
    select_p = sub.add_parser("select")
    select_p.add_argument("--candidates", required=True)
    select_p.add_argument("--capabilities", required=True)
    select_p.add_argument("--count", type=int, required=True)
    select_p.add_argument("--max-components", type=int, default=3)
    select_p.add_argument("--seed", required=True)
    select_p.add_argument("--output", required=True)
    discover_p = sub.add_parser("discover-software")
    discover_p.add_argument("--capabilities", required=True)
    discover_p.add_argument("--seed", required=True)
    discover_p.add_argument("--output", required=True)
    validate_software = sub.add_parser("validate-software")
    validate_software.add_argument("--capabilities", required=True)
    validate_software.add_argument("--seed", required=True)
    validate_software.add_argument("--journal-dir", required=True)
    validate_software.add_argument("--output", required=True)
    coverage_p = sub.add_parser("coverage")
    coverage_p.add_argument("--plan", action="append", required=True)
    coverage_p.add_argument("--capabilities", required=True)
    coverage_p.add_argument("--output")
    for name in ("inject", "recover"):
        command = sub.add_parser(name)
        command.add_argument("--plan", required=True)
        command.add_argument("--execution-id", required=True)
        command.add_argument("--journal-dir", required=True)
        if name == "inject":
            command.add_argument(
                "--wait-duration", action="store_true",
                help="wait for the first positive duration and fail-safe recover",
            )
    recover_incomplete = sub.add_parser("recover-incomplete")
    recover_incomplete.add_argument("--plan", action="append", required=True)
    recover_incomplete.add_argument("--journal-dir", required=True)
    return root


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    if args.command == "compile":
        raw = _read(Path(args.spec))
        values = raw if isinstance(raw, list) else raw.get("faults", [raw])
        specs = tuple(FaultSpec.from_dict(x) for x in values)
        relationship = "single" if len(specs) == 1 else args.relationship
        plan = compile_fault_set(specs, _read(Path(args.capabilities)), relationship=relationship)
        _write(Path(args.output), plan.to_dict())
        print(f"compiled_plan={args.output} fingerprint={plan.plan_fingerprint}")
        return 0
    if args.command == "select":
        specs = tuple(FaultSpec.from_dict(x) for x in _read(Path(args.candidates)))
        plans = select_combinations(
            specs, _read(Path(args.capabilities)), count=args.count,
            master_seed=args.seed, max_components=args.max_components,
        )
        _write(Path(args.output), [x.to_dict() for x in plans])
        print(f"selected_plans={len(plans)} output={args.output}")
        return 0
    if args.command == "discover-software":
        specs = discover_software_fault_specs(
            _read(Path(args.capabilities)), master_seed=args.seed
        )
        _write(Path(args.output), [item.to_dict() for item in specs])
        print(f"discovered_software_faults={len(specs)} output={args.output}")
        return 0
    if args.command == "validate-software":
        capabilities = _read(Path(args.capabilities))
        specs = discover_software_fault_specs(capabilities, master_seed=args.seed)
        if not specs:
            raise ValueError("capability manifest exposes no software fault profiles")
        executor = FaultExecutor(Path(args.journal_dir))
        from generator.faults.drivers import get_driver
        from generator.templates import evaluate_verifier

        results = []
        for index, spec in enumerate(specs):
            plan = compile_fault_set((spec,), capabilities, relationship="single")
            action = plan.actions[0]
            driver = get_driver(action.driver)
            snapshot_code, snapshot = driver.snapshot(action, executor.runner)
            active_code, active_output = driver.verify_active(action, executor.runner)
            baseline_active = evaluate_verifier(
                action.active_verifier_kind,
                action.active_verifier_value,
                active_output,
            )
            if snapshot_code != 0 or baseline_active:
                raise RuntimeError(
                    f"software fault baseline is invalid for {spec.fault_id}: "
                    f"snapshot={snapshot_code}, active={active_code}, "
                    f"output={(snapshot + active_output)[:500]}"
                )
            execution_id = f"software-{index:04d}-{spec.fault_id}"
            journal = executor.inject(plan, execution_id)
            injected = _read(journal)
            if injected.get("status") != "active":
                raise RuntimeError(f"software fault did not become active: {spec.fault_id}")
            executor.recover(plan, execution_id)
            recovered = _read(journal)
            if recovered.get("status") != "recovered":
                raise RuntimeError(f"software fault did not recover: {spec.fault_id}")
            results.append({
                "fault_id": spec.fault_id,
                "fault_type": spec.fault_type,
                "target": action.targets[0],
                "artifact": action.artifact,
                "plan_fingerprint": plan.plan_fingerprint,
                "baseline_snapshot": snapshot.strip()[:256],
                "baseline_fault_inactive": True,
                "injection_verified": True,
                "recovery_verified": True,
                "journal": str(journal.resolve()),
            })
        report = {
            "schema_version": 1,
            "mode": "no_ai_software_fault_lifecycle",
            "ai_invoked": False,
            "topology_fingerprint": capabilities.get("topology_fingerprint", ""),
            "software_fault_count": len(results),
            "all_passed": all(
                item["injection_verified"] and item["recovery_verified"]
                for item in results
            ),
            "results": results,
        }
        _write(Path(args.output), report)
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if args.command == "coverage":
        report = measure_coverage(
            _load_plans(args.plan), _read(Path(args.capabilities))
        ).to_dict()
        if args.output:
            _write(Path(args.output), report)
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if args.command == "recover-incomplete":
        plans = _load_plans(args.plan)
        by_fingerprint = {item.plan_fingerprint: item for item in plans}
        recovered = FaultExecutor(Path(args.journal_dir)).recover_incomplete(
            by_fingerprint
        )
        print(json.dumps({"recovered": [str(path) for path in recovered]}, indent=2))
        return 0
    plan = CompiledFaultPlan.from_dict(_read(Path(args.plan)))
    executor = FaultExecutor(Path(args.journal_dir))
    if args.command == "inject":
        path = executor.inject(plan, args.execution_id)
        if args.wait_duration:
            path = executor.wait_for_expiry(plan, args.execution_id)
    else:
        path = executor.recover(plan, args.execution_id)
    print(f"fault_{args.command}_journal={path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
