# Z02: A02 MPLS / FRR Control-Plane Inspection

`Z02` is the agent-specific bundle for `examples/basic/A02_transit_as_mpls/output`.

Use this when the goal is to validate control-plane tooling and mixed routing backend behavior.

## Best Use

- protocol-aware routing summary validation
- FRR/MPLS inspection through explicit `vtysh` evidence
- attached-runtime regression checks for mixed BIRD/FRR nodes

## Tool Path

Default order:

1. `routing_protocol_summary(auto)`
2. `inventory_list_nodes`
3. `routing_looking_glass`
4. `ops_exec` with `vtysh` only when FRR/MPLS evidence is actually needed

## Command

```bash
./scripts/seed-codex run \
  "Attach to examples/basic/A02_transit_as_mpls/output; summarize routing backend behavior and identify where explicit FRR evidence is required." \
  --workspace-name z02_probe \
  --attach-output-dir examples/basic/A02_transit_as_mpls/output \
  --policy read_only
```

## Status

- live readiness: `conditional_go`
- strong tooling bundle
- not the strongest narrative bundle for a general audience
