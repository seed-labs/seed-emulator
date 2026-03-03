---
description: Show practical kubectl usage for current SEED namespace and optionally run non-destructive status queries.
agent: seed-lab
---

Use skills:

1. `seed-lab-experiment-assistant`
2. `seed-lab-optimizer`

Mandatory behavior:

1. Run:
   - `/home/zzw4257/seed-k8s/scripts/seed_lab_entry_status.sh`
2. Read:
   - `/home/zzw4257/seed-k8s/output/assistant_entry/latest/summary.json`
3. Output:
   - one direct command for the user's current question
   - 2-3 classic kubectl patterns with short purpose notes
   - explicit assumptions for `KUBECONFIG` and `SEED_NAMESPACE`
4. For pure explain requests, do not execute shell commands.
5. Keep commands non-destructive unless user explicitly asks.
