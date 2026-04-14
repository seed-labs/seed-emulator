# Dialogue: TS_B00_PREFIX_HIJACK_LIVE

## High-level mission flow (`seed_agent_task_*`)

1. `seed_agent_task_begin(...)`
   - key params:
     - `workspace_name=lab1`
     - `attach_output_dir=<B00 output>`
     - `context_json={"target_prefix":"10.150.0.0/24","attacker_asn":"151"}`
   - expected status: `awaiting_confirmation`
2. `seed_agent_task_execute(session_id)`
   - with `approval_token=YES_RUN_DYNAMIC_FAULTS`
   - expected status: `ok`
3. `seed_agent_task_status(session_id)`
   - expected status: `ok`

## Live execution semantics

- This mission performs live `bgp_announce_prefix` and `bgp_withdraw_prefix` actions.
- It uses `net_ops` stage policy and requires confirmation before execution.
- It must always rollback and verify post-rollback routing health.

## Fallback low-level flow (`seedops_*`)

1. `workspace_attach_compose`
2. `workspace_refresh`
3. `routing_bgp_summary`
4. `bgp_announce_prefix`
5. `routing_bgp_summary`
6. `traceroute`
7. `bgp_withdraw_prefix`
8. `routing_bgp_summary`

## Branch expectations

- `needs_input`: missing `attach_output_dir` / `target_prefix` / `attacker_asn`
- `awaiting_confirmation`: missing approval token
- `upstream_error`: SeedOps unavailable
- `ok`: live hijack executed, evidence captured, rollback completed
