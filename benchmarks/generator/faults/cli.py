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
    coverage_p = sub.add_parser("coverage")
    coverage_p.add_argument("--plan", action="append", required=True)
    coverage_p.add_argument("--capabilities", required=True)
    coverage_p.add_argument("--output")
    for name in ("inject", "recover"):
        command = sub.add_parser(name)
        command.add_argument("--plan", required=True)
        command.add_argument("--execution-id", required=True)
        command.add_argument("--journal-dir", required=True)
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
    if args.command == "coverage":
        report = measure_coverage(
            _load_plans(args.plan), _read(Path(args.capabilities))
        ).to_dict()
        if args.output:
            _write(Path(args.output), report)
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    plan = CompiledFaultPlan.from_dict(_read(Path(args.plan)))
    executor = FaultExecutor(Path(args.journal_dir))
    if args.command == "inject":
        path = executor.inject(plan, args.execution_id)
    else:
        path = executor.recover(plan, args.execution_id)
    print(f"fault_{args.command}_journal={path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
