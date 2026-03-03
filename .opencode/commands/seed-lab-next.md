---
description: Print exactly one next command from latest next_actions.json.
agent: seed-lab
---

Use skills:

1. `seed-lab-experiment-assistant`
2. `seed-lab-optimizer`

Mandatory behavior:

1. Read latest `next_actions.json` in this priority:
   - `output/profile_runs/${SEED_EXPERIMENT_PROFILE:-mini_internet}/latest/next_actions.json`
   - `output/multinode_mini_validation/latest/next_actions.json`
2. Output only:
   - `minimal_retry_command` if present
   - else `fallback_command`
