# S02 — B00 Path Maintenance

## Goal

Diagnose path or routing degradation on an already-running B00 network:

- BGP summary
- route snapshots
- traceroute diagnostics

## Baseline

- Scenario baseline: `B00_mini_internet`
- Attach source: `${B00_OUTPUT_DIR}`

## Run

```bash
./examples/agent-base/S02_b00_path_maintenance/run.sh --mode both
```

Example with explicit output directory:

```bash
./examples/agent-base/S02_b00_path_maintenance/run.sh \
  --mode canonical \
  --output-dir examples/internet/B00_mini_internet/output
```

## Assertions

- plan/run status checks
- terminal job status
- non-empty `workspace_id` and `job_id`
- generated route and traceroute diagnostics files

## Outputs

Under `.../artifacts/S02_b00_path_maintenance/<timestamp>/`:

- `plan.json`
- `run.json`
- `diagnostics/routes.txt`
- `diagnostics/trace.txt`
