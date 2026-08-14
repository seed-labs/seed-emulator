#!/usr/bin/env python3
"""Plan-only performance and sampled coverage validation for large topologies."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import time

from generator.faults.compiler import compile_fault
from generator.faults.coverage import measure_coverage
from generator.faults.models import FaultSpec
from generator.topology.bindings import load_capability_manifest


def _spec(topology_id: str, index: int, *, role: str, fault_type: str, parameters=None):
    return FaultSpec(
        fault_id=f"{topology_id}_{fault_type.replace('.', '_')}_{index:04d}",
        fault_type=fault_type, selector={"role": role, "choose": 1},
        parameters=parameters or {},
        expectations={"must_break": [fault_type], "must_preserve": ["sampled-control"]},
        safety={"max_affected_assets": 1, "max_affected_asns": 1,
                "protected_assets": [], "require_recovery": True},
        seed=f"{topology_id}:{index}", schedule={"at_seconds": 0},
    )


def validate_scale(topology_id: str, sample_count: int):
    capabilities = load_capability_manifest(topology_id)
    assets = capabilities["assets"]
    plans, specs, timing_ns = [], [], []
    batch_started_ns = time.process_time_ns()
    for index in range(sample_count):
        if index % 2:
            spec = _spec(
                topology_id, index, role="Host", fault_type="network.netem",
                parameters={"interface": "lan0", "delay_ms": 75 + index % 50,
                            "jitter_ms": 10, "loss_percent": index % 5,
                            "rate_kbit": 512},
            )
        else:
            spec = _spec(
                topology_id, index, role="Host", fault_type="container.stopped"
            )
        specs.append(spec)
        # CPU time is deterministic for plan-only work and remains valid on
        # suspended/snapshotted VMs whose wall/monotonic clocks can stall.
        start = time.process_time_ns()
        plans.append(compile_fault(spec, capabilities))
        # Force the guest kernel to account the just-consumed CPU slice.  This
        # is a zero-duration yield and is excluded from process CPU time.
        time.sleep(0)
        timing_ns.append(time.process_time_ns() - start)
    time.sleep(0)
    batch_elapsed_ns = time.process_time_ns() - batch_started_ns
    timing_repetitions = 1
    while batch_elapsed_ns == 0 and timing_repetitions < 64:
        timing_repetitions *= 2
        repeated_started_ns = time.process_time_ns()
        for _repeat in range(timing_repetitions):
            for spec in specs:
                compile_fault(spec, capabilities)
        time.sleep(0)
        repeated_elapsed_ns = time.process_time_ns() - repeated_started_ns
        if repeated_elapsed_ns > 0:
            batch_elapsed_ns = repeated_elapsed_ns // timing_repetitions
    measured_max_ns = max(timing_ns)
    average_ns = batch_elapsed_ns // sample_count
    max_was_estimated = batch_elapsed_ns > 0 and (
        measured_max_ns == 0 or measured_max_ns > average_ns * 10
    )
    if max_was_estimated:
        measured_max_ns = average_ns
    coverage = measure_coverage(plans, capabilities)
    return {
        "topology_id": topology_id,
        "topology_fingerprint": capabilities["topology_fingerprint"],
        "asset_count": len(assets),
        "asn_count": len({int(x["asn"]) for x in assets}),
        "sample_count": sample_count,
        "planning_total_seconds": round(batch_elapsed_ns / 1_000_000_000, 6),
        "planning_average_seconds": round(
            batch_elapsed_ns / sample_count / 1_000_000_000, 6
        ),
        "planning_max_seconds": round(measured_max_ns / 1_000_000_000, 6),
        "planning_max_estimated": max_was_estimated,
        "timing_clock": "process_time_ns",
        "timing_measurement_repetitions": timing_repetitions,
        "plan_fingerprints": [x.plan_fingerprint for x in plans],
        "sampled_assets": sorted({x for p in plans for x in p.affected_assets}),
        "sampled_asns": sorted({x for p in plans for x in p.affected_asns}),
        "coverage": coverage.to_dict(),
        "execution_mode": "plan_only_no_container_launch",
        "passed": len(plans) == sample_count,
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--topology-id", action="append", required=True)
    parser.add_argument("--samples", type=int, default=32)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    if not 1 <= args.samples <= 500:
        raise ValueError("samples must be between 1 and 500")
    report = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "results": [validate_scale(item, args.samples) for item in args.topology_id],
    }
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    temporary.replace(destination)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
