# S04 Dialogue Template

## Canonical Path (`seed_agent_*`)

### User
On `${B29_OUTPUT_DIR}`, run baseline mail diagnostics, inject controlled packet loss, then rollback and compare logs.

### Tool Calls
1. `seed_agent_run` (baseline, `policy_profile=read_only`)
2. `seed_agent_policy_check` (packet-loss command, `policy_profile=net_ops`)
3. `seed_agent_run` (experiment, `policy_profile=net_ops`)
4. `seed_agent_run` (rollback, `policy_profile=net_ops`)

### Expected Status Branch
- With gate enabled: `ok`
- Without gate/token: `blocked` for experiment stage
- Error branches: `needs_input | upstream_error | timeout | error`

---

## Low-level Fallback (`seedops_*`)

### Tool Sequence
1. Baseline logs playbook (`mail_logs_before`)
2. Experiment playbook (`inject_fault packet_loss` + `mail_logs_during`)
3. Rollback playbook (`inject_fault reset` + `mail_logs_after`)

### Key Parameters
- `workspace_name=lab1`
- `output_dir=${B29_OUTPUT_DIR}`
- experiment requires `--risk on --confirm-token YES_RUN_DYNAMIC_FAULTS`

### Expected Status Branch
- With gate enabled: `ok`
- Without gate/token: `blocked`
