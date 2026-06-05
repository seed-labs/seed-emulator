#!/usr/bin/env python3

from __future__ import annotations

try:
    from .base import TestRunner
except ImportError:
    from base import TestRunner


class SatelliteTestRunner(TestRunner):
    """Extension point for future satellite emulation tests."""

    runner_name = "satellite"
