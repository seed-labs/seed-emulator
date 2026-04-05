# Z28: B28 Runtime Traffic Lab

`Z28` packages `examples/internet/B28_traffic_generator/3-multi-traffic-generator/output` as the main non-BGP attached-runtime sample.

## What It Proves

- the agent can enter a running lab without topology hints
- it can classify generator and receiver roles from runtime evidence
- it can design controlled experiments after read-only inspection

## Tool Path

Start with:

- `workspace_refresh`
- `inventory_list_nodes`
- `ops_logs`
- `ops_exec`

The important point is not shell cleverness.
The important point is runtime evidence: process list, sockets, logs, and node classes.

## Command

```bash
./scripts/seed-codex run \
  "Attach to examples/internet/B28_traffic_generator/3-multi-traffic-generator/output; identify traffic generator and receiver roles from runtime evidence only." \
  --workspace-name z28_probe \
  --attach-output-dir examples/internet/B28_traffic_generator/3-multi-traffic-generator/output \
  --policy read_only
```

## Status

- live readiness: `go`
- best current non-BGP attached-runtime bundle
