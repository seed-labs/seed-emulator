# S01 — B29 Health Maintenance

## Goal

Run a read-only patrol on an already-running B29 email network:

- inventory refresh
- BGP summary on routers
- operational logs on hosts
- structured summary for next actions

## Baseline

- Scenario baseline: `B29_email_dns`
- Attach source: `${B29_OUTPUT_DIR}` (relative paths supported)

## Run

```bash
./examples/agent-base/S01_b29_health_maintenance/run.sh --mode both
```

Optional overrides:

```bash
./examples/agent-base/S01_b29_health_maintenance/run.sh \
  --mode canonical \
  --output-dir examples/internet/B29_email_dns/output \
  --policy read_only
```

## Assertions

- `status=ok`
- terminal `job_status`
- `compiled_plan.policy.allowed=true` (canonical path)
- `artifact_count>=1`

## Outputs

Under `.../artifacts/S01_b29_health_maintenance/<timestamp>/`:

- `response.canonical.json`
- `job.steps.json`
- `artifacts.list.json`
- `summary.md`
