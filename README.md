# SEED Emulator (`mcp-server` branch)

This repository is the core SEED Emulator codebase for the `mcp-server` branch. It provides:

- programmable Internet emulation (AS/IX/BGP/DNS/services)
- compiler outputs to Docker/Compose runtimes
- a modern MCP operations control plane (`SeedOps`) for running labs

This repo now supports two complementary workflows:

1. **BUILD path**: define topology -> compile -> run containers
2. **OPS path**: attach to running output -> observe/operate via MCP tools

![The Web UI](./docs/assets/web-ui.png)

---

## Interactive Operations Baseline

The current agent closure baseline is attached-runtime operation on already-running SEED outputs.
The canonical loop is:

`attach -> inspect -> decide -> operate -> verify -> summarize`

This baseline is evaluated across six scenario classes:

1. Diagnosis / Maintenance
2. Disturbance Recovery
3. Routing Security
4. Service Reachability
5. Security Offense-Defense
6. Research Experiments

Operational constraint:

- generated labs often reuse fixed `container_name` values
- different `output/` directories should be treated as mutually conflicting runtime assets unless isolated sequentially
- the baseline tooling now assumes sequential runtime preparation for multi-scenario review

The public entrypoint for this workflow is the repo-root launcher:

```bash
scripts/seed-codex up
scripts/seed-codex ui
```

Subrepo-local launchers remain supported for implementation work, but root commands are the documented default.

When you need the real active prompt / MCP / skill surface, see:

- `scripts/seed-codex inspect`
- [`docs/user_manual/seed_codex_active_stack.md`](./docs/user_manual/seed_codex_active_stack.md)

The current truthful answer to “why is `seed-codex` unique?” is:

- dedicated project `CODEX_HOME`
- project-generated `developer_instructions`
- project MCP tool whitelist
- project Codex skills synced into that `CODEX_HOME`
- no project-local plugin yet

---

## Quick Start (BUILD path)

### Prerequisites

- `python3`
- `docker`
- `docker-compose` (or compose plugin)

### Environment

```bash
source development.env
```

For persistent usage, add repo root to `PYTHONPATH` in your shell profile.

### Run a minimal example

```bash
cd examples/basic/A00_simple_as
python3 simple_as.py
cd output
docker-compose build && docker-compose up
```

After startup, routers need time to converge.

---

## Quick Start (OPS path / SeedOps MCP)

Start SeedOps MCP server:

```bash
cd mcp-server
export SEED_MCP_TOKEN=your-bearer-token
export FASTMCP_HOST=127.0.0.1 FASTMCP_PORT=8000 FASTMCP_STREAMABLE_HTTP_PATH=/mcp
python serve_http.py
```

Then use a client (for example `seed-agent`) to call SeedOps tools:

- workspace attach (`workspace_attach_compose` / `workspace_attach_labels`)
- inventory + selectors (`inventory_list_nodes`)
- batch ops (`ops_exec`, `ops_logs`, `routing_bgp_summary`)
- async jobs/artifacts (`playbook_run`, `job_get`, `artifacts_list`)

SeedOps manual:

- `docs/user_manual/mcp_seedops.md`

---

## Practical Runtime Usage (recommended)

Use this when you want to operate and maintain real running labs (not build-only).

Tested attached-runtime baseline on `2026-04-02`:

- live network: `examples/internet/B29_email_dns/output`
- stable interactive entry: `scripts/seed-codex ui`
- stable task entry: `scripts/seed-codex mission ...`
- current high-level `run` path still frequently falls back to `template_fallback`
- generated labs should be started one at a time; `B00` and `B29` conflict if launched together on the same Docker host

### 1) Start a real target lab

```bash
docker-compose -f examples/internet/B29_email_dns/output/docker-compose.yml up -d
```

Notes:

- this host uses `docker-compose` v1, not `docker compose`
- `B00_mini_internet/output` and `B29_email_dns/output` overlap in Docker network ranges, so do not keep them up at the same time

### 2) Start the dual MCP stack (SeedOps + SeedAgent)

```bash
export SEED_REPO_ROOT=/path/to/your/seed-repo

# Optional for local use. If unset, scripts/seed-codex defaults both to seed-local-token.
export SEED_MCP_TOKEN=your-seedops-token
export SEED_AGENT_MCP_TOKEN=your-seedagent-token

# LLM vars: both naming styles are supported by seed-agent.
export LLM_BASE_URL=https://your-openai-compatible-endpoint/v1
export LLM_API_KEY=your-llm-key
export LLM_MODEL=gpt-5.2

cd "${SEED_REPO_ROOT}"
scripts/seed-codex up
scripts/seed-codex status
```

### 3) Run interactive maintenance checks (natural language, real runtime)

This is the primary operations mode.

```bash
cd "${SEED_REPO_ROOT}"
scripts/seed-codex ui
```

Important:

- `scripts/seed-codex ui` itself does not define model flags.
- It forwards all extra arguments directly to the underlying `codex` binary.
- In practice, pass model/config flags exactly as native Codex CLI arguments.

Recommended interactive launch for this repo:

```bash
cd "${SEED_REPO_ROOT}"
scripts/seed-codex ui -m gpt-5.4 -c 'model_reasoning_effort="low"'
```

Useful interactive variants:

```bash
# Override model only
scripts/seed-codex ui -m gpt-5.4

# Override reasoning effort only
scripts/seed-codex ui -c 'model_reasoning_effort="low"'

# Start in repo root explicitly and keep the project profile
scripts/seed-codex ui -C /home/parallels/seed-email-service -m gpt-5.4 -c 'model_reasoning_effort="low"'
```

Inside Codex, describe the live objective directly, for example:

- `Attach to mcp-server/output_e2e_demo, refresh inventory, check BGP neighbors and critical services, repair anomalies, and leave evidence.`
- `Attach to examples/internet/B29_email_dns/output, diagnose end-to-end mail reachability, and verify recovery if action is needed.`

Recommended live prompt for the B29 showcase:

- `Attach to examples/internet/B29_email_dns/output, summarize the running environment, identify the key mail and DNS nodes, explain the operational scope, and ask only for the missing inputs needed to debug a concrete mail reachability issue.`

### 4) Run non-interactive regression or mission flows

These commands are the automation path for repeatability and CI-style verification.

```bash
cd "${SEED_REPO_ROOT}"
scripts/seed-codex plan "Attach to mcp-server/output_e2e_demo and summarize BGP health"
scripts/seed-codex run "Attach to mcp-server/output_e2e_demo and refresh inventory, then collect health evidence"
```

Useful non-interactive verification commands before a live interactive demo:

```bash
# Verify runtime awareness through the same Codex shell/provider chain
scripts/seed-codex probe-context \
  --attach-output-dir examples/internet/B29_email_dns/output \
  --workspace-name pre_demo_probe \
  --model gpt-5.4 \
  --reasoning-effort low

# Verify task discovery + task-begin behavior with the model in the loop
scripts/seed-codex exec \
  --model gpt-5.4 \
  --reasoning-effort low \
  "Use MCP tools only. Call seed_agent_task_catalog for B29, then begin the B29 mail reachability task and return the missing inputs."
```

Practical rule:

- use `ui` for the actual showcase
- use `probe-context` / `exec` before the showcase to prove the chain is healthy
- do not use `run` as the main stage unless you explicitly want the high-level one-shot path

Observed behavior from the tested B29 run:

- `scripts/seed-codex run ...` reliably attached to the live network and returned structured environment summaries
- the same run often reported `planner_mode: template_fallback`
- this is acceptable for attach/inventory demos, but weak for a “model planned everything” story

### 5) Run controlled experiment tasks with confirmation gate

```bash
cd "${SEED_REPO_ROOT}"
export SEED_AGENT_MCP_URL=http://127.0.0.1:8100/mcp
export SEED_AGENT_MCP_TOKEN=your-seedagent-token

examples/agent-missions/run_task_demo.sh \
  --task RS_B29_FAULT_IMPACT_ABLATION \
  --objective "Run controlled packet loss ablation with rollback" \
  --attach-output-dir examples/internet/B29_email_dns/output \
  --risk on \
  --confirm-token YES_RUN_DYNAMIC_FAULTS
```

### 5.1) Recommended task-style demo path

For a cleaner operations demo, prefer the task interface over free-form one-shot `run`.

List available B29 tasks:

```bash
scripts/seed-codex mission list --baseline B29
```

Start a concrete troubleshooting task:

```bash
scripts/seed-codex mission start \
  --task TS_B29_MAIL_REACHABILITY_DEBUG \
  --objective "排查 as200/host_0 到 as202/dns-auth-gmail 的可达性并给出证据" \
  --workspace-name demo-rs-b29-live \
  --attach-output-dir examples/internet/B29_email_dns/output \
  --context-json '{"source_node":"as200/host_0","destination_node":"as202/dns-auth-gmail"}'
```

Execute after the confirmation gate:

```bash
scripts/seed-codex mission execute \
  --session <session_id> \
  --approve YES_RUN_DYNAMIC_FAULTS \
  --follow-job on \
  --download-artifacts on \
  --artifacts-dir /tmp/seed-mission-b29-debug
```

What the tested B29 mission produced:

- attach succeeded on a live `76`-node runtime
- confirmation gate worked before execution
- execution completed with `6` downloaded artifacts
- evidence included endpoint logs, endpoint probe output, and BGP route context

### 5.2) Run the six-class review pack

Use explicit per-service tokens when SeedOps and SeedAgent do not share auth:

```bash
cd "${SEED_REPO_ROOT}"
examples/agent-missions/run_review_pack.sh \
  --seedops-token "${SEED_MCP_TOKEN}" \
  --seedagent-token "${SEED_AGENT_MCP_TOKEN}"
```

### 6) Stop services

```bash
cd "${SEED_REPO_ROOT}"
scripts/seed-codex down
```

### 7) If first startup fails due old Docker residues

If you see `invalid pool request: Pool overlaps`, remove only overlapping SEED networks:

```bash
docker network rm \
  b29_output_net_151_net0 \
  b29_output_net_152_net0 \
  output_e2e_demo_net_150_net0 \
  red_blue_demo_net_100_link_web100_r100
```

If you see `container name ... is already in use`, remove conflicting old containers, then retry `docker-compose up -d`.

---

## Repository map

```text
seed-repo/
├── examples/                 # Topology and scenario examples
├── mcp-server/               # SeedOps MCP server implementation
├── docs/user_manual/         # User manuals and feature guides
├── library/, seedemu/        # Emulator core packages
├── docker_images/            # Container image build assets
└── client/                   # Visualization/client components
```

---

## Documentation entrypoints

- Main user manual index: `docs/user_manual/README.md`
- Build flow overview: `docs/user_manual/overall_flow.md`
- SeedOps MCP operations: `docs/user_manual/mcp_seedops.md`
- Attached-runtime capability audit: `docs/user_manual/attached_runtime_capability_audit.md`
- Proposal materials: `docs/proposal/README.md`
- Showcase pack: `showcase/README.md`
- Example catalogs:
  - `examples/basic/README.md`
  - `examples/internet/README.md`
  - `examples/blockchain/README.md`
  - `examples/scion/README.md`
  - `examples/agent-specific/README.md` (curated agent-first attached-runtime bundles)
  - `examples/agent-missions/README.md` (six-class runtime operations baseline)
  - `docs/user_manual/agent_missions_logbook.md` (runtime evidence snapshots)
  - `docs/user_manual/seed_agent_platform_review.md` (full platform retrospective)

---

## Notes for constrained network environments

If Docker Hub access is unstable:

- configure proxy: `docs/user_manual/dockerhub_proxy.md`
- or build local images: `docker_images/README.md`

---

## Related repository

High-level agent and Codex integration live in:

- `subrepos/seed-agent/README.md`

Recommended closed-loop launcher from `seed-agent`:

- `scripts/seed-codex up`
- `scripts/seed-codex ui`

---

## Contributing

See `CONTRIBUTING.md`.

## License

GNU GPL v3.0, see `LICENSE.txt`.
