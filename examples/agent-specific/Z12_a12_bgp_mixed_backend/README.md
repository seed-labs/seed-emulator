# Z12: A12 Mixed BIRD / FRR BGP Backend

`Z12` is the agent-facing runtime bundle for `examples/basic/A12_bgp_mixed_backend/output`.

Use it when the goal is to inspect or validate selective FRR migration inside a
mixed BIRD/FRRouting control plane.

## Best Use

- backend-aware BGP diagnostics
- FRR migration planning on already-running routers
- interoperability checks between BIRD and FRR speakers

## Tool Path

1. `routing_protocol_summary(auto)`
2. `inventory_list_nodes`
3. `routing_looking_glass`
4. `ops_exec` only to collect explicit `birdc` or `vtysh` evidence

## Command

```bash
./scripts/seed-codex run \
  "Attach to examples/basic/A12_bgp_mixed_backend/output; identify which routers use BIRD versus FRRouting, confirm interoperability evidence, and propose the safest next FRR migration step." \
  --workspace-name z12_probe \
  --attach-output-dir examples/basic/A12_bgp_mixed_backend/output \
  --policy read_only
```

## Status

- live readiness: `conditional_go`
- strongest new FRR migration narrative
- best current mixed-backend BGP showcase
