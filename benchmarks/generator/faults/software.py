"""Discover deterministic FaultSpec candidates from software capabilities."""

from __future__ import annotations

import re
from typing import Any, Mapping, Tuple

from generator.faults.models import FaultSpec, canonical_sha256


def _id(value: object) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", str(value).lower()).strip("_")
    return normalized[:28] or "software"


def discover_software_fault_specs(
    capabilities: Mapping[str, Any], *, master_seed: str
) -> Tuple[FaultSpec, ...]:
    """Create one bounded candidate per asset/profile advertised by a build."""
    if not master_seed:
        raise ValueError("software fault discovery requires a master seed")
    discovered = []
    seen = set()
    for asset in sorted(
        capabilities.get("assets") or (), key=lambda item: str(item.get("container", ""))
    ):
        container = str(asset.get("container", ""))
        if not container:
            continue
        for software in sorted(
            asset.get("software") or (), key=lambda item: str(item.get("software_id", ""))
        ):
            software_id = str(software.get("software_id", ""))
            for profile in sorted(
                software.get("fault_profiles") or (),
                key=lambda item: str(item.get("profile_id", "")),
            ):
                profile_id = str(profile.get("profile_id", ""))
                fault_type = str(profile.get("fault_type", ""))
                identity = (container, software_id, profile_id, fault_type)
                if not all(identity) or identity in seen:
                    continue
                seen.add(identity)
                suffix = canonical_sha256({
                    "identity": identity, "master_seed": master_seed,
                    "topology": capabilities.get("topology_fingerprint", ""),
                })[:10]
                fault_id = f"sw_{_id(software_id)}_{_id(profile_id)}_{suffix}"[:95]
                discovered.append(FaultSpec(
                    fault_id=fault_id,
                    fault_type=fault_type,
                    selector={
                        "container": container,
                        "software": software_id,
                        "fault_profile": profile_id,
                    },
                    parameters={},
                    expectations={
                        "must_break": [f"software:{software_id}:{profile_id}"],
                        "must_preserve": ["unselected-assets"],
                    },
                    safety={
                        "max_affected_assets": 1,
                        "max_affected_asns": 1,
                        "protected_assets": [],
                        "require_recovery": True,
                    },
                    seed=f"{master_seed}:{suffix}",
                    schedule={"at_seconds": 0, "duration_seconds": 30},
                ))
    return tuple(discovered)
