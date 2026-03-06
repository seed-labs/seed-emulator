---
description: Collect runtime observation snapshot and give a single next command.
agent: seed-lab
---

Use skills:

1. `seed-lab-experiment-assistant`
2. `seed-lab-reporting`
3. `seed-lab-optimizer`

Mandatory behavior:

1. Run:
   - `scripts/seed_k8s_profile_runner.sh ${SEED_EXPERIMENT_PROFILE:-mini_internet} observe`
2. Summarize key observe artifacts and output one next command from `next_actions.json`.
