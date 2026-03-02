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

### 1) Start a real target lab

```bash
docker-compose -f mcp-server/output_e2e_demo/docker-compose.yml up -d
```

### 2) Start the dual MCP stack (SeedOps + SeedAgent)

```bash
export SEED_REPO_ROOT=/path/to/your/seed-repo

export SEED_MCP_TOKEN=your-seedops-token
export SEED_AGENT_MCP_TOKEN=your-seedagent-token

# LLM vars: both naming styles are supported by seed-agent.
export LLM_BASE_URL=https://your-openai-compatible-endpoint/v1
export LLM_API_KEY=your-llm-key
export LLM_MODEL=gpt-5.2

"${SEED_REPO_ROOT}/subrepos/seed-agent/scripts/seed-codex" up
"${SEED_REPO_ROOT}/subrepos/seed-agent/scripts/seed-codex" status
```

### 3) Run maintenance checks (natural language, real runtime)

```bash
cd "${SEED_REPO_ROOT}/subrepos/seed-agent"
export SEED_MCP_CLIENT_MODE=http
export SEED_MCP_URL=http://127.0.0.1:8000/mcp
export SEED_MCP_TOKEN=your-seedops-token
python main.py "Attach to ${SEED_REPO_ROOT}/mcp-server/output_e2e_demo and refresh inventory, then summarize BGP health"
```

### 4) Run controlled experiment tasks with confirmation gate

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

### 5) Stop services

```bash
"${SEED_REPO_ROOT}/subrepos/seed-agent/scripts/seed-codex" down
```

### 6) If first startup fails due old Docker residues

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
- Example catalogs:
  - `examples/basic/README.md`
  - `examples/internet/README.md`
  - `examples/blockchain/README.md`
  - `examples/scion/README.md`
  - `examples/agent-missions/README.md` (task-engine runtime operations)
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

- `subrepos/seed-agent/scripts/seed-codex up`
- `subrepos/seed-agent/scripts/seed-codex ui`

---

## Contributing

See `CONTRIBUTING.md`.

## License

GNU GPL v3.0, see `LICENSE.txt`.
