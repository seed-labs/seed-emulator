---
description: Generate normalized report files and include failure-code chain.
agent: seed-lab
---

Use skills:

1. `seed-lab-experiment-assistant`
2. `seed-lab-reporting`
3. `seed-lab-optimizer`

Mandatory behavior:

1. Run:
   - `scripts/seed_k8s_profile_runner.sh ${SEED_EXPERIMENT_PROFILE:-mini_internet} report`
2. Print absolute paths for report outputs.
3. Include `failure_code` and `minimal_retry_command` in summary.
