"""Test helpers package.

Keep this package import lightweight: unit tests should not require optional
runtime dependencies (e.g., the Python `docker` package) just to import
`tests.*`.
"""

from __future__ import annotations

import unittest

try:
    from .SeedEmuTestCase import SeedEmuTestCase as SeedEmuTestCase
except ModuleNotFoundError as exc:
    # Many integration tests rely on the python `docker` package via
    # SeedEmuTestCase. Allow pure unit tests to run even when it's missing.
    if exc.name not in {"docker"}:
        raise

    class SeedEmuTestCase(unittest.TestCase):
        @classmethod
        def setUpClass(cls, *args, **kwargs) -> None:  # type: ignore[override]
            raise unittest.SkipTest("python package 'docker' not installed; skipping docker-based tests")
