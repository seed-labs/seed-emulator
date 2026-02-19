# Dialogue: SEC_B29_DNS_MAIL_ABUSE_RESPONSE

## High-level mission flow (`seed_agent_task_*`)

1. `seed_agent_task_begin(...)`
   - key params: `workspace_name=lab1`, `attach_output_dir=<B29 output>`, `context_json={"suspected_domain":"evil.example"}`
   - expected status: `awaiting_confirmation` (contains `act: net_ops`)
2. `seed_agent_task_execute(session_id, approval_token="YES_RUN_DYNAMIC_FAULTS")`
   - expected status: `ok`
3. `seed_agent_task_status(session_id)`
   - expected status: `ok`

## Fallback low-level flow (`seedops_*`)

1. `workspace_attach_compose`
2. `workspace_refresh`
3. `ops_logs`
4. `routing_bgp_summary`
5. `ops_exec` (mitigation check)

## Branch expectations

- `awaiting_confirmation`: risk gate before execute
- `needs_input`: missing domain or attach target
- `error`: response payload malformed or non-JSON

