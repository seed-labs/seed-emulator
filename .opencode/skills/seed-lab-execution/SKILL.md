---
name: seed-lab-execution
description: Execute SEED mini-internet pipeline stages compile, build, and deploy on k3s using canonical project scripts.
---

## When to use

Use after preflight passes and when user asks to start or continue deployment.

## Canonical stage commands

Run these commands in order:

1. `scripts/validate_k3s_mini_internet_multinode.sh compile`
2. `scripts/validate_k3s_mini_internet_multinode.sh build`
3. `scripts/validate_k3s_mini_internet_multinode.sh deploy`

For one-shot runs:

- `scripts/validate_k3s_mini_internet_multinode.sh all`

## Evidence expectations

Execution output must include references to:

- `<artifact_dir>/compile.log`
- `<artifact_dir>/remote_build.log`
- `<artifact_dir>/apply.log`
- `<artifact_dir>/wait.log`
- `<artifact_dir>/deployments_wide.txt`
- `<artifact_dir>/pods_wide.txt`

## Deployment completion criteria

Treat deployment as ready only when all namespace deployments are `Available` in wait output.
