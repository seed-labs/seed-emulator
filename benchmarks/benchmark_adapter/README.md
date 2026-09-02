# Candidate Adapter

<!-- README_SYNC_REQUIRED: Update this file and benchmarks/README.md whenever the candidate contract changes. -->

The Adapter is the authoritative candidate authorization boundary. It exposes the minimum `agent_view`, validates action names and call budgets from `grant_spec.json`, binds project/service and fixed arguments, forwards only declared Tool Service operations, redacts results, and records every accepted or rejected action.

New grants do not contain a Tool Service bearer token: Tool Service is a thin operation adapter, while candidate policy belongs here. Legacy server-token fields may still appear in old run evidence but are ignored by the current Adapter. The candidate cannot discover the complete Tool Service catalog or choose arbitrary project, service, tool, or arguments.

```bash
BENCHMARK_GRANT_SPEC=/absolute/path/grant_spec.json \
PYTHONPATH=benchmarks python3 -m uvicorn benchmark_adapter.app:app --host 127.0.0.1 --port 8101
```
