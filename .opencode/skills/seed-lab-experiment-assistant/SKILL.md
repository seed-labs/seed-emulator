---
name: seed-lab-experiment-assistant
description: Orchestrate layered seed-lab skills for deterministic SEED k3s experiments with proactive next-action guidance.
---

## When to use

Use for end-to-end SEED experiments on k3s/kvm where the goal is runnable, verifiable, diagnosable, and proactively guided.

## Skill loading order

1. `seed-lab-core`
2. `seed-lab-preflight`
3. `seed-lab-execution`
4. `seed-lab-verification`
5. `seed-lab-triage` (when failed)
6. `seed-lab-reporting`
7. `seed-lab-optimizer`

## Canonical stage order

0. bootstrap
1. preflight
2. compile
3. build
4. deploy
5. verify
6. observe
7. summary

## Intent modes

1. `execution` mode
- Default.
- Run stage actions and produce artifacts.
- If user intent is broad/ambiguous (no explicit stage/action), run bootstrap first:
  - `scripts/seed_lab_entry_status.sh`
  - then recommend exactly one next command.
- Do not require slash commands: if the user asks in natural language (e.g. “现在跑咋样/卡哪了/下一步是什么”), read artifacts and answer directly with evidence + one next action.

2. `explain_only` mode
- Trigger when user says they only want explanation/playbook and explicitly asks not to run commands.
- Do not execute shell commands in this mode.
- Output fixed structure:
  - `目标`
  - `命令`
  - `成功判据`
  - `与 docker-compose 对应关系` (for migration users)

## Command mapping

- `/seed-lab-home`: bootstrap status and task navigation
- `/seed-lab-start`: preflight -> compile -> build -> deploy
- `/seed-lab-verify`: verify existing deployment
- `/seed-lab-observe`: collect runtime snapshot
- `/seed-lab-all`: full run + observe + report
- `/seed-lab-doctor`: proactive risk check without deployment
- `/seed-lab-next`: print single next command from artifacts
- `/seed-lab-triage`: diagnose failure from artifacts
- `/seed-lab-report`: generate normalized report from artifacts

## Hard acceptance checks

Verification is successful only when all are true:

- placement gate passed:
  - if `placement_mode == strict3`: `strict3_passed == true`
  - else: `placement_passed == true`
- `bgp_passed`
- `connectivity_passed`
- `recovery_passed`

## Failure behavior

On first hard failure, stop and return:

1. `failed_stage`
2. `failure_code`
3. `first_evidence_file`
4. `minimal_retry_command`
5. `fallback_command`

## Environment reminders (always)

Whenever command suggestions are shown, include current values (or defaults) of:

- `KUBECONFIG`
- `SEED_EXPERIMENT_PROFILE`
- `SEED_NAMESPACE`
- `SEED_CNI_TYPE`
