# Dialogue: TS_B29_MAIL_REACHABILITY_DEBUG

## High-level mission flow (`seed_agent_task_*`)

1. `seed_agent_task_begin(...)`
   - key params: `workspace_name=lab1`, `attach_output_dir=<B29 output>`
   - `context_json={"source_node":"as150/mail_client","destination_node":"as151/mail_server"}`
   - expected status: `awaiting_confirmation`
2. `seed_agent_task_execute(..., approval_token="YES_RUN_DYNAMIC_FAULTS")`
   - expected status: `ok`
3. `seed_agent_task_status(session_id)`
   - expected status: `ok`

## Fallback low-level flow (`seedops_*`)

1. `workspace_attach_compose`
2. `workspace_refresh`
3. `ping` + `traceroute`
4. `ops_logs`
5. `artifacts_list`

## Branch expectations

- `needs_input`: missing source/destination node
- `blocked`: policy profile mismatch
- `timeout`: long-running diagnostics exceed limits

