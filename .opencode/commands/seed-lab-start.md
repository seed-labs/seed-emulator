---
description: Start SEED run from preflight to deployment readiness with proactive next actions.
agent: seed-lab
---

Use skills:

1. `seed-lab-experiment-assistant`
2. `seed-lab-optimizer`

Mandatory behavior:

1. Resolve profile from `SEED_EXPERIMENT_PROFILE` (default `mini_internet`).
2. Run:
   - `scripts/seed_k8s_profile_runner.sh ${SEED_EXPERIMENT_PROFILE:-mini_internet} start`
3. Then read and prioritize:
   - `output/profile_runs/${SEED_EXPERIMENT_PROFILE:-mini_internet}/latest/next_actions.json`
4. Output stage PASS/FAIL and one next command.
5. On failure return strict 5-tuple.
