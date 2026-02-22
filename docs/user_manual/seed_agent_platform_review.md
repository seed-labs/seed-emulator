# SEED Platform Agent Review (MCP + Task Engine)

Last updated: 2026-02-18  
Scope: `seed-email-service` + `subrepos/seed-agent`

---

## 1. Executive Summary

This round moves the project from “single-shot demo scripting” to a reusable platform capability:

- `Codex` is an optional shell.
- `Seed-Agent` is the behavioral core.
- `SeedOps MCP` remains the runtime execution backbone.
- A reusable task engine is now added for multi-turn mission workflows.

The new loop is:

`User/Codex -> Seed-Agent MCP (task engine + orchestration) -> SeedOps MCP (execution) -> running SEED network`

This is now suitable for teaching, research, and project operations under one surface.

---

## 2. What Was Delivered

## 2.1 Seed-Agent (submodule) core upgrades

1. New mission APIs on Seed-Agent MCP:
   - `seed_agent_task_catalog`
   - `seed_agent_task_begin`
   - `seed_agent_task_reply`
   - `seed_agent_task_execute`
   - `seed_agent_task_status`

2. New task engine package:
   - `task_engine/models.py`
   - `task_engine/registry.py`
   - `task_engine/session_store.py` (SQLite persistence)
   - `task_engine/hitl.py`
   - `task_engine/orchestrator.py`
   - `task_engine/reporter.py`

3. Status semantics expanded:
   - Existing: `ok/needs_input/blocked/upstream_error/timeout/error`
   - Added: `awaiting_confirmation`

4. `seed-codex` shell upgraded:
   - `mission list/start/reply/execute/status`
   - submodule path auto-detection fixed
   - robust `context_json` parsing fixed
   - mission attach path normalized to absolute path

5. SDK wrapper upgraded:
   - `mcp_client/seedagent_api.py` now includes task APIs and accepts `awaiting_confirmation`.

## 2.2 seed-email-service platform assets

1. New reusable mission pack:
   - `examples/agent-missions/tasks/*.yaml` (6 tasks)
   - `examples/agent-missions/playbooks/*.yaml`
   - `examples/agent-missions/dialogues/*.md`
   - `examples/agent-missions/run_task_demo.sh`

2. New evidence-oriented docs:
   - `docs/user_manual/agent_missions_logbook.md`
   - this document `docs/user_manual/seed_agent_platform_review.md`

3. Existing `examples/agent-base` preserved as legacy showcase path.

---

## 3. Platform Positioning (Non-Toy Boundary)

This system is no longer framed as “a classroom-only script”.
It is a platform interface for all SEED runtime scenarios:

- Teaching: guided mission templates and deterministic evidence output.
- Research: controlled experiments with confirmation gates and rollback paths.
- Project operations: troubleshooting and maintenance missions over running labs.

The core abstraction is now **task package + state machine**, not a one-off prompt.

---

## 4. Runtime State Machine

Mission session lifecycle:

`BEGIN -> (needs_input)* -> (awaiting_confirmation)? -> executing -> done/error`

Deterministic HITL triggers:

1. Missing required mission inputs.
2. Elevated policy required (`net_ops` / `danger` stage).
3. Objective-risk conflict or policy conflict.

Confirmation token for risky missions:

- `YES_RUN_DYNAMIC_FAULTS`

---

## 5. API Surface (Current Canonical)

## 5.1 OPS orchestration APIs

- `seed_agent_run`
- `seed_agent_plan`
- `seed_agent_policy_check`
- `seed_agent_artifacts_download`

## 5.2 Mission APIs

- `seed_agent_task_catalog(track="all", baseline="all")`
- `seed_agent_task_begin(task_id, objective, workspace_name, attach_output_dir, attach_name_regex, context_json)`
- `seed_agent_task_reply(session_id, answers_json)`
- `seed_agent_task_execute(session_id, approval_token, follow_job, download_artifacts, artifacts_dir)`
- `seed_agent_task_status(session_id)`

Backward-compatible alias support remains one milestone for `seedagent_*`.

---

## 6. Mission Package Contract

Task files (`examples/agent-missions/tasks/*.yaml`) enforce:

- mission identity: `task_id/title/track/baseline`
- required inputs + validation hints
- stage flow + policy per stage
- canonical request template
- fallback playbook references
- acceptance checks + report template

V1 task set (6 missions):

- Security: 2
- Troubleshooting: 2
- Research: 2

---

## 7. Evidence Snapshot (Real Runs)

## 7.1 Automated quality checks

Executed:

- `pytest tests/test_seedagent_api_reframe.py tests/test_seedagent_tools.py tests/test_task_registry.py tests/test_task_hitl.py tests/test_task_state_machine.py tests/test_task_fallback.py -q`
- Result: `17 passed`

## 7.2 Real mission run A (read-only track)

- Task: `RS_B00_CONVERGENCE_COMPARISON`
- Session: `ba3f3c6a-b9f7-4bd2-8ba4-d5191322edd3`
- Execute status: `ok`
- Job: `af1c4743-000a-4381-a8eb-7d171ca345e8`
- Job status: `succeeded`

## 7.3 Real mission run B (risk gate + confirmation)

- Task: `RS_B29_FAULT_IMPACT_ABLATION`
- Session: `57709cf8-146b-4e65-aeb3-8e061bbd3ca9`
- Without approval: `awaiting_confirmation`
- With `YES_RUN_DYNAMIC_FAULTS`: execute `ok`
- Job: `13ced7eb-e011-40bb-84cc-a4b7e9823f21`
- Job status: `succeeded`

Evidence details are logged in:

- `docs/user_manual/agent_missions_logbook.md`

## 7.4 One-command review pack run

Executed:

- `examples/agent-missions/run_review_pack.sh --seed-token seed-local-token`

Latest pack:

- output dir: `examples/agent-missions/reports/20260218T155712Z`
- read-only session: `31324859-056f-4d2c-b3f3-92218683aa2e`
- read-only job: `fd069440-fd25-408e-a3bf-41b315f2bffb` (`succeeded`)
- risk session: `e3e64f4d-aff6-41c2-a122-324d93cf4110`
- risk job: `4b0705a5-7797-4035-b731-dbbb4f1c13f5` (`succeeded`)
- assertions: all true (`catalog_ok/read_only_ok/risk_gate_ok/risk_execute_ok`)

---

## 8. Known Gaps (Honest Boundary)

1. If LLM credentials are unavailable at runtime, planner falls back deterministically.
2. Current fallback planner is generic OPS-safe and not yet mission-specific for every advanced action pattern.
3. Successful job completion does not automatically guarantee meaningful experiment quality if the target runtime network is not truly up (must verify attach target and live containers).

These are engineering gaps, not conceptual blockers.

---

## 9. Recommended Demo Script for External Review

1. Start services:
   - `subrepos/seed-agent/scripts/seed-codex up`
2. Show catalog:
   - `subrepos/seed-agent/scripts/seed-codex mission list`
3. Show read-only mission success:
   - run `RS_B00_CONVERGENCE_COMPARISON`
4. Show risk gate behavior:
   - run `RS_B29_FAULT_IMPACT_ABLATION` once without token (expect `awaiting_confirmation`)
   - re-run with token (expect execution)
5. Stop services:
   - `subrepos/seed-agent/scripts/seed-codex down`

This flow demonstrates planning, HITL, policy gating, execution, and evidence output in one session.

One-command alternative:

- `examples/agent-missions/run_review_pack.sh`
- outputs: `examples/agent-missions/reports/<timestamp>/review_summary.json` and `review_report.md`

---

## 10. Next Milestone (M2 -> M3 focus)

1. Mission-specific fallback templates (reduce semantic drift when LLM unavailable).
2. Structured metrics extraction in `report_summary` for research comparability.
3. Attach/runtime health prechecks before mission execution.
4. Mission report exporter (`task_summary.json`, `task_report.md`, `decision_log.json`, `artifacts_index.json`) as first-class outputs.
