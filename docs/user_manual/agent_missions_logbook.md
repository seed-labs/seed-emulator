# Seed-Agent Mission Logbook (Runtime Evidence)

This logbook captures reproducible runtime evidence for the mission task-engine flow.

---

## Environment

- Repository: `seed-email-service` + submodule `subrepos/seed-agent`
- Date: `2026-02-18`
- Servers started by:
  - `subrepos/seed-agent/scripts/seed-codex up`
- Auth (local demo): `SEED_MCP_TOKEN=seed-local-token`, `SEED_AGENT_MCP_TOKEN=seed-local-token`

---

## Scenario

- Mission: `RS_B00_CONVERGENCE_COMPARISON`
- Objective: `Compare convergence`
- Attach target: `examples/internet/B00_mini_internet/output`
- Entry script: `examples/agent-missions/run_task_demo.sh`

Command:

```bash
SEED_AGENT_MCP_URL=http://127.0.0.1:8100/mcp \
SEED_AGENT_MCP_TOKEN=seed-local-token \
examples/agent-missions/run_task_demo.sh \
  --task RS_B00_CONVERGENCE_COMPARISON \
  --objective "Compare convergence" \
  --attach-output-dir examples/internet/B00_mini_internet/output \
  --context-json '{"comparison_target":"AS2-AS3"}' \
  --work-dir /tmp/seed-agent-mission-demo-real
```

---

## Observed Result

- Exit code: `0`
- Session: `ba3f3c6a-b9f7-4bd2-8ba4-d5191322edd3`
- Begin status: `ok`
- Execute status: `ok`
- Final task status: `ok`
- Job id: `af1c4743-000a-4381-a8eb-7d171ca345e8`
- Job status: `succeeded`
- Planner mode observed: `template_fallback` (LLM unavailable in this run)

Generated summary payload:

```json
{
  "run_dir": "/tmp/seed-agent-mission-demo-real/RS_B00_CONVERGENCE_COMPARISON/20260218T124800Z",
  "session_id": "ba3f3c6a-b9f7-4bd2-8ba4-d5191322edd3",
  "begin_status": "ok",
  "reply_status": null,
  "execute_status": "ok",
  "task_status": "ok",
  "job_id": "af1c4743-000a-4381-a8eb-7d171ca345e8",
  "job_status": "succeeded"
}
```

---

## Notes

- This evidence proves the task-engine state flow:
  `task_begin -> task_execute -> task_status`.
- In this run, LLM credentials were not active for the server process, so execution used deterministic fallback and still completed successfully.
- To force full LLM-primary execution, export valid `OPENAI_API_KEY`/provider credentials before `seed-codex up`.

---

## Risk-Gate Evidence

Mission:

- `RS_B29_FAULT_IMPACT_ABLATION`

Observed behavior (without approval token):

- `seed_agent_task_execute` returned `status=awaiting_confirmation`
- response included:
  - `required_approval_token=YES_RUN_DYNAMIC_FAULTS`
  - `policy_profile=net_ops`
  - risk summary explaining stage-level elevated policy

This confirms HITL confirmation-gate behavior is active for risky stages.

---

## Batch Evidence Packaging

For repeatable review exports, run:

```bash
examples/agent-missions/run_review_pack.sh
```

It generates a timestamped bundle under:

- `examples/agent-missions/reports/<timestamp>/review_summary.json`
- `examples/agent-missions/reports/<timestamp>/review_report.md`

Latest validated bundle:

- `examples/agent-missions/reports/20260218T155712Z/review_summary.json`
- `examples/agent-missions/reports/20260218T155712Z/review_report.md`
