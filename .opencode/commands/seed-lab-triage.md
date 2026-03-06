---
description: Diagnose latest failed run and return strict 5-tuple.
agent: seed-lab
---

Use skills:

1. `seed-lab-experiment-assistant`
2. `seed-lab-triage`
3. `seed-lab-optimizer`

Mandatory behavior:

1. Run:
   - `scripts/seed_k8s_profile_runner.sh ${SEED_EXPERIMENT_PROFILE:-mini_internet} triage`
2. Prefer diagnostics from `next_actions.json` and `diagnostics.json`.
3. Return strict 5-tuple.
