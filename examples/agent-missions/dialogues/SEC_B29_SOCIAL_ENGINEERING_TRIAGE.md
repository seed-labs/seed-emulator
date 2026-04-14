# Dialogue: SEC_B29_SOCIAL_ENGINEERING_TRIAGE

## High-level mission flow (`seed_agent_task_*`)

1. `seed_agent_task_begin(task_id, objective, workspace_name, attach_output_dir, context_json)`
   - key params: `workspace_name=lab1`, `attach_output_dir=<B29 output>`, `context_json={"suspicious_sender":"attacker@example.net"}`
   - expected status: `ok` or `needs_input`
2. `seed_agent_task_execute(session_id, follow_job=true)`
   - expected status: `ok`
3. `seed_agent_task_status(session_id)`
   - expected status: `ok`

## Fallback low-level flow (`seedops_*`)

1. `workspace_attach_compose`
2. `workspace_refresh`
3. `ops_logs` + `routing_bgp_summary`
4. `capture_evidence`
5. `artifacts_list`

## Branch expectations

- `needs_input`: missing `attach_output_dir` or `suspicious_sender`
- `blocked`: policy rejects requested action
- `upstream_error|timeout`: SeedOps/SeedAgent service unavailable

