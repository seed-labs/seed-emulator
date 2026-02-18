# Seed-Agent Showcase Logbook Workflow

This document defines a reproducible showcase workflow with auditable outputs:

- real run on started network
- log capture
- machine-readable summary
- markdown report for demo/PR handoff

## Recommended Layout (Seed-Agent as subrepo)

Use a repo-local path instead of user-home absolute paths:

```bash
seed-email-service/
└── subrepos/
    └── seed-agent/
```

Initialize submodule:

```bash
git submodule update --init --recursive
```

Optional override:

```bash
export SEED_AGENT_DIR=./subrepos/seed-agent
```

`run_real_showcase.sh` defaults to `./subrepos/seed-agent`.

## LLM Environment

`examples/agent-base/run_real_showcase.sh` loads `./.env` automatically (if present) and forwards:

- `LLM_MODEL`
- `LLM_API_KEY` / `OPENAI_API_KEY`
- `LLM_BASE_URL` / `OPENAI_API_BASE`
- `GEMINI_API_KEY` / `GOOGLE_API_KEY`

This enables LLM-first planning when keys are valid.

## One-command run + report

```bash
./examples/agent-base/run_showcase_with_report.sh \
  --work-dir /tmp/seed-agent-real-showcase \
  --s01-mode canonical \
  --s04-mode canonical
```

Outputs:

- `/tmp/seed-agent-real-showcase/real_showcase_summary.json`
- `/tmp/seed-agent-real-showcase/showcase_report.md`
- `/tmp/seed-agent-real-showcase/logs/`

## Report content

`showcase_report.md` includes:

- exit codes per scenario
- status/job snapshot
- artifact paths
- tail logs for `s01/s02/s03/s04` and `seedagent/seedops`
