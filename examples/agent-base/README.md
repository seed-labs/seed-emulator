# Seed-Agent Dynamic Operations Showcase (`examples/agent-base`)

This package demonstrates **runtime operations only** on already-running SEED networks.
It is designed to highlight:

- **Codex as outer shell**
- **Seed-Agent as behavior core**
- **SeedOps as deterministic execution plane**

No static topology build/start is performed here.

---

## Scenario Matrix

| ID | Category | Baseline | Core Goal |
|---|---|---|---|
| `S01_b29_health_maintenance` | maintenance | B29 | Email-network health patrol (BGP + logs) |
| `S02_b00_path_maintenance` | maintenance | B00 | Route/path degradation diagnostics |
| `S03_b00_latency_experiment` | experiment | B00 | Controlled latency injection + rollback |
| `S04_b29_packetloss_experiment` | experiment | B29 | Controlled packet-loss experiment + rollback |

Each scenario supports:

- `--mode canonical` (`seed_agent_*` high-level path)
- `--mode fallback` (`seedops_*` deterministic low-level path)
- `--mode both` (default, with consistency check)

---

## Preconditions

1. SeedOps MCP server is up (default `http://127.0.0.1:8000/mcp`).
2. Seed-Agent MCP server is up (default `http://127.0.0.1:8100/mcp`).
3. Target networks are already running and attachable.
4. Environment variables are configured:

```bash
export SEED_AGENT_MCP_TOKEN='<seed-agent-token>'
export SEED_MCP_TOKEN='<seedops-token>'

# Optional endpoint overrides
export SEED_AGENT_MCP_URL='http://127.0.0.1:8100/mcp'
export SEEDOPS_MCP_URL='http://127.0.0.1:8000/mcp'

# Optional output dir overrides (relative paths supported)
export B29_OUTPUT_DIR='examples/internet/B29_email_dns/output'
export B00_OUTPUT_DIR='examples/internet/B00_mini_internet/output'
```

---

## Quick Run

Run all maintenance scenarios:

```bash
./examples/agent-base/run_all.sh --tier maintenance
```

Run all experiment scenarios with risk gate enabled:

```bash
./examples/agent-base/run_all.sh \
  --tier experiment \
  --risk on \
  --confirm-token YES_RUN_DYNAMIC_FAULTS
```

Run one scenario directly:

```bash
./examples/agent-base/S01_b29_health_maintenance/run.sh --mode both
```


## One-Command Real Showcase

For a full real local run (including temporary compose copy, subnet conflict auto-remap, MCP startup, and scenario execution):

```bash
./examples/agent-base/run_real_showcase.sh
```

`run_real_showcase.sh` automatically loads `./.env` (if present) and forwards LLM env vars to Seed-Agent:

- `LLM_MODEL`
- `LLM_API_KEY` / `OPENAI_API_KEY`
- `LLM_BASE_URL` / `OPENAI_API_BASE`
- `GEMINI_API_KEY` / `GOOGLE_API_KEY`

Useful options:

```bash
./examples/agent-base/run_real_showcase.sh \
  --work-dir /tmp/seed-agent-real-showcase \
  --s01-mode fallback \
  --s04-mode fallback
```

If your `seed-agent` is managed as a subrepo/submodule, this script auto-detects `./subrepos/seed-agent`.
You can still override explicitly:

```bash
export SEED_AGENT_DIR=./subrepos/seed-agent
```

Fast canonical showcase (real submission, non-blocking follow for B29):

```bash
./examples/agent-base/run_real_showcase.sh \
  --work-dir /tmp/seed-agent-real-showcase \
  --s01-mode canonical \
  --s04-mode canonical
```

## Logs → Docs (for demo handoff)

Run showcase and auto-generate a Markdown report from logs/artifacts:

```bash
./examples/agent-base/run_showcase_with_report.sh \
  --work-dir /tmp/seed-agent-real-showcase \
  --s01-mode canonical \
  --s04-mode canonical
```

Generated files:

- `real_showcase_summary.json`
- `showcase_report.md`

Outputs:

- summary: `<work-dir>/real_showcase_summary.json`
- logs: `<work-dir>/logs/`

The script uses relative repository paths and does not hardcode user-home absolute paths.

---

## Exit Codes

- `0`: success
- `2`: needs input
- `3`: blocked
- `4`: upstream error or timeout
- `5`: assertion failure / execution error

---

## Output Layout

Each run is stored under:

```text
examples/agent-base/<scenario>/artifacts/<scenario_id>/<timestamp>/
```

and `latest` points to the most recent run directory.

Typical outputs:

- canonical/fallback JSON responses
- job steps
- downloaded artifacts
- scenario summary / comparison markdown
