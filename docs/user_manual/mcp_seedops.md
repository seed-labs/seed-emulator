# MCP Ops Control Plane (SeedOps)

SeedOps turns the `mcp-server` into an **operational control plane** for **already-running** SEED Emulator Docker/Compose networks.

It is designed for:

- Attaching to an existing `docker compose up -d` output (no rebuild needed)
- Building a runtime **inventory** from SEED container labels
- Selecting nodes via **selectors**
- Running **batch operations** (`exec`, `logs`, `BGP` summary)
- Running deterministic **YAML playbooks** as **async jobs** (with artifacts + snapshots)

This guide covers both Phase 1 (workspace/inventory/ops) and Phase 2 (jobs/playbooks/collector).

---

## Security model (HTTP)

- Transport: **MCP Streamable-HTTP**
- Auth: **Bearer Token** (static shared secret)
- No OAuth flow (Phase 1/2)
- `server.py` (stdio) remains local/no-auth for backwards compatibility
- `serve_http.py` enforces `SEED_MCP_TOKEN`

---

## Run the MCP HTTP server

From the repo root:

```bash
cd mcp-server
python3 -m pip install -r requirements.txt

export SEED_MCP_TOKEN='change-me'
export FASTMCP_HOST=0.0.0.0
export FASTMCP_PORT=8000
export FASTMCP_STREAMABLE_HTTP_PATH=/mcp
export SEED_MCP_PUBLIC_URL=http://127.0.0.1:8000

python3 serve_http.py
```

If you run with `FASTMCP_HOST=0.0.0.0` and clients connect remotely, set a reachable `SEED_MCP_PUBLIC_URL`.

### DNS rebinding protection (important for remote clients)

The server enables Host/Origin allowlists by default. If clients get `421 Invalid Host` or `403 Invalid Origin`:

- Ensure `SEED_MCP_PUBLIC_URL` matches what clients use
- Or explicitly extend allowlists:

```bash
export SEED_MCP_ALLOWED_HOSTS='seed-mcp.example.com:*,10.0.0.5:*'
export SEED_MCP_ALLOWED_ORIGINS='http://seed-mcp.example.com:*,http://10.0.0.5:*'
```

You can disable this protection (not recommended on untrusted networks):

```bash
export SEED_MCP_DNS_REBINDING_PROTECTION=0
```

---

## Data locations

By default, SeedOps stores state under `mcp-server/.seedops/`:

- DB: `mcp-server/.seedops/seedops.db` (override with `SEEDOPS_DB_PATH`)
- Workspace data/artifacts: `mcp-server/.seedops/workspaces/` (override with `SEEDOPS_DATA_DIR`)

---

## Phase 1: Workspaces + Inventory

### 1) Create a workspace

Tool: `workspace_create(name)`

### 2) Attach to an already-running network

Attach by Compose output directory (recommended):

- Tool: `workspace_attach_compose(workspace_id, output_dir)`
- It reads `output_dir/docker-compose.yml` and records `services.*.container_name`

Or attach by label scan:

- Tool: `workspace_attach_labels(workspace_id, name_regex, label_prefix=...)`
- Safer than scanning all containers because it filters by name + label prefix

### 3) Refresh inventory

Tool: `workspace_refresh(workspace_id)`

### 4) List nodes (selector)

Tool: `inventory_list_nodes(workspace_id, selector={})`

Selector semantics:

- AND across provided keys
- OR inside list values
- `labels` is AND across k/v
- **Empty list matches nothing** (safer than matching everything)

Common keys:

- `asn`, `role`, `node_name`, `class`, `network`, `container_name`, `labels`

---

## Phase 1: Ops (batch)

### Batch exec

Tool: `ops_exec(workspace_id, selector, command, timeout_seconds=30, parallelism=20, max_output_chars=8000)`

Exec backend:

- `SEEDOPS_EXEC_BACKEND=auto` (default)
- `cli` uses host-side timeout/output limits via `docker exec`
- `sdk` uses Docker SDK (may be less robust for timeouts)

Recommended for large scenarios:

```bash
export SEEDOPS_EXEC_BACKEND=cli
```

### Batch logs

Tool: `ops_logs(workspace_id, selector, tail=200, since_seconds=0, ...)`

### BGP summary (BIRD)

Tool: `routing_bgp_summary(workspace_id, selector)`

It runs `birdc show protocols` inside selected containers and aggregates BGP status.

---

## Phase 2: Jobs + YAML playbooks

Playbooks run **asynchronously** and produce:

- `job_steps` (progress + step events)
- artifacts (optional JSON outputs saved to disk)

### Validate a playbook

Tool: `playbook_validate(playbook_yaml)`

### Run a playbook

Tool: `playbook_run(workspace_id, playbook_yaml)` → returns `job_id`

Then poll:

- `job_get(job_id)`
- `job_steps_list(job_id, since_step_id=0, limit=200)`
- `artifacts_list(job_id)` then:
  - `artifact_read(artifact_id)` (small text)
  - `artifact_read_chunk(artifact_id, offset=0, max_bytes=65536)` (large/binary, remote-friendly)

Cancel a running job:

- `job_cancel(job_id)`

### Artifacts (remote-friendly)

Artifact `path` values are **server-local filesystem paths**. Remote clients should use `artifact_read` or `artifact_read_chunk`.

To download an artifact in chunks:

1. Call `artifacts_list(job_id)` to find `artifact_id`
2. Repeatedly call `artifact_read_chunk(artifact_id, offset, max_bytes)` until `eof=true`
3. Base64-decode `content_b64` and append bytes locally

### Playbook YAML schema (v1)

Supported actions:

- `workspace_refresh`
- `inventory_list_nodes`
- `ops_exec`
- `ops_logs`
- `routing_bgp_summary`
- `sleep`

Example:

```yaml
version: 1
name: bgp_check
defaults:
  selector:
    role: ["BorderRouter", "Router"]
  timeout_seconds: 20
  parallelism: 30
  max_output_chars: 6000

steps:
  - action: workspace_refresh
    id: refresh
    save_as: refresh

  - action: routing_bgp_summary
    id: bgp
    # selector can be omitted to use defaults.selector
    save_as: bgp_summary

  - action: ops_exec
    id: routes
    selector: { asn: [150, 151] }
    command: "ip route"
    save_as: routes_as150_151

  - action: sleep
    seconds: 2
```

Notes:

- For `ops_exec/ops_logs/routing_bgp_summary/inventory_list_nodes`, selector is taken from `step.selector` or `defaults.selector`.
- To select everything, explicitly pass `{}` (do not use `[]`).

---

## Phase 2: Collector + snapshots

Start a periodic collector job:

- Tool: `collector_start(workspace_id, interval_seconds=30, selector={}, include_bgp_summary=true)`

Stop it:

- Tool: `job_cancel(job_id)`

List snapshots:

- Tool: `snapshots_list(workspace_id, snapshot_type="", since_ts=0, limit=200)`

Snapshot types (current):

- `inventory_summary`
- `bgp_summary_counts`
