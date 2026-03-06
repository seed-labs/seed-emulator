---
description: Bootstrap status for real users: what is available now, what can be done next, and where evidence is stored.
agent: seed-lab
---

Use skills:

1. `seed-lab-experiment-assistant`
2. `seed-lab-optimizer`

Mandatory behavior:

1. Run:
   - `scripts/seed_lab_entry_status.sh`
2. Read:
   - `output/assistant_entry/latest/summary.json`
3. Output sections:
   - `当前可用环境` (KVM/k3s/kubeconfig/namespace)
   - `可做任务` (k8s/k3s macro tasks and profile options)
   - `证据位置` (artifact and output paths)
   - `建议下一步` (exactly one command)
   - `关键环境变量` (`KUBECONFIG`, `SEED_EXPERIMENT_PROFILE`, `SEED_NAMESPACE`, `SEED_CNI_TYPE`)
4. Do not run long pipeline commands unless user explicitly requests.
