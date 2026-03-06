---
name: seed-lab-verification
description: Verify placement gate, BGP establishment, cross-AS connectivity, and recovery for SEED k3s mini-internet runs.
---

## When to use

Use after deployment readiness for acceptance checks.

## Verification command

Use:

- `scripts/validate_k3s_mini_internet_multinode.sh verify`

## Acceptance criteria

Read `<artifact_dir>/summary.json`. Success requires all of these:

- placement gate passed:
  - if `placement_mode == strict3`: `strict3_passed == true`
  - else: `placement_passed == true` and `nodes_used >= SEED_MIN_NODES_USED` (default 2)
- `bgp_passed == true`
- `connectivity_passed == true`
- `recovery_passed == true`

## Required evidence pointers

On success or failure, always report these files when they exist:

- `placement_check.json`
- `bird_router151.txt`
- `bird_ix100.txt`
- `ping_150_to_151.txt`
- `recovery_check.json`
- `summary.json`

## Failure contract

If any acceptance criterion fails, output:

1. `failed_stage`
2. `failed_command`
3. `first_evidence_file`
4. `minimal_retry_command`
