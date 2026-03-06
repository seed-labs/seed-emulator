---
description: Proactive risk assessment without deployment.
agent: seed-lab
---

Use skills:

1. `seed-lab-experiment-assistant`
2. `seed-lab-preflight`
3. `seed-lab-optimizer`

Mandatory behavior:

1. Run:
   - `scripts/seed_k8s_profile_runner.sh ${SEED_EXPERIMENT_PROFILE:-mini_internet} doctor`
2. Output one risk summary and one next command.
3. If failed, return strict 5-tuple.
