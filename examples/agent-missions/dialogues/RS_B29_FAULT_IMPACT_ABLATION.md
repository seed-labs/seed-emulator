# Dialogue: RS_B29_FAULT_IMPACT_ABLATION

## High-level mission flow (`seed_agent_task_*`)

1. `seed_agent_task_begin(...)`
   - key params: `workspace_name=lab1`, `attach_output_dir=<B29 output>`
   - `context_json={"fault_target":"as150/router0","fault_type":"packet_loss"}`
   - expected status: `awaiting_confirmation`
2. `seed_agent_task_execute(..., approval_token="YES_RUN_DYNAMIC_FAULTS")`
   - expected status: `ok`
3. `seed_agent_task_status(session_id)`
   - expected status: `ok`

## Fallback low-level flow (`seedops_*`)

1. `workspace_attach_compose`
2. `workspace_refresh` + baseline observations
3. `inject_fault(packet_loss)`
4. `routing_bgp_summary`
5. `inject_fault(reset)` + verification checks

## Branch expectations

- `awaiting_confirmation`: no valid approval token
- `blocked`: request executed under `read_only` profile
- `ok`: injection and rollback both completed

