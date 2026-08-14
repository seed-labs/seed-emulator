"""Coverage metrics and deterministic automatic fault-combination selection."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from itertools import combinations
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from generator.faults.compiler import compile_fault_set
from generator.faults.drivers import DRIVERS
from generator.faults.models import FaultSpec


@dataclass(frozen=True)
class CoverageReport:
    fault_types: Tuple[str, ...]
    drivers: Tuple[str, ...]
    assets: Tuple[str, ...]
    asns: Tuple[int, ...]
    relationships: Tuple[str, ...]
    pair_signatures: Tuple[str, ...]
    scores: Dict[str, float]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fault_types": list(self.fault_types), "drivers": list(self.drivers),
            "assets": list(self.assets), "asns": list(self.asns),
            "relationships": list(self.relationships),
            "pair_signatures": list(self.pair_signatures), "scores": self.scores,
        }


def measure_coverage(plans, capabilities: Mapping[str, Any]) -> CoverageReport:
    all_assets = {str(x["container"]) for x in capabilities.get("assets", [])}
    all_asns = {int(x["asn"]) for x in capabilities.get("assets", []) if "asn" in x}
    types = {a.category for p in plans for a in p.actions}
    drivers = {a.driver for p in plans for a in p.actions}
    assets = {x for p in plans for x in p.affected_assets}
    asns = {x for p in plans for x in p.affected_asns}
    relationships = {p.relationship for p in plans}
    pairs = {
        "+".join(sorted(a.driver for a in p.actions))
        for p in plans if len(p.actions) > 1
    }
    scores = {
        "asset_coverage": len(assets) / max(1, len(all_assets)),
        "asn_coverage": len(asns) / max(1, len(all_asns)),
        "driver_diversity": len(drivers) / max(1, len(DRIVERS)),
        "composition_coverage": min(1.0, len(pairs) / 4),
    }
    scores["weighted_total"] = round(
        scores["asset_coverage"] * .25 + scores["asn_coverage"] * .25
        + scores["driver_diversity"] * .30 + scores["composition_coverage"] * .20,
        6,
    )
    return CoverageReport(
        tuple(sorted(types)), tuple(sorted(drivers)), tuple(sorted(assets)),
        tuple(sorted(asns)), tuple(sorted(relationships)), tuple(sorted(pairs)), scores,
    )


def select_combinations(
    candidates: Sequence[FaultSpec],
    capabilities: Mapping[str, Any],
    *,
    count: int,
    master_seed: str,
    max_components: int = 3,
):
    """Greedily maximize new drivers/assets/ASNs while rejecting conflicts."""
    if count < 1 or max_components < 2:
        raise ValueError("invalid combination selection budget")
    pool = []
    upper = min(max_components, len(candidates))
    for size in range(2, upper + 1):
        for group in combinations(candidates, size):
            try:
                plan = compile_fault_set(group, capabilities, relationship="independent")
            except ValueError:
                continue
            tie = hashlib.sha256(
                (master_seed + plan.plan_fingerprint).encode("utf-8")
            ).hexdigest()
            pool.append((plan, tie))
    selected, seen_drivers, seen_assets, seen_asns, seen_pairs = [], set(), set(), set(), set()
    while pool and len(selected) < count:
        def utility(item):
            plan, tie = item
            drivers = {a.driver for a in plan.actions}
            pairs = {"+".join(sorted(drivers))}
            gain = (len(drivers - seen_drivers) * 100 +
                    len(set(plan.affected_asns) - seen_asns) * 20 +
                    len(set(plan.affected_assets) - seen_assets) * 5 +
                    len(pairs - seen_pairs) * 30)
            return gain, tie
        best = max(pool, key=utility)
        pool.remove(best)
        plan = best[0]
        selected.append(plan)
        seen_drivers.update(a.driver for a in plan.actions)
        seen_assets.update(plan.affected_assets)
        seen_asns.update(plan.affected_asns)
        seen_pairs.add("+".join(sorted(a.driver for a in plan.actions)))
    if len(selected) != count:
        raise ValueError(f"only selected {len(selected)}/{count} conflict-free combinations")
    return tuple(selected)
