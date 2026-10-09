"""Convert resource mappings from cluster YAML to internal MiB units.

No files or runtime resources change. memoryGb is a compatibility spelling
for binary GiB, consistent with this project's existing VM size convention.
"""
from decimal import Decimal, InvalidOperation
from typing import Any


def readMemoryMiB(resources: dict[str, Any], default: int = 0) -> int:
    """Read memory from resources, rejecting invalid or conflicting units."""
    converted = []
    for key, factor in (
        ("memoryGiB", 1024), ("memoryGb", 1024),
        ("memoryMb", 1), ("memory_mb", 1),
    ):
        if key not in resources:
            continue
        try:
            value = Decimal(str(resources[key])) * factor
        except (InvalidOperation, ValueError):
            raise ValueError(f"{key} must be a positive numeric memory size") from None
        if not value.is_finite() or value <= 0 or value != value.to_integral_value():
            raise ValueError(f"{key} must represent a positive whole number of MiB")
        converted.append(int(value))
    if len(set(converted)) > 1:
        raise ValueError("Conflicting memory units in resource configuration")
    return converted[0] if converted else default


def normalizeMemory(resources: dict[str, Any]) -> None:
    """Replace supported memory fields in resources with canonical memoryMb."""
    value = readMemoryMiB(resources)
    if value:
        for key in ("memoryGiB", "memoryGb", "memory_mb"):
            resources.pop(key, None)
        resources["memoryMb"] = value
