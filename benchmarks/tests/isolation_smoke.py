#!/usr/bin/env python3
"""Manual smoke test entry point for benchmark topology isolation."""

from benchmark_cli import recreate_topology_for_isolation


if __name__ == "__main__":
    success = recreate_topology_for_isolation(
        "B00_mini_internet_firewall"
    )
    print("RECREATE_OK" if success else "RECREATE_FAILED")
    raise SystemExit(0 if success else 1)
