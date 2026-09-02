# Scenario documents

<!-- README_SYNC_REQUIRED: Update this file and benchmarks/README.md whenever this directory's contract changes. -->

This directory is reserved for explicitly persisted user scenarios. The repository no longer ships a topology-specific default scenario and the CLI never infers one from an examples tree.

Every scenario must choose one topology mode:

- `python_discovered`: carries the `artifact_id`, `compose_path`, descriptor, and source path returned by `benchmark.topology.discover_python`;
- `runtime_discovered`: binds an already running Compose project discovered by `benchmark.runtime.describe`.

Python sources are materialized through the single `benchmark.topology.lifecycle` interface. Runtime scenarios do not own their project's lifecycle. Fault authoring, candidate grants, probes, scoring, and naming remain explicit scenario fields and are validated by `benchmark_agent.scenario`.
