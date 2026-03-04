---
name: seed-lab-preflight
description: Prepare and validate SEED k3s runtime prerequisites before compile/deploy by using smoke, kubeconfig fetch, and preflight checks.
---

## When to use

Use before compile/build/deploy/verify for any k3s-based SEED run.

## Workflow

1. Load guardrails:
   - `/home/zzw4257/seed-k8s/scripts/env_seedemu.sh`
2. Run non-destructive smoke checks:
   - `/home/zzw4257/seed-k8s/scripts/opencode_seedlab_smoke.sh`
3. If kubeconfig missing or invalid:
   - `/home/zzw4257/seed-k8s/scripts/k3s_fetch_kubeconfig.sh`
4. Run preflight stage:
   - `/home/zzw4257/seed-k8s/scripts/validate_k3s_mini_internet_multinode.sh preflight`

## Required evidence

Preflight should point to:

- `<artifact_dir>/preflight.json`
- `<artifact_dir>/kube_nodes.txt`
- `<artifact_dir>/multus_status.txt`
- `<artifact_dir>/summary.json`

## Fast failure handling

If preflight fails, report:

1. failed stage (`preflight`)
2. failed command
3. first evidence file path
4. smallest retry command
