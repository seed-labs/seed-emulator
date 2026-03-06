---
description: Execute full run (start->verify->observe->report) with proactive diagnostics.
agent: seed-lab
---

Use skills:

1. `seed-lab-experiment-assistant`
2. `seed-lab-optimizer`

Mandatory behavior:

1. Run:
   - `scripts/seed_k8s_profile_runner.sh ${SEED_EXPERIMENT_PROFILE:-mini_internet} all`
2. Report:
   - latest runner summary path
   - report.json/report.md path
   - one next command
3. On failure return strict 5-tuple.
