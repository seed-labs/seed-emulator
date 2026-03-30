# SEED-Emulator Kubernetes Examples

This directory contains the Kubernetes-facing example scripts for SEED
Emulator.

Some examples are promoted into profile-backed runtime workflows. Others are
compile-only examples that are not yet part of the runtime baseline.

Public operator guide: `docs/k8s_usage.md`  
Maintainer architecture guide: `docs/k3s_runtime_architecture.md`

## Support Matrix

| Script | Support tier | Public profile | Compile entry | Runtime entry | Size policy |
|:---|:---|:---|:---|:---|:---|
| `k8s_mini_internet.py` | Tier-1 | `mini_internet` | `scripts/seed_k8s_profile_runner.sh mini_internet compile` | `scripts/seed_k8s_profile_runner.sh mini_internet all` | fixed example |
| `k8s_real_topology_rr.py` | Tier-1 | `real_topology_rr` | `scripts/seed_k8s_profile_runner.sh real_topology_rr compile` | `SEED_TOPOLOGY_SIZE=214 scripts/seed_k8s_profile_runner.sh real_topology_rr all` | `214` baseline |
| `k8s_real_topology_rr.py` | Tier-1 | `real_topology_rr_scale` | `scripts/seed_k8s_profile_runner.sh real_topology_rr_scale compile` | `SEED_TOPOLOGY_SIZE=214 scripts/seed_k8s_profile_runner.sh real_topology_rr_scale all` | `214` baseline, `1078` rehearsal, `1897` target via `seedemu-k3s-scale` |
| `k8s_transit_as.py` | Tier-2 | `transit_as` | `scripts/seed_k8s_profile_runner.sh transit_as compile` | `scripts/seed_k8s_profile_runner.sh transit_as compile/build/deploy/verify/report` | fixed example |
| `k8s_mini_internet_with_visualization.py` | Tier-2 | `mini_internet_viz` | `scripts/seed_k8s_profile_runner.sh mini_internet_viz compile` | `scripts/seed_k8s_profile_runner.sh mini_internet_viz compile/build/deploy/verify/report` | fixed example |
| `k8s_hybrid_kubevirt_demo.py` | Tier-2 | `hybrid_kubevirt` | `scripts/seed_k8s_profile_runner.sh hybrid_kubevirt compile` | `scripts/seed_k8s_profile_runner.sh hybrid_kubevirt compile/build/deploy/verify/report` | capability-gated by cluster features |
| `k8s_nano_internet.py` | Tier-3 | none | `python3 examples/kubernetes/k8s_nano_internet.py` | compile-only | not promoted |
| `k8s_multinode_demo.py` | Tier-3 | none | `python3 examples/kubernetes/k8s_multinode_demo.py` | compile-only | not promoted |
| `k8s_multinode_demo_dynamic.py` | Tier-3 | none | `python3 examples/kubernetes/k8s_multinode_demo_dynamic.py` | compile-only | not promoted |

## Official staged workflow

For promoted profiles, the normal operator flow is:

```bash
scripts/seed_k8s_profile_runner.sh <profile> compile
scripts/seed_k8s_profile_runner.sh <profile> build
scripts/seed_k8s_profile_runner.sh <profile> deploy
scripts/seed_k8s_profile_runner.sh <profile> start-bird
scripts/seed_k8s_profile_runner.sh <profile> start-kernel
scripts/seed_k8s_profile_runner.sh <profile> verify
scripts/seed_k8s_profile_runner.sh <profile> observe
scripts/seed_k8s_profile_runner.sh <profile> report
```

`all` is a convenience wrapper for the same chain.

## Real-topology dataset notes

`k8s_real_topology_rr.py` reads external real-topology data. The dataset is not
committed to this repository.

Default operator settings:

```bash
export SEED_REAL_TOPOLOGY_DIR=~/lxl_topology/autocoder_test
export SEED_ASSIGNMENT_FILE="${SEED_REAL_TOPOLOGY_DIR}/assignment.pkl"
export SEED_TOPOLOGY_SIZE=214
```

On the reference cluster:

- `214` is the maintained baseline
- `1078` is the rehearsal/debug waypoint
- `1897` is the first official large-hardware target and is capacity-gated on
  the reference cluster
- the current SSH/entry-status hardening keeps the runtime behavior of the
  `214` promoted examples intact and makes KVM node access visible before
  build/deploy time

To move from the reference cluster to the tracked scale inventory:

```bash
SEED_CLUSTER_INVENTORY=seedemu-k3s-scale \
SEED_K3S_FORCE_REINSTALL=true \
scripts/setup_k3s_cluster.sh
```

## Acceptance mapping

- Tier-1 profiles are part of `scripts/seed_k8s_acceptance.sh tier1-runtime`
- Tier-2 profiles are part of `scripts/seed_k8s_acceptance.sh tier2-runtime`
- Tier-3 examples are part of `scripts/seed_k8s_acceptance.sh compile-all`

## What “promoted” means

An example is promoted beyond compile-only only when it has:

1. a stable compile entry,
2. a public support-tier declaration,
3. a documented staged runtime path,
4. a stable evidence contract.
