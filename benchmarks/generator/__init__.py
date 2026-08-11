"""Deterministic, contract-aware benchmark generation.

The package intentionally performs no eager imports. The scenario registry
loads the runtime adapter during its own initialization, so eager convenience
imports here would create a package initialization cycle.
"""
