---
name: seed-lab-triage
description: Diagnose failed SEED k3s runs from artifact directories and return minimal retry commands.
---

## When to use

Use when any stage fails or when user asks for diagnosis.

## Inputs

- `SEED_ARTIFACT_DIR` or explicit artifact directory argument
- optional observe directory (`SEED_OBSERVE_DIR`)

## Triage order

1. Read `<artifact_dir>/summary.json` for `failure_reason`.
2. Map `failure_reason` to first evidence files:
   - `kubeconfig_not_found_after_fetch`: `kubeconfig_fetch.log`
   - `preflight_failed_after_repair`: `preflight.json`, `preflight_repair.log`
   - `compile_missing_k8s_yaml`: `compile.log`
   - `deploy_wait_timeout_or_failure`: `wait.log`, `events_tail.txt`
   - `strict3_placement_failed`: `placement_check.json`, `placement_actual.json`
   - `bgp_not_established`: `bird_router151.txt`, `bird_ix100.txt`
   - `connectivity_check_failed`: `ping_150_to_151.txt`
   - `recovery_check_failed`: `recovery_check.json`
3. Provide smallest retry command from stage boundary:
   - preflight -> `... preflight`
   - compile -> `... compile`
   - build -> `... build`
   - deploy -> `... deploy`
   - verify -> `... verify`

## Output schema

Return concise JSON-like keys in plain text:

- `failed_stage`
- `failure_reason`
- `failed_command`
- `first_evidence_file`
- `minimal_retry_command`
