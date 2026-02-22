# Dialogue: RS_B00_CONVERGENCE_COMPARISON

## High-level mission flow (`seed_agent_task_*`)

1. `seed_agent_task_begin(...)`
   - key params: `workspace_name=lab1`, `attach_output_dir=<B00 output>`
   - `context_json={"comparison_target":"AS2<->AS3 convergence"}`
   - expected status: `ok` (read-only mission)
2. `seed_agent_task_execute(session_id)`
   - expected status: `ok`
3. `seed_agent_task_status(session_id)`
   - expected status: `ok`

## Fallback low-level flow (`seedops_*`)

1. `workspace_attach_compose`
2. `workspace_refresh`
3. `routing_bgp_summary` (snapshot A)
4. `sleep`
5. `routing_bgp_summary` (snapshot B)

## Branch expectations

- `needs_input`: missing comparison target
- `upstream_error`: SeedOps unreachable
- `error`: invalid task payload/JSON

