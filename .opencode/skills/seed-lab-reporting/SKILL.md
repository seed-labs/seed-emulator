---
name: seed-lab-reporting
description: Generate normalized report.json and report.md from validation and observe artifacts for reproducible SEED review.
---

## When to use

Use after verify/observe, or when user asks for a concise review package.

## Report command

Run:

`scripts/seedlab_report_from_artifacts.sh [validation_dir] [observe_dir] [report_dir]`

If arguments are not given:

- validation_dir: `SEED_ARTIFACT_DIR` or latest `output/multinode_mini_validation/*`
- observe_dir: `SEED_OBSERVE_DIR` or `output/mini_observe/latest`
- report_dir: `<validation_dir>/report`

## Required outputs

- `<report_dir>/report.json`
- `<report_dir>/report.md`

## Report minimum content

- cluster and namespace
- cni type and interface
- strict3/bgp/connectivity/recovery pass flags
- nodes used
- failure reason
- key evidence file paths
- one recommended next command
