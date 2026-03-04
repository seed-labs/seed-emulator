---
name: seed-lab-core
description: Core operating contract for SEED k3s experiments: absolute paths, environment guardrails, stage order, and destructive-action confirmation.
---

## When to use

Use this skill for any SEED lab run in this workspace. It defines non-negotiable behavior for all other seed-lab skills.

## Non-negotiable rules

1. Use `/home/zzw4257/seed-k8s` as repo root.
2. Use absolute paths only.
3. Run stages in this order unless user explicitly overrides:
   - bootstrap
   - preflight
   - compile
   - build
   - deploy
   - verify
   - observe
   - summary
4. Always report stage result with:
   - `stage`
   - `status`
   - `command`
   - `artifact`
   - `next`

Bootstrap stage command:

- `/home/zzw4257/seed-k8s/scripts/seed_lab_entry_status.sh`

## Required environment contract

Before run actions, ensure these variables exist or assign defaults:

- `KUBECONFIG`
- `SEED_K3S_MASTER_IP`
- `SEED_K3S_WORKER1_IP`
- `SEED_K3S_WORKER2_IP`
- `SEED_K3S_USER`
- `SEED_K3S_SSH_KEY`
- `SEED_NAMESPACE`
- `SEED_CNI_TYPE`
- `SEED_ARTIFACT_DIR`
- `SEED_OUTPUT_DIR`

Default profile for local k3s lab:

- `SEED_K3S_CLUSTER_NAME=seedemu-k3s`
- `SEED_NAMESPACE=seedemu-k3s-mini-mn`
- `SEED_CNI_TYPE=macvlan`
- `CONNECTIVITY_RETRY=24`
- `CONNECTIVITY_RETRY_INTERVAL_SECONDS=5`

## Guardrail for destructive operations

Require explicit confirmation phrase before destructive operations:

`CONFIRM_SEED_DESTRUCTIVE: <target>`

Destructive operations include:

- `kubectl delete namespace ...`
- `kubectl delete pod ...` for fault injection
- `scripts/setup_k3s_cluster.sh` rebuild path
