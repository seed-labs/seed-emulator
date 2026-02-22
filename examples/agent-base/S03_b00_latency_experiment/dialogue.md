# S03 Dialogue Template

## Canonical Path (`seed_agent_*`)

### User
Run baseline checks on `${B00_OUTPUT_DIR}`, then perform controlled latency injection and rollback.

### Tool Calls
1. `seed_agent_run` (baseline, `policy_profile=read_only`)
2. `seed_agent_policy_check` (injection command precheck, `policy_profile=net_ops`)
3. `seed_agent_run` (experiment, `policy_profile=net_ops`)
4. `seed_agent_run` (rollback, `policy_profile=net_ops`)

### Expected Status Branch
- With gate enabled: `ok`
- Without gate/token: `blocked` (experiment stage must not run)
- Error branches: `needs_input | upstream_error | timeout | error`

---

## Low-level Fallback (`seedops_*`)

### Tool Sequence
1. Baseline read-only playbook (`workspace_refresh`, `routing_bgp_summary`, `traceroute`)
2. Experiment playbook (`inject_fault latency` + evidence collection)
3. Rollback playbook (`inject_fault reset` + post-check)

### Key Parameters
- `workspace_name=lab1`
- `output_dir=${B00_OUTPUT_DIR}`
- experiment requires `--risk on --confirm-token YES_RUN_DYNAMIC_FAULTS`

### Expected Status Branch
- With gate enabled: `ok`
- Without gate/token: `blocked`
