# SEED Emulator K3s Runtime Architecture

This document is the maintainer-facing architecture manual for the SEED
K8s/K3s subsystem.

It answers four questions:

1. What is the maintained runtime model?
2. Which profiles and examples are officially supported?
3. What evidence defines a successful run?
4. How do we promote new examples without weakening the baseline?

## 1. Architectural boundary

The K8s subsystem is intentionally layered:

- **Example script**: builds topology and compiles Kubernetes artifacts
- **Profile**: names the workflow and declares defaults and contract
- **Runner**: the public lifecycle entry
- **Validate / report**: turn cluster state into evidence and normalized reports
- **Acceptance harness**: runs the public delivery checks

The operator entry is fixed:

```bash
scripts/seed_k8s_profile_runner.sh <profile> <action>
```

We do not create a second execution framework for “advanced” runs.

## 2. Reference truth and support tiers

### Tier-1 runtime-validated profiles

These are the branch truth for runtime acceptance:

- `mini_internet`
- `real_topology_rr`
- `real_topology_rr_scale`

Current validated size on the reference cluster:

- `mini_internet`
- `real_topology_rr(214)`
- `real_topology_rr_scale(214)`

### Tier-2 capability-gated profiles

- `transit_as`
- `mini_internet_viz`
- `hybrid_kubevirt`

These can be part of the public subsystem, but they may legally return a
capability-gated outcome when the reference cluster lacks a required feature.

### Tier-3 compile-only backlog

- `k8s_nano_internet.py`
- `k8s_multinode_demo.py`
- `k8s_multinode_demo_dynamic.py`

Tier-3 examples must compile cleanly and be classified in the public matrix,
but they are not runtime gates yet.

## 3. Profile contract

Profiles live in `configs/seed_k8s_profiles.yaml`.

Each public profile must declare:

- `profile_id`
- `support_tier`
- `acceptance_level`
- `capacity_gate`
- `compile_script`
- `default_namespace`
- `default_cni_type`
- `default_scheduling_strategy`
- `verify_mode`

Tier-1 and Tier-2 public profiles also declare validation artifact
requirements.

## 4. Artifact contract

Every official runtime-supported profile must produce a stable evidence set.

The core files are:

- `validation/summary.json`
- `validation/placement_by_as.tsv`
- `validation/protocol_health.json`
- `validation/connectivity_matrix.tsv`
- `validation/convergence_timeline.json`
- `validation/failure_injection_summary.json`
- `validation/resource_summary.json`
- `validation/relationship_graph.json`
- `validation/network_attachment_matrix.tsv`
- `report/report.json`

The summary and report contracts must keep these fields non-null:

- `profile_id`
- `runner_status`
- `pipeline_duration_seconds`
- `image_distribution_mode`
- `support_tier`
- `capacity_gate_status`

## 5. Protocol startup model

The maintained multi-node model is explicit:

- `start` deploys workloads
- `phase-start` starts `bird` and performs protocol startup
- `verify` checks placement, protocol health, connectivity, and recovery

This keeps deployment failures separate from protocol failures.

## 6. Relationship evidence

One of the main reasons for the K8s branch is to prove that the K8s runtime can
express the strong workload relationships that used to be easier to “see” in the
Compose workflow.

The maintained evidence is:

- `placement_by_as.tsv`: which AS landed on which node
- `network_attachment_matrix.tsv`: what network attachments each Pod reported
- `relationship_graph.json`: ASN, Pod, node, attachment, and sampled protocol
  adjacency graph

These files are required because “Pods are ready” is not enough for a network
experiment delivery.

## 7. Capacity gate model

The current reference cluster is the 3-node K3s+KVM environment.

The real-topology scale target remains official, but it is capacity-gated on the
reference cluster:

- `214` is the maintained Tier-1 runtime acceptance size
- `1897/1899` stays supported in code and docs
- larger runs on the reference cluster must fail with `CAPACITY_GATED`

This keeps the roadmap visible without pretending the current hardware can
accept everything.

## 8. Acceptance system

The public acceptance entry is:

```bash
scripts/seed_k8s_acceptance.sh <suite>
```

The maintained suites are:

- `docs`
- `unit`
- `compile-all`
- `tier1-runtime`
- `tier2-runtime`
- `all`

This is intentionally broader than unit tests. The K8s subsystem is accepted by
runtime evidence, not by unit coverage alone.

## 9. Public docs vs local notes

Tracked docs must remain:

- English
- stable
- operator or maintainer facing

The following must stay out of git:

- dated runbooks
- private handoff notes
- personal assessments
- local showcase/report packs
- local `.opencode` package state

Those belong under ignored local paths such as `output/private_docs/`.

## 10. Promotion path for new examples

An example moves through these stages:

1. **Compile-only**: stable `k8s.yaml` and `build_images.sh`
2. **Tier-2**: documented runtime workflow and capability-gated acceptance
3. **Tier-1**: full validation contract and stable runtime evidence on the
   reference cluster

Promotion requires:

- docs update,
- profile metadata update (if operator-facing),
- acceptance coverage,
- evidence contract stability.
