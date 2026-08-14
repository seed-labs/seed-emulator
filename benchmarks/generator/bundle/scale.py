"""Plan-only scale validation for compiled multi-agent bundles."""

from __future__ import annotations

from datetime import datetime, timezone
import time
from typing import Dict, Iterable

from generator.bundle.compiler import resolve_assets
from generator.bundle.models import CompiledBenchmarkBundle
from generator.bundle.pilot import pilot_capabilities
from generator.bundle.specs import ServiceSpec, TestSpec, WorkloadSpec


def validate_bundle_scales(
    bundle: CompiledBenchmarkBundle,
    sizes: Iterable[int] = (5, 20, 100, 1000, 10000),
) -> Dict[str, object]:
    results = []
    private = bundle.private_bundle
    selectors = [
        *(ServiceSpec.from_dict(x).selector for x in private["services"]),
        *(WorkloadSpec.from_dict(x).source for x in private["workloads"]),
        *(TestSpec.from_dict(x).selector for x in private["tests"]),
    ]
    for size in sizes:
        if not 5 <= int(size) <= 10000:
            raise ValueError("scale must be between 5 and 10000")
        capabilities = pilot_capabilities(int(size))
        started = time.process_time_ns()
        resolutions = [resolve_assets(item, capabilities) for item in selectors]
        elapsed = time.process_time_ns() - started
        results.append({
            "asset_count": int(size), "selector_count": len(selectors),
            "resolved_asset_count": sum(len(item) for item in resolutions),
            "planning_seconds": round(elapsed / 1_000_000_000, 6),
            "execution_mode": "plan_only_no_container_launch",
            "passed": all(resolutions),
        })
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "bundle_fingerprint": bundle.bundle_fingerprint,
        "results": results,
        "passed": all(item["passed"] for item in results),
    }
