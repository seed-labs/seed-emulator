# SEED Emulator K3s Runtime Architecture

This document is the maintainer manual for the K8s/K3s subsystem.

It defines the public contract that must remain stable enough for a master
branch merge.

## 1. Layering

The K8s subsystem is intentionally split into five layers:

1. **Example script**: builds the topology and compiles Kubernetes artifacts
2. **Profile metadata**: declares defaults, support tier, and artifact contract
3. **Runner**: exposes the staged public lifecycle
4. **Validate / report**: turns cluster state into evidence and a normalized report
5. **Acceptance harness**: checks docs, unit tests, compile coverage, and runtime evidence

The public execution entry remains:

```bash
scripts/seed_k8s_profile_runner.sh <profile> <action>
```

There is no second execution framework for “advanced” use.

## 2. Public staged contract

The public lifecycle is:

```text
doctor -> compile -> build -> deploy -> start-bird -> start-kernel -> verify -> observe -> report
```

Compatibility aliases:

- `start` -> `deploy`
- `phase-start` -> compatibility wrapper for the old protocol-start stage

`all` exists only as a convenience wrapper for the full staged chain.

## 3. Profile metadata contract

Profiles live in `configs/seed_k8s_profiles.yaml`.

Each public profile must declare:

- `profile_id`
- `support_tier`
- `acceptance_level`
- `capacity_gate`
- `default_topology_size`
- `compile_script`
- `default_namespace`
- `default_cni_type`
- `default_scheduling_strategy`
- `verify_mode`

Tier-1 and Tier-2 profiles also declare the required validation artifacts.

## 4. Inventory contract

Cluster inventories live in `configs/clusters/<inventory>.yaml`.

The normalized inventory contract includes:

- cluster name
- runtime
- SSH user and key resolution
- registry host and port
- default CNI master interface
- node list
- `reference_cluster`
- `max_validated_topology_size`
- optional K3s density settings such as:
  - `k3s.cluster_cidr`
  - `k3s.service_cidr`
  - `k3s.node_cidr_mask_size_ipv4`
  - `k3s.max_pods`

The current tracked reference inventory is `configs/clusters/seedemu-k3s.yaml`.
The tracked scale inventory is `configs/clusters/seedemu-k3s-scale.yaml`.

Operators must be able to prove KVM node reachability independently from the
rest of the runtime. The tracked helper for that is:

```bash
python3 scripts/seed_k8s_ssh_probe.py --user ubuntu --key ~/.ssh/id_ed25519 ...
```

The validator preflight uses the same SSH settings and writes
`validation/ssh_access.json` so node-access failures surface as
`SSH_ACCESS_FAILED` instead of being misclassified as a later-stage runtime
issue.

Placement policy for the reference cluster is intentionally conservative:
multi-Pod AS workloads prefer worker nodes, and the control-plane node is used
for singleton workloads unless workers can no longer fit the larger AS.

That field is what drives scale gating. The reference cluster currently exposes
`max_validated_topology_size: 214`.

When the operator switches from the reference inventory to the scale inventory,
the cluster must be recreated so the wider Pod CIDR allocation actually takes
effect:

```bash
SEED_CLUSTER_INVENTORY=seedemu-k3s-scale \
SEED_K3S_FORCE_REINSTALL=true \
scripts/setup_k3s_cluster.sh
```

## 5. Support tiers and scale policy

### Tier-1 runtime-validated

- `mini_internet`
- `real_topology_rr`
- `real_topology_rr_scale`

Current reference-cluster truth:

- `mini_internet`
- `real_topology_rr(214)`
- `real_topology_rr_scale(214)`

Scope note for the latest hardening pass:

- the large-topology `214` runtime path was already functional before this SSH
  diagnostic update,
- this pass improves node-access truth and operator triage,
- it does not redefine the topology semantics of the promoted examples.

### Tier-2 capability-gated runtime

- `transit_as`
- `mini_internet_viz`
- `hybrid_kubevirt`

### Tier-3 compile-only

- `k8s_nano_internet.py`
- `k8s_multinode_demo.py`
- `k8s_multinode_demo_dynamic.py`

Large-topology policy:

- `214` is the maintained reference-cluster runtime size
- `1078` is the rehearsal/debug waypoint
- `1897` is the first official large-hardware target

If a request exceeds the current inventory limit, the subsystem must return
`CAPACITY_GATED`, not an ambiguous later-stage failure.

## 6. Status truth

Two fields must stay distinct:

- `runner_status`: whether the requested action succeeded
- `acceptance_status`: overall lifecycle truth of the run

Allowed acceptance values:

- `NOT_RUN`
- `PARTIAL`
- `PASS`
- `FAIL`
- `CAPACITY_GATED`

Rules:

- `start-bird` or `start-kernel` success is still only `PARTIAL`
- only a full verify/report-backed run may become `PASS`
- `overall_passed=true` is reserved for a fully accepted run

`scripts/seed_lab_entry_status.sh` must keep reporting:

- latest attempted run
- latest verified run
- latest accepted run
- active `seedemu-*` namespaces that still occupy the cluster

On the reference 3-node K3s+KVM cluster, the `214`-node real-topology profiles
are effectively single-tenant workloads. Operators should not leave
`seedemu-k3s-real-topo*` namespaces running while launching another `214`-node
profile.

## 7. Artifact contract

Every runtime-supported profile must produce a stable evidence set.

Required validation artifacts:

- `validation/summary.json`
- `validation/placement_by_as.tsv`
- `validation/protocol_health.json`
- `validation/connectivity_matrix.tsv`
- `validation/convergence_timeline.json`
- `validation/failure_injection_summary.json`
- `validation/resource_summary.json`
- `validation/relationship_graph.json`
- `validation/network_attachment_matrix.tsv`

Canonical protocol-start artifacts:

- `validation/start_bird_summary.json`
- `validation/start_bird.log`
- `validation/start_kernel_summary.json`
- `validation/start_kernel.log`

Compatibility artifacts remain available for older tooling:

- `validation/phased_startup_summary.json`
- `validation/bird0130_summary.json`
- `validation/bird_kernel_summary.json`

The normalized report must live at:

- `report/report.json`

## 8. Relationship evidence

K8s parity is not proven by Pod readiness alone. The maintained evidence is:

- `placement_by_as.tsv`
- `network_attachment_matrix.tsv`
- `relationship_graph.json`

These artifacts are the answer to “can K8s preserve the same strong workload
relationships that Compose made easier to inspect?”

## 9. Acceptance system

The public acceptance entry is:

```bash
scripts/seed_k8s_acceptance.sh <suite>
```

Maintained suites:

- `docs`
- `unit`
- `compile-all`
- `tier1-runtime`
- `tier2-runtime`
- `all`

K8s delivery is judged by evidence-backed runtime acceptance, not only by unit
tests.

## 10. Public docs vs local notes

Tracked docs must remain:

- English
- stable
- operator-facing or maintainer-facing

The following must stay local-only and out of git:

- dated runbooks
- handoff notes
- private investigation notes
- local showcase or report packs
- local helper workbenches such as `lxl/`

Those belong under ignored local paths such as `output/private_docs/`.

## 11. Migration rule for future examples

New K8s example migrations should follow one pattern:

1. shared topology builder
2. Kubernetes compile entry
3. optional public profile
4. staged runtime contract
5. support-tier declaration

Promotion path:

1. compile-only
2. Tier-2 runtime candidate
3. Tier-1 runtime-validated

Promotion requires:

- public docs,
- profile metadata,
- acceptance coverage,
- stable evidence artifacts.
