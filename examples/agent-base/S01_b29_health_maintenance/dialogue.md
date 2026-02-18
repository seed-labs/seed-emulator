# S01 Dialogue Template

## Canonical Path (`seed_agent_*`)

### User
Attach to `${B29_OUTPUT_DIR}` and run health patrol for B29 email network.

### Tool Call
- Tool: `seed_agent_run`
- Params:
  - `workspace_name=lab1`
  - `attach_output_dir=${B29_OUTPUT_DIR}`
  - `policy_profile=read_only`
  - `follow_job=true`

### Expected Status Branch
- Primary: `ok`
- Fallback branches: `needs_input | blocked | upstream_error | timeout | error`

### Expected Structured Output
- `status`
- `compiled_plan.playbook_yaml`
- `summary.workspace_id`
- `summary.job_id`
- `summary.job_status`

---

## Low-level Fallback (`seedops_*`)

### Tool Sequence
1. `workspace_list` / `workspace_create`
2. `workspace_attach_compose`
3. `playbook_validate`
4. `playbook_run`
5. `job_get` + `job_steps_list`
6. `artifacts_list` (+ `artifact_read_chunk` for downloads)

### Key Parameters
- `workspace_name=lab1`
- `output_dir=${B29_OUTPUT_DIR}`
- `playbook=playbook.fallback.yaml`

### Expected Status Branch
- Primary: `ok`
- Fallback branches: `needs_input | upstream_error | timeout | error`
