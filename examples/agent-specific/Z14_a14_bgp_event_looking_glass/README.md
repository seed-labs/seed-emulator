# Z14: A14 BGP Event Looking Glass

`Z14` is the agent-facing runtime bundle for `examples/basic/A14_bgp_event_looking_glass/output`.

Use it when the goal is to inspect a BGP event dashboard together with a
route-table looking glass and reason about what each surface can and cannot
show.

## Best Use

- control-plane observability demos
- route-state versus event-stream comparison
- BGP looking glass product exploration

## Tool Path

1. `workspace_refresh`
2. `inventory_list_nodes`
3. `routing_protocol_summary`
4. `routing_looking_glass`
5. `ops_logs` / `ops_exec` for dashboard and event validation

## Command

```bash
./scripts/seed-codex run \
  "Attach to examples/basic/A14_bgp_event_looking_glass/output; locate the route-table looking glass and the ExaBGP event dashboard, then explain what each one reveals about BGP behavior." \
  --workspace-name z14_probe \
  --attach-output-dir examples/basic/A14_bgp_event_looking_glass/output \
  --policy read_only
```

## Status

- live readiness: `conditional_go`
- strongest new observability bundle for BGP control-plane events
- good showcase for future BGP LG product work
