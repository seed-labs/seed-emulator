# Dialogue: TS_B00_BGP_FLAP_ROOTCAUSE

## High-level mission flow (`seed_agent_task_*`)

1. `seed_agent_task_begin(...)`
   - key params: `workspace_name=lab1`, `attach_output_dir=<B00 output>`, `context_json={"suspect_router":"as2/r2"}`
   - expected status: `awaiting_confirmation` (task has `act: net_ops`)
2. `seed_agent_task_execute(..., approval_token="YES_RUN_DYNAMIC_FAULTS")`
   - expected status: `ok`
3. `seed_agent_task_status(session_id)`
   - expected status: `ok`

## Fallback low-level flow (`seedops_*`)

1. `workspace_attach_compose`
2. `workspace_refresh`
3. `routing_bgp_summary`
4. `traceroute`
5. `ops_exec("birdc show protocols all")`

## Branch expectations

- `needs_input`: missing `suspect_router` or attach target
- `awaiting_confirmation`: missing approval token
- `upstream_error`: SeedOps unavailable

