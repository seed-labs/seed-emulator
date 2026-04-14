# Z00: B00 Attached-Runtime Routing Ops

`Z00` is the agent-specific package for `examples/internet/B00_mini_internet/output`.

Use this bundle when the goal is attached-runtime routing work, not topology construction.

## What It Is Good For

- environment takeover on a clean Internet-style SEED lab
- router-centric maintenance and breakpoint diagnostics
- controlled latency experiments with rollback
- live routing security drills when a rollback path is required

## Tool Path

Primary high-level path:

- `seed_agent_run`
- `seed_agent_plan`
- `seed_agent_task_*`

Preferred low-level ops:

- `inventory_list_nodes`
- `routing_protocol_summary`
- `routing_looking_glass`
- `ops_logs`
- `job_get`
- `job_steps_list`
- `artifacts_list`

Do not start with shell commands unless the tool surface leaves a real gap.

## Task And Skill Fit

Mission tasks already aligned with `Z00`:

- `TS_B00_BGP_FLAP_ROOTCAUSE`
- `RS_B00_CONVERGENCE_COMPARISON`
- `TS_B00_PREFIX_HIJACK_LIVE`

Key `skill_patterns`:

- `attach-and-scan`
- `bgp-health-triage`
- `routing-drill-and-rollback`
- `evidence-collection`

## Commands

Interactive:

```bash
./scripts/seed-codex ui -m gpt-5.4 -c 'model_reasoning_effort="low"'
```

Read-only probe:

```bash
./scripts/seed-codex run \
  "Attach to examples/internet/B00_mini_internet/output; only do read-only routing and environment understanding." \
  --workspace-name z00_probe \
  --attach-output-dir examples/internet/B00_mini_internet/output \
  --policy read_only
```

Mission entry:

```bash
./scripts/seed-codex mission list --baseline B00
```

## Status

- live readiness: `go`
- use it as the default routing-focused attached-runtime bundle
- keep risky drills behind confirmation
