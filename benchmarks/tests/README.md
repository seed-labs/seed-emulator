# Tests

<!-- README_SYNC_REQUIRED: Update this file and benchmarks/README.md whenever test scope or commands change. -->

The suite validates pure topology facts, strict LLM Proposal parsing, all four semantic FaultDrivers, target-bound Binding/catalog compilation, evidence drift rejection, Python and runtime discovery, unified topology lifecycle, Adapter-owned authorization, fault evidence, scoring, and the optional Inspect AI harness. `fixtures/runtime_scenario.json` is legacy compatibility data only.

The normal unit suite does not invoke Docker or an external model:

```bash
PYTHONPATH=benchmarks python3 -m unittest discover -s benchmarks/tests -v
```

Integration runs that change Docker state remain explicit and must use the Tool Service boundary.
