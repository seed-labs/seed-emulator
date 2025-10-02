"""Compatibility shims applied automatically when the test suite runs.

Parsimonious (pinned at 0.8.1 for legacy Ethereum tooling) still calls
`inspect.getargspec`, which was removed in Python 3.11.  By placing this
shim in `sitecustomize.py`, Python will import it automatically on startup
and we can safely bridge the gap without patching third-party sources.
"""
from __future__ import annotations

import inspect
from collections import namedtuple

if not hasattr(inspect, "getargspec"):
    FullArgSpec = inspect.FullArgSpec  # type: ignore[attr-defined]
    ArgSpec = namedtuple("ArgSpec", "args varargs keywords defaults")

    def getargspec(func):  # type: ignore[override]
        spec: FullArgSpec = inspect.getfullargspec(func)
        return ArgSpec(spec.args, spec.varargs, spec.varkw, spec.defaults)

    inspect.getargspec = getargspec  # type: ignore[attr-defined]
