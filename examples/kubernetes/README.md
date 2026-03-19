# SEED-Emulator Kubernetes Examples

This directory contains the Kubernetes-facing example scripts for SEED
Emulator. Some scripts are promoted into official profile-based workflows,
while others are compile-ready examples that will be promoted later.

For the public operator workflow, start with `docs/k8s_usage.md`.
For maintainer boundaries and promotion rules, see `docs/k3s_runtime_architecture.md`.

## Support Matrix

| Script | Docker / legacy source | Tier | Runtime status | Recommended entry |
|:---|:---|:---|:---|:---|
| `k8s_mini_internet.py` | `examples/internet/B00_mini_internet` | Tier-1 | Runtime-validated | `scripts/seed_k8s_profile_runner.sh mini_internet all` |
| `k8s_real_topology_rr.py` | External dataset (`RR_214_example.py` lineage) | Tier-1 | Runtime-validated (`real_topology_rr`, `real_topology_rr_scale`) | `scripts/seed_k8s_profile_runner.sh real_topology_rr all` |
| `k8s_transit_as.py` | `examples/basic/A01_transit_as` | Tier-2 | Capability-gated runtime | `scripts/seed_k8s_profile_runner.sh transit_as build/start/verify/report` |
| `k8s_mini_internet_with_visualization.py` | `examples/internet/B00_mini_internet` + Internet Map | Tier-2 | Capability-gated runtime | `scripts/seed_k8s_profile_runner.sh mini_internet_viz build/start/verify/report` |
| `k8s_hybrid_kubevirt_demo.py` | Hybrid KubeVirt demo | Tier-2 | Capability-gated runtime | `scripts/seed_k8s_profile_runner.sh hybrid_kubevirt build/start/verify/report` |
| `k8s_nano_internet.py` | `examples/basic/A20_nano_internet` | Tier-3 | Compile-only backlog | `python3 examples/kubernetes/k8s_nano_internet.py` |
| `k8s_multinode_demo.py` | Kubernetes-only demo | Tier-3 | Compile-only backlog | `python3 examples/kubernetes/k8s_multinode_demo.py` |
| `k8s_multinode_demo_dynamic.py` | Kubernetes-only demo | Tier-3 | Compile-only backlog | `python3 examples/kubernetes/k8s_multinode_demo_dynamic.py` |

## Official Profiles

The maintained profiles are defined in `configs/seed_k8s_profiles.yaml`.

- `mini_internet`: Tier-1, strict runtime acceptance
- `real_topology_rr`: Tier-1, strict runtime acceptance (default size `214`)
- `real_topology_rr_scale`: Tier-1, strict runtime acceptance at `214`, capacity-gated for larger runs
- `transit_as`: Tier-2, capability-gated runtime
- `mini_internet_viz`: Tier-2, capability-gated runtime
- `hybrid_kubevirt`: Tier-2, capability-gated runtime

## Recommended Workflow

### Operator workflow

```bash
cd <repo_root>
source scripts/env_seedemu.sh
scripts/seed_lab_entry_status.sh
scripts/seed_k8s_profile_runner.sh mini_internet all
```

### Compile smoke for an individual example

```bash
cd <repo_root>
source scripts/env_seedemu.sh
PYTHONPATH="${REPO_ROOT}" python3 examples/kubernetes/k8s_transit_as.py
```

### Run the acceptance harness

```bash
cd <repo_root>
source scripts/env_seedemu.sh
scripts/seed_k8s_acceptance.sh compile-all
```

## Hybrid KubeVirt Runtime Profile

`k8s_hybrid_kubevirt_demo.py` supports `SEED_RUNTIME_PROFILE`:

- `auto`: pick the best available mode
- `full`: require VM + container hybrid mode
- `degraded`: force container-only mode
- `strict`: fail if VM mode is unavailable

Example:

```bash
SEED_RUNTIME_PROFILE=auto PYTHONPATH="${REPO_ROOT}" python3 examples/kubernetes/k8s_hybrid_kubevirt_demo.py
```

## What “promoted” means

An example is promoted beyond compile-only only when it has:

1. a stable compile entry,
2. a profile (if it is operator-facing),
3. a validation artifact contract,
4. a documented acceptance path.
