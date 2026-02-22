# S02 Dialogue Template

## Canonical Path (`seed_agent_*`)

### User
Attach to `${B00_OUTPUT_DIR}` and troubleshoot path degradation with BGP + routes + traceroute.

### Tool Calls
1. `seed_agent_plan`
2. `seed_agent_run`

### Key Parameters
- `workspace_name=lab1`
- `attach_output_dir=${B00_OUTPUT_DIR}`
- `policy_profile=read_only`

### Expected Status Branch
- Primary: `ok`
- Fallback branches: `needs_input | blocked | upstream_error | timeout | error`

---

## Low-level Fallback (`seedops_*`)

### Tool Sequence
1. `workspace_attach_compose`
2. `playbook_validate`
3. `playbook_run`
4. `job_get` + `job_steps_list`
5. `artifacts_list` + `artifact_read_chunk`

### Key Parameters
- `workspace_name=lab1`
- `output_dir=${B00_OUTPUT_DIR}`
- `playbook=playbook.fallback.yaml`

### Expected Status Branch
- Primary: `ok`
- Fallback branches: `needs_input | upstream_error | timeout | error`
