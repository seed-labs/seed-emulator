---
description: Verify current SEED run and output proactive retry guidance if failed.
agent: seed-lab
---

Use skills:

1. `seed-lab-experiment-assistant`
2. `seed-lab-verification`
3. `seed-lab-optimizer`

Mandatory behavior:

1. Run:
   - `/home/zzw4257/seed-k8s/scripts/seed_k8s_profile_runner.sh ${SEED_EXPERIMENT_PROFILE:-mini_internet} verify`
2. Read `next_actions.json` and prefer its `minimal_retry_command`.
3. On failure return strict 5-tuple.
