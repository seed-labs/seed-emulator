# Z01: Y01 Prefix Hijack Drill Candidate

`Z01` packages `examples/yesterday_once_more/Y01_bgp_prefix_hijacking/demo/output` as an agent-specific runtime candidate.

This is not the default stable bundle.
It exists because Y01 shows the strongest routing-security potential, but the runtime is still heavier than B00/B29.

## Best Use

- read-only pre-drill analysis
- scope selection for routing-security observation
- evidence design for before/during/after comparison

## Tool Path

Start with:

- `seed_agent_run`
- `inventory_list_nodes`
- `routing_protocol_summary`
- `routing_looking_glass`

Use live mutation only after explicit policy and runtime checks.

## Commands

```bash
./scripts/seed-codex run \
  "Attach to examples/yesterday_once_more/Y01_bgp_prefix_hijacking/demo/output; only inspect the running environment and identify how a prefix hijack should be observed." \
  --workspace-name z01_probe \
  --attach-output-dir examples/yesterday_once_more/Y01_bgp_prefix_hijacking/demo/output \
  --policy read_only
```

## Status

- live readiness: `conditional_go`
- use as a strong candidate, not the only guaranteed live path
