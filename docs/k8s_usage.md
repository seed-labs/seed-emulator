# SEED Emulator: Kubernetes and K3s Operator Guide

This guide is the public operator manual for the SEED K8s/K3s subsystem. It is
written for someone who wants to run the maintained workflows without depending
on local notes or AI-only context.

The current reference environment is a 3-node K3s+KVM cluster. The maintained
runtime-validated profiles are:

- `mini_internet`
- `real_topology_rr`
- `real_topology_rr_scale`

For the local Kind + Multus + KubeVirt developer path, see
`docs/runbooks/local_kind_quick_runbook.md`.

## 1. Public entry points

The K8s subsystem exposes one operator entry:

```bash
scripts/seed_k8s_profile_runner.sh <profile> <action>
```

The most useful actions are:

- `doctor`
- `build`
- `start`
- `phase-start`
- `verify`
- `observe`
- `report`
- `all`

The first command to run on any machine is:

```bash
cd <repo_root>
source scripts/env_seedemu.sh
scripts/seed_lab_entry_status.sh
```

That command prints the current cluster state, inventory, latest run evidence,
and the next recommended action.

## 2. Support tiers

### Tier-1: runtime-validated

These profiles are part of the official acceptance baseline:

- `mini_internet`
- `real_topology_rr`
- `real_topology_rr_scale`

They must produce the full validation contract:

- `summary.json`
- `placement_by_as.tsv`
- `protocol_health.json`
- `connectivity_matrix.tsv`
- `convergence_timeline.json`
- `failure_injection_summary.json`
- `resource_summary.json`
- `relationship_graph.json`
- `network_attachment_matrix.tsv`

### Tier-2: capability-gated runtime

These profiles are supported, but may depend on optional services or cluster
features:

- `transit_as`
- `mini_internet_viz`
- `hybrid_kubevirt`

### Tier-3: compile-only backlog

These examples must compile cleanly, but they are not yet official runtime
acceptance targets:

- `k8s_nano_internet.py`
- `k8s_multinode_demo.py`
- `k8s_multinode_demo_dynamic.py`

## 3. Environment guardrails

Use the repository environment helper before running K8s workflows:

```bash
cd <repo_root>
source scripts/env_seedemu.sh
```

That gives you:

- a stable `REPO_ROOT`,
- a stable `PYTHONPATH`,
- the `k3s*` shortcut commands on `PATH`.

The key variables are:

- `KUBECONFIG`
- `SEED_EXPERIMENT_PROFILE`
- `SEED_NAMESPACE`
- `SEED_CNI_TYPE`
- `SEED_CNI_MASTER_INTERFACE`
- `SEED_REGISTRY`
- `SEED_OUTPUT_DIR`
- `SEED_ARTIFACT_DIR`

For real topology runs, you also need:

- `SEED_REAL_TOPOLOGY_DIR`
- `SEED_TOPOLOGY_SIZE`
- `SEED_TOPOLOGY_FILE` (optional override)
- `SEED_ASSIGNMENT_FILE` (optional override)

## 4. Reference-cluster quick start

### 4.1 Health check

```bash
scripts/seed_k8s_profile_runner.sh mini_internet doctor
```

### 4.2 Full Tier-1 baseline

```bash
scripts/seed_k8s_profile_runner.sh mini_internet all
SEED_TOPOLOGY_SIZE=214 scripts/seed_k8s_profile_runner.sh real_topology_rr all
SEED_TOPOLOGY_SIZE=214 scripts/seed_k8s_profile_runner.sh real_topology_rr_scale all
```

### 4.3 Split-stage workflow

Use this when you want separate timing for build, deployment, and protocol
startup:

```bash
scripts/seed_k8s_profile_runner.sh mini_internet build
scripts/seed_k8s_profile_runner.sh mini_internet start
scripts/seed_k8s_profile_runner.sh mini_internet phase-start
scripts/seed_k8s_profile_runner.sh mini_internet verify
scripts/seed_k8s_profile_runner.sh mini_internet observe
scripts/seed_k8s_profile_runner.sh mini_internet report
```

`start` brings workloads up but does **not** start `bird`.
`phase-start` is the explicit protocol-start phase.

## 5. Real-topology data and capacity gate

The real-topology profile reads external data and does not commit the dataset to
the repository.

Default operator settings:

```bash
export SEED_REAL_TOPOLOGY_DIR=~/lxl_topology/autocoder_test
export SEED_ASSIGNMENT_FILE="${SEED_REAL_TOPOLOGY_DIR}/assignment.pkl"
export SEED_TOPOLOGY_SIZE=214
```

The current reference cluster validates `214` as the official Tier-1 size.

Larger targets such as `1897/1899` are still part of the official roadmap, but
they are **capacity-gated** on the reference cluster. When a scale request is
too large for the reference environment, preflight returns a clean
`CAPACITY_GATED` result instead of a vague build or deploy failure.

## 6. Compose-style shortcuts

After `source scripts/env_seedemu.sh`, the following shortcuts are available:

- `k3sdoctor <profile>`
- `k3sbuild <profile>`
- `k3sup <profile>`
- `k3sphase <profile>`
- `k3sverify <profile>`
- `k3sobserve <profile>`
- `k3sreport <profile>`
- `k3sall <profile>`
- `k3scompare <profile>`
- `k3sdown <profile>`

Runtime inspection shortcuts:

- `k3sps <profile>`
- `k3slogs <profile> <pod-or-selector>`
- `k3sexec <profile> <pod-or-selector> -- <command>`
- `k3stop <profile>`
- `k3sevents <profile>`

These are thin aliases. They print the real command mapping before execution.

## 7. Evidence-first verification

The validation contract is the definition of “ready for experiment”. A run is
not complete just because `kubectl apply` succeeded.

Open these files first:

1. `output/profile_runs/<profile>/latest/validation/summary.json`
2. `output/profile_runs/<profile>/latest/validation/protocol_health.json`
3. `output/profile_runs/<profile>/latest/validation/placement_by_as.tsv`
4. `output/profile_runs/<profile>/latest/report/report.json`

If someone asks whether K8s preserves strong workload relationships, the most
useful files are:

- `placement_by_as.tsv`
- `network_attachment_matrix.tsv`
- `relationship_graph.json`

## 8. Acceptance entry

The public acceptance harness is:

```bash
scripts/seed_k8s_acceptance.sh <suite>
```

Supported suites:

- `docs`
- `unit`
- `compile-all`
- `tier1-runtime`
- `tier2-runtime`
- `all`

## 9. Troubleshooting rules

- If `doctor` fails, do not jump straight to `all`.
- If `start` fails, inspect deployment and image distribution evidence before
  re-running.
- If `phase-start` fails, inspect the `bird_before_phase.txt`,
  `bird_after_phase.txt`, or `phased_startup_summary.json` artifacts.
- If `verify` fails, use `diagnostics.json`, `artifact_contract.json`, and
  `report/report.json` before inventing a new retry path.

## 10. Optional AI helper

`opencode` is optional. If you want the repository's tracked AI helper flow, see
`docs/runbooks/opencode_seed_lab_quickstart.md`.
