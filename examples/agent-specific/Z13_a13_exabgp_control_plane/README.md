# Z13: A13 ExaBGP Control Plane Tooling

`Z13` is the agent-facing runtime bundle for `examples/basic/A13_exabgp_control_plane/output`.

Use it when the goal is to reason about ExaBGP as an embedded control-plane
tool, inspect its peer state, and reuse it for later BGP experiments.

## Best Use

- ExaBGP discovery and inspection
- announcement evidence review
- control-plane experiment planning

## Tool Path

1. `workspace_refresh`
2. `inventory_list_nodes`
3. `routing_protocol_summary`
4. `ops_logs` / `ops_exec` for ExaBGP logs and config confirmation

## Command

```bash
./scripts/seed-codex run \
  "Attach to examples/basic/A13_exabgp_control_plane/output; locate the ExaBGP tool node, summarize its BGP peer, current announcements, and available control-plane evidence." \
  --workspace-name z13_probe \
  --attach-output-dir examples/basic/A13_exabgp_control_plane/output \
  --policy read_only
```

## Status

- live readiness: `conditional_go`
- best current ExaBGP runtime bundle
- useful for later controlled injection stories
